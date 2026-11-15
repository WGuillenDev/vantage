import argparse
import json
import math
import re
import statistics
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable

from .area_config import PIPELINE_DIR, ConfigError, load_zone

REPORTS_DIR = PIPELINE_DIR / "reports"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
ROUTER_NAME = "OSRM public demo, driving profile"
LIMITATION = "the router uses OpenStreetMap too, so it checks the calculation, not ground truth"
USER_AGENT = "vantage-timecheck"  # generic on purpose: no name, email or machine data
THRESHOLD = {"median_relative_error": 0.25, "min_pairs": 15}
MAX_PAIRS = 20
MIN_SECONDS_BETWEEN_REQUESTS = 1.0

Fetch = Callable[[str, dict], tuple[int, str]]


class CrossCheckError(Exception):
  pass


def http_fetch(url: str, headers: dict) -> tuple[int, str]:
  try:
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
      return response.status, response.read().decode("utf-8")
  except urllib.error.HTTPError as exc:
    return exc.code, ""


def _id_number(identifier: str) -> int:
  match = re.search(r"\d+", identifier)
  return int(match.group()) if match else 0


def _positions(n: int) -> list[int]:
  k = min(MAX_PAIRS, n)
  if k == 0:
    return []
  if k == 1:
    return [0]
  # Round half up in integers so the positions never depend on float rounding.
  return [(2 * i * (n - 1) + (k - 1)) // (2 * (k - 1)) for i in range(k)]


def build_sample(graph: dict, baseline: list[dict]) -> list[dict]:
  """Up to 20 communities with a baseline route, at evenly spaced positions of the list sorted by time, then id number."""
  routed = [row for row in baseline if row["time_s"] is not None and row["hospital_id"] is not None]
  routed.sort(key=lambda row: (row["time_s"], _id_number(row["community_id"])))
  return [
    {"community_id": routed[p]["community_id"], "hospital_id": routed[p]["hospital_id"], "model_s": routed[p]["time_s"]}
    for p in _positions(len(routed))
  ]


def _coordinates(graph: dict) -> dict[str, tuple[float, float]]:
  nodes = {node["id"]: (node["lon"], node["lat"]) for node in graph["nodes"]}
  coordinates = {}
  for kind in ("communities", "hospitals"):
    for item in graph[kind]:
      if item["node"] not in nodes:
        raise CrossCheckError(f"graph.json: {kind} {item['id']} points to the missing node {item['node']}")
      coordinates[item["id"]] = nodes[item["node"]]
  return coordinates


def _route_seconds(fetch: Fetch, origin: tuple[float, float], destination: tuple[float, float]) -> float | None:
  url = f"{OSRM_URL}/{origin[0]},{origin[1]};{destination[0]},{destination[1]}?overview=false"
  try:
    status, body = fetch(url, {"User-Agent": USER_AGENT})
  except OSError as exc:
    raise CrossCheckError(f"network failure while querying the router: {exc}") from None
  if status != 200:
    raise CrossCheckError(f"the router answered HTTP {status}")
  try:
    answer = json.loads(body)
  except json.JSONDecodeError:
    raise CrossCheckError("the router answered HTTP 200 with a body that is not JSON") from None
  if not isinstance(answer, dict):
    raise CrossCheckError("the router answered with an unexpected shape")
  if answer.get("code") != "Ok" or not answer.get("routes"):
    return None
  route = answer["routes"][0]
  duration = route.get("duration") if isinstance(route, dict) else None
  if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration):
    raise CrossCheckError("the router answered with an unexpected shape")
  # A zero duration means both points snapped to the same spot: no usable time, and it cannot be a divisor.
  return duration if duration > 0 else None


def load_references(path: Path) -> list[dict]:
  if not path.exists():
    return []
  try:
    entries = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, ValueError) as exc:
    raise CrossCheckError(f"{path.name}: cannot be read ({exc})") from None
  if not isinstance(entries, list):
    raise CrossCheckError(f"{path.name}: must be a list of entries")
  for number, entry in enumerate(entries, start=1):
    label = f"{path.name}: entry {number} ({entry.get('community_id') if isinstance(entry, dict) else '?'})"
    if not isinstance(entry, dict):
      raise CrossCheckError(f"{label}: must be an object")
    for key in ("community_id", "hospital_id", "source", "accessed_on"):
      value = entry.get(key)
      if not isinstance(value, str) or not value.strip():
        raise CrossCheckError(f"{label}: {key} is missing or empty")
    minutes = entry.get("minutes")
    if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or not (math.isfinite(minutes) and minutes > 0):
      raise CrossCheckError(f"{label}: minutes must be a finite number greater than 0")
  return entries


def _reference_row(entry: dict, baseline: dict[str, dict]) -> dict:
  row = baseline.get(entry["community_id"])
  # The baseline only holds the time to the nearest referral hospital: for any other hospital there is no model time.
  model_s = row["time_s"] if row and row["hospital_id"] == entry["hospital_id"] else None
  reference_s = entry["minutes"] * 60
  return {**entry, "model_s": model_s, "relative_error": None if model_s is None else abs(model_s - reference_s) / reference_s}


def build_report(
  graph: dict,
  scenarios: dict,
  references: list[dict],
  fetch: Fetch,
  sleep: Callable[[float], None] = time.sleep,
  today: str | None = None,
) -> dict:
  coordinates = _coordinates(graph)
  baseline = {row["community_id"]: row for row in scenarios["baseline"]}
  selected = build_sample(graph, scenarios["baseline"])
  for row in selected:
    for kind, key in (("community", "community_id"), ("hospital", "hospital_id")):
      if row[key] not in coordinates:
        raise CrossCheckError(f"scenarios.json: baseline {kind} {row[key]} is not in graph.json")
  pairs = []
  for index, sample in enumerate(selected):
    if index:
      sleep(MIN_SECONDS_BETWEEN_REQUESTS)
    router_s = _route_seconds(fetch, coordinates[sample["community_id"]], coordinates[sample["hospital_id"]])
    pairs.append({
      **sample,
      "router_s": router_s,
      "relative_error": None if router_s is None else abs(sample["model_s"] - router_s) / router_s,
    })
  timed = [pair for pair in pairs if pair["router_s"] is not None]
  median_error = statistics.median(p["relative_error"] for p in timed) if timed else None
  median_bias = statistics.median((p["model_s"] - p["router_s"]) / p["router_s"] for p in timed) if timed else None
  if len(timed) < THRESHOLD["min_pairs"]:
    verdict = "insufficient_pairs"
  else:
    verdict = "pass" if median_error <= THRESHOLD["median_relative_error"] else "fail"
  return {
    "router": ROUTER_NAME,
    "queried_on": today or date.today().isoformat(),
    "limitation": LIMITATION,
    "threshold": THRESHOLD,
    "pairs": pairs,
    "excluded": len(pairs) - len(timed),
    "median_relative_error": median_error,
    "median_bias": median_bias,
    "references": [_reference_row(entry, baseline) for entry in references],
    "verdict": verdict,
  }


def _read_json(path: Path) -> dict:
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, ValueError) as exc:
    raise CrossCheckError(f"{path.name}: cannot be read ({exc})") from None


def execute(
  output_dir: Path,
  reports_dir: Path,
  fetch: Fetch | None = None,
  sleep: Callable[[float], None] = time.sleep,
  today: str | None = None,
) -> Path:
  graph = _read_json(output_dir / "graph.json")
  scenarios = _read_json(output_dir / "scenarios.json")
  references = load_references(reports_dir / "reference_times.json")  # checked before any request
  report = build_report(graph, scenarios, references, fetch or http_fetch, sleep, today)
  reports_dir.mkdir(parents=True, exist_ok=True)
  path = reports_dir / "time_crosscheck.json"
  path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  return path


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="timecheck", description="Compare model travel times with an OSRM router.")
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  args = parser.parse_args(argv)
  try:
    zone = load_zone(args.area)
    path = execute(zone.output_dir, REPORTS_DIR / zone.id)
  except (ConfigError, CrossCheckError) as exc:
    raise SystemExit(str(exc)) from None
  print(f"{zone.id}: report written to {path}")
