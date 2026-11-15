import copy
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Callable

# The scorer is the stage of `impact-scoring`: (graph, units) in, the content of scenarios.json out.
# It is injected so this module reads only candidates[].id, .rank and .affected_community_ids.
Scorer = Callable[[dict, list[dict]], dict]

SPEEDS = (0.8, 1.2)
THRESHOLDS = {"top5_min_overlap": 4}
MIN_UNITS_WITH_IMPACT = 5


class SensitivityError(Exception):
  pass


def speed_variant(graph: dict, factor: float) -> dict:
  """Every time_s divided by the factor and rounded half up; exact arithmetic, so no float drift on the halves."""
  divisor = Fraction(str(factor))
  edges = [{**edge, "time_s": math.floor(Fraction(edge["time_s"]) / divisor + Fraction(1, 2))} for edge in graph["edges"]]
  return {**copy.deepcopy({k: v for k, v in graph.items() if k != "edges"}), "edges": edges}


def hospital_variant(graph: dict, hospital: dict) -> dict:
  rest = {k: v for k, v in graph.items() if k != "hospitals"}
  return {**copy.deepcopy(rest), "hospitals": [h for h in copy.deepcopy(graph["hospitals"]) if h["id"] != hospital["id"]]}


def _ranked(scenarios: dict) -> list[dict]:
  return sorted(scenarios["candidates"], key=lambda unit: unit["rank"])


def _impact_ranks(scenarios: dict) -> dict[str, int]:
  return {unit["id"]: unit["rank"] for unit in scenarios["candidates"] if unit["affected_community_ids"]}


def top_overlap(baseline: dict, run: dict, k: int) -> int:
  top = lambda scenarios: {unit["id"] for unit in _ranked(scenarios)[:k]}
  return len(top(baseline) & top(run))


def _average_ranks(values: list[float]) -> list[float]:
  ordered = sorted(values)
  return [sum(i + 1 for i, v in enumerate(ordered) if v == value) / ordered.count(value) for value in values]


def rank_correlation(baseline: dict, run: dict) -> tuple[float | None, int]:
  """Spearman over the units with impact in both runs, and how many there are; None without a defined value."""
  base_ranks, run_ranks = _impact_ranks(baseline), _impact_ranks(run)
  common = sorted(base_ranks.keys() & run_ranks.keys())
  if len(common) < 2:
    return None, len(common)
  x = _average_ranks([base_ranks[unit] for unit in common])
  y = _average_ranks([run_ranks[unit] for unit in common])
  mean_x, mean_y = sum(x) / len(x), sum(y) / len(y)
  covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
  spread = math.sqrt(sum((a - mean_x) ** 2 for a in x) * sum((b - mean_y) ** 2 for b in y))
  # No spread (every rank tied in one run): the correlation is undefined.
  return (covariance / spread if spread else None), len(common)


def _check_scenarios(scenarios: object, label: str) -> None:
  """The fields this module reads, checked where the data comes from a file or from the scorer."""
  if not isinstance(scenarios, dict):
    raise SensitivityError(f"{label}: must be a JSON object")
  candidates = scenarios.get("candidates")
  if not isinstance(candidates, list):
    raise SensitivityError(f"{label}: candidates must be a list")
  for number, unit in enumerate(candidates, start=1):
    if not isinstance(unit, dict) or not isinstance(unit.get("id"), str):
      raise SensitivityError(f"{label}: candidate {number} needs a text id")
    if isinstance(unit.get("rank"), bool) or not isinstance(unit.get("rank"), int):
      raise SensitivityError(f"{label}: candidate {unit['id']} needs an integer rank")
    if not isinstance(unit.get("affected_community_ids"), list):
      raise SensitivityError(f"{label}: candidate {unit['id']} needs affected_community_ids as a list")


def _check_graph(graph: object) -> None:
  if not isinstance(graph, dict):
    raise SensitivityError("graph.json: must be a JSON object")
  for key in ("edges", "hospitals"):
    if not isinstance(graph.get(key), list):
      raise SensitivityError(f"graph.json: {key} must be a list")
  for hospital in graph["hospitals"]:
    if not isinstance(hospital, dict) or "id" not in hospital or "name" not in hospital:
      raise SensitivityError("graph.json: every hospital needs an id and a name")


def _as_json(value: object, label: str) -> object:
  """The value as it would read back from a file, so a tuple and a list with the same content compare equal."""
  try:
    return json.loads(json.dumps(value))
  except (TypeError, ValueError):
    raise SensitivityError(f"{label}: contains data that is not JSON-serializable") from None


def _run(kind: str, value: float | str, baseline: dict, scenarios: dict) -> dict:
  scenarios = _as_json(scenarios, "scorer output")
  _check_scenarios(scenarios, "scorer output")
  correlation, compared = rank_correlation(baseline, scenarios)
  return {
    "kind": kind,
    "value": value,
    "top5_overlap": top_overlap(baseline, scenarios, 5),
    "top10_overlap": top_overlap(baseline, scenarios, 10),
    "rank_correlation": correlation,
    "compared_units": compared,
  }


def build_report(graph: dict, units: list[dict], scenarios: dict, scorer: Scorer) -> dict:
  _check_graph(graph)
  _check_scenarios(scenarios, "scenarios.json")
  if _as_json(scorer(graph, units), "scorer output") != _as_json(scenarios, "scenarios.json"):
    raise SensitivityError("the baseline is not reproducible: scoring the unperturbed graph does not give scenarios.json")
  with_impact = len(_impact_ranks(scenarios))
  gradable = with_impact >= MIN_UNITS_WITH_IMPACT

  runs = []
  for factor in SPEEDS:
    run = _run("speed", factor, scenarios, scorer(speed_variant(graph, factor), units))
    if gradable:
      run["passes"] = run["top5_overlap"] >= THRESHOLDS["top5_min_overlap"]
    runs.append(run)

  skipped = []
  if len(graph["hospitals"]) < 2:
    skipped.append({"kind": "hospital", "reason": "only one referral hospital"})
  else:
    for hospital in graph["hospitals"]:
      runs.append(_run("hospital", hospital["name"], scenarios, scorer(hospital_variant(graph, hospital), units)))

  if not gradable:
    verdict = "insufficient_units"
  else:
    verdict = "pass" if all(run["passes"] for run in runs if run["kind"] == "speed") else "fail"
  return {
    "thresholds": THRESHOLDS,
    "baseline": {"unit_ids": [unit["id"] for unit in _ranked(scenarios)], "units_with_impact": with_impact},
    "runs": runs,
    "skipped": skipped,
    "verdict": verdict,
  }


def _read_json(path: Path):
  if not path.exists():
    raise SensitivityError(f"{path.name} not found in {path.parent}; run `make all` first")
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, ValueError) as exc:
    raise SensitivityError(f"{path.name}: cannot be read ({exc})") from None


def execute(output_dir: Path, work_dir: Path, reports_dir: Path, scorer: Scorer) -> Path:
  graph = _read_json(output_dir / "graph.json")
  scenarios = _read_json(output_dir / "scenarios.json")
  units = _read_json(work_dir / "closure_units.json")
  if not isinstance(units, list):
    raise SensitivityError("closure_units.json: must be a list of units")
  report = build_report(graph, units, scenarios, scorer)
  reports_dir.mkdir(parents=True, exist_ok=True)
  path = reports_dir / "sensitivity.json"
  path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  return path
