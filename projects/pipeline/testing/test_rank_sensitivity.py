import copy
import json
from pathlib import Path

import pytest

from pipeline.rank_sensitivity import (
  SensitivityError,
  build_report,
  execute,
  hospital_variant,
  rank_correlation,
  speed_variant,
  top_overlap,
)

UNITS = [{"id": f"T-{i:02d}", "edge_ids": [f"e{i}"], "length_m": 100.0} for i in range(1, 13)]
HOSPITALS = [{"id": f"h{i}", "name": f"Hospital {i}", "node": "n1"} for i in range(1, 4)]


def make_graph(hospitals=HOSPITALS, times=(100, 200)) -> dict:
  return {
    "nodes": [{"id": "n1", "lon": 0.0, "lat": 0.0}],
    "edges": [{"id": f"e{i}", "from": "n1", "to": "n1", "time_s": t, "road": "Ruta", "oneway": False} for i, t in enumerate(times, 1)],
    "hospitals": copy.deepcopy(hospitals),
    "communities": [{"id": "c1", "name": "C1", "node": "n1", "population": 10}],
  }


def ids(*numbers: int) -> list[str]:
  return [f"T-{n:02d}" for n in numbers]


def scenarios_of(order: list[str], with_impact: int | None = None) -> dict:
  """Scenarios in the given rank order; only the first `with_impact` units have an affected community."""
  count = len(order) if with_impact is None else with_impact
  return {
    "baseline": [],
    "candidates": [
      {"id": uid, "rank": rank, "affected_community_ids": ["c1"] if rank <= count else []}
      for rank, uid in enumerate(order, start=1)
    ],
  }


BASE_ORDER = ids(*range(1, 13))


class Stub:
  """Scorer stub: answers by (first edge time, hospital ids), and records every graph and units it receives."""

  def __init__(self, answers: dict, default=None):
    self.answers, self.default, self.calls = answers, default, []

  def __call__(self, graph: dict, units: list[dict]) -> dict:
    self.calls.append((copy.deepcopy(graph), units))
    key = (graph["edges"][0]["time_s"], tuple(h["id"] for h in graph["hospitals"]))
    return self.answers.get(key, self.default if self.default is not None else scenarios_of(BASE_ORDER))


def stub_for_speeds(slow: list[str], fast: list[str]) -> Stub:
  all_ids = ("h1", "h2", "h3")
  return Stub({(100, all_ids): scenarios_of(BASE_ORDER), (125, all_ids): scenarios_of(slow), (83, all_ids): scenarios_of(fast)})


# --- perturbations -------------------------------------------------------------------------------


def test_inv_03_speed_variant_divides_every_time_and_rounds_half_up():
  graph = make_graph(times=(3, 9, 5, 100))
  slow = speed_variant(graph, 0.8)  # 3/0.8 = 3.75, 9/0.8 = 11.25, 5/0.8 = 6.25, 100/0.8 = 125
  fast = speed_variant(graph, 1.2)  # 3/1.2 = 2.5 (half up: 3), 9/1.2 = 7.5 (8), 5/1.2 = 4.17, 100/1.2 = 83.3
  assert [e["time_s"] for e in slow["edges"]] == [4, 11, 6, 125]
  assert [e["time_s"] for e in fast["edges"]] == [3, 8, 4, 83]


def test_inv_03_speed_variant_changes_only_the_times_and_never_the_input():
  graph = make_graph()
  before = copy.deepcopy(graph)
  variant = speed_variant(graph, 1.2)
  assert graph == before
  assert variant["communities"] == before["communities"] and variant["hospitals"] == before["hospitals"]
  assert [{k: v for k, v in e.items() if k != "time_s"} for e in variant["edges"]] == [
    {k: v for k, v in e.items() if k != "time_s"} for e in before["edges"]
  ]


def test_inv_06_hospital_variant_keeps_every_other_hospital_and_drops_the_removed_one():
  graph = make_graph()
  before = copy.deepcopy(graph)
  variant = hospital_variant(graph, HOSPITALS[1])
  assert [h["id"] for h in variant["hospitals"]] == ["h1", "h3"]
  assert graph == before
  assert variant["edges"] == before["edges"] and variant["communities"] == before["communities"]


# --- measures ------------------------------------------------------------------------------------


def test_inv_07_top_overlap_counts_the_ids_shared_by_both_top_k():
  base = scenarios_of(BASE_ORDER)
  assert top_overlap(base, scenarios_of(BASE_ORDER), 5) == 5
  assert top_overlap(base, scenarios_of(ids(1, 2, 3, 5, 4, 6, 7, 8, 9, 10, 11, 12)), 5) == 5  # order inside the top 5 is free
  assert top_overlap(base, scenarios_of(ids(1, 2, 3, 4, 6, 5, 7, 8, 9, 10, 11, 12)), 5) == 4  # T-06 enters the top 5
  assert top_overlap(base, scenarios_of(ids(1, 2, 3, 4, 6, 5, 7, 8, 9, 10, 11, 12)), 4) == 4
  assert top_overlap(base, scenarios_of(ids(1, 2, 3, 6, 7, 4, 5, 8, 9, 10, 11, 12)), 5) == 3
  assert top_overlap(base, scenarios_of(ids(*range(6, 13), 1, 2, 3, 4, 5)), 5) == 0


def test_inv_07_top_overlap_uses_rank_not_list_order():
  shuffled = scenarios_of(BASE_ORDER)
  shuffled["candidates"].reverse()
  assert top_overlap(scenarios_of(BASE_ORDER), shuffled, 5) == 5


def test_inv_07_top_k_of_fewer_than_k_units_takes_them_all():
  few = scenarios_of(ids(1, 2, 3))
  assert top_overlap(few, few, 5) == 3 and top_overlap(few, few, 10) == 3


def test_inv_08_rank_correlation_is_one_for_the_same_order_and_minus_one_for_the_reverse():
  base = scenarios_of(ids(1, 2, 3, 4, 5))
  assert rank_correlation(base, scenarios_of(ids(1, 2, 3, 4, 5))) == (pytest.approx(1.0), 5)
  assert rank_correlation(base, scenarios_of(ids(5, 4, 3, 2, 1))) == (pytest.approx(-1.0), 5)


def test_inv_08_rank_correlation_matches_the_spearman_formula():
  # Unit ranks 1..5 against T-01:2, T-02:1, T-03:3, T-04:5, T-05:4: d = (-1, 1, 0, -1, 1), sum d^2 = 4 -> 1 - 6*4 / (5*24) = 0.8
  base = scenarios_of(ids(1, 2, 3, 4, 5))
  run = scenarios_of(ids(2, 1, 3, 5, 4))
  assert rank_correlation(base, run) == (pytest.approx(0.8), 5)


def test_inv_08_rank_correlation_uses_only_the_units_with_impact_in_both_runs():
  base = scenarios_of(ids(1, 2, 3, 4, 5, 6), with_impact=5)  # T-06 has no impact in the baseline
  run = scenarios_of(ids(6, 5, 4, 3, 2, 1), with_impact=4)  # only T-06, T-05, T-04, T-03 have impact
  value, compared = rank_correlation(base, run)
  assert compared == 3  # T-03, T-04, T-05 are in both
  assert value == pytest.approx(-1.0)


@pytest.mark.parametrize("with_impact", [0, 1])
def test_inv_08_rank_correlation_is_null_with_fewer_than_two_common_units(with_impact: int):
  base = scenarios_of(ids(1, 2, 3), with_impact=with_impact)
  assert rank_correlation(base, base) == (None, with_impact)


def test_inv_08_rank_correlation_is_null_when_two_units_have_no_spread():
  base = scenarios_of(ids(1, 2, 3))
  run = scenarios_of(ids(1, 2, 3))
  for c in run["candidates"]:
    c["rank"] = 1  # a tie of every rank: no spread, no correlation
  assert rank_correlation(base, run) == (None, 3)


def test_inv_08_rank_correlation_averages_the_ranks_of_ties():
  base = scenarios_of(ids(1, 2, 3, 4))
  run = scenarios_of(ids(1, 2, 3, 4))
  run["candidates"][0]["rank"], run["candidates"][1]["rank"] = 1, 1  # T-01 and T-02 tie at 1
  # run ranks 1,1,3,4 -> average ranks 1.5,1.5,3,4 against 1,2,3,4: Pearson = 0.9486832980505138
  assert rank_correlation(base, run)[0] == pytest.approx(0.9486832980505138)


# --- the report ----------------------------------------------------------------------------------


def report(slow, fast, graph=None, baseline=None, extra=None):
  graph = graph or make_graph()
  scorer = stub_for_speeds(slow, fast)
  if baseline:
    scorer.answers[(100, ("h1", "h2", "h3"))] = baseline  # the scorer reproduces whatever baseline is given
  if extra:
    scorer.answers.update(extra)
  return build_report(graph, UNITS, baseline or scenarios_of(BASE_ORDER), scorer), scorer


def test_inv_03_the_report_has_two_speed_runs_and_one_run_per_hospital():
  result, _ = report(BASE_ORDER, BASE_ORDER)
  assert [(r["kind"], r["value"]) for r in result["runs"]] == [
    ("speed", 0.8), ("speed", 1.2), ("hospital", "Hospital 1"), ("hospital", "Hospital 2"), ("hospital", "Hospital 3"),
  ]
  assert result["thresholds"] == {"top5_min_overlap": 4}
  assert result["skipped"] == []


def test_inv_03_the_scorer_gets_the_unperturbed_graph_and_then_each_perturbed_one():
  _, scorer = report(BASE_ORDER, BASE_ORDER)
  seen = [(g["edges"][0]["time_s"], [h["id"] for h in g["hospitals"]]) for g, _ in scorer.calls]
  assert seen == [
    (100, ["h1", "h2", "h3"]),  # the baseline reproduction
    (125, ["h1", "h2", "h3"]), (83, ["h1", "h2", "h3"]),
    (100, ["h2", "h3"]), (100, ["h1", "h3"]), (100, ["h1", "h2"]),
  ]
  assert all(units is UNITS for _, units in scorer.calls)


def test_inv_07_each_run_reports_its_overlaps_and_compared_units():
  slow = ids(1, 2, 3, 4, 6, 5, 7, 8, 9, 10, 11, 12)  # T-06 enters the top 5 and T-05 leaves it
  result, _ = report(slow, BASE_ORDER)
  first = result["runs"][0]
  assert (first["top5_overlap"], first["top10_overlap"], first["compared_units"]) == (4, 10, 12)
  assert result["baseline"] == {"unit_ids": BASE_ORDER, "units_with_impact": 12}


def test_inv_09_a_speed_run_passes_with_a_top5_overlap_of_at_least_4_and_the_verdict_follows():
  four = ids(1, 2, 3, 4, 6, 5, 7, 8, 9, 10, 11, 12)  # 4 shared
  four_of_five = ids(1, 2, 3, 4, 7, 5, 6, 8, 9, 10, 11, 12)  # 4 shared: T-01..T-04
  result, _ = report(four_of_five, four)
  assert [r["passes"] for r in result["runs"][:2]] == [True, True] and result["runs"][0]["top5_overlap"] == 4
  assert result["verdict"] == "pass"


def test_inv_09_three_shared_in_the_top5_fails_the_run_and_the_verdict():
  three = ids(1, 2, 3, 6, 7, 4, 5, 8, 9, 10, 11, 12)
  result, _ = report(three, BASE_ORDER)
  assert [r["passes"] for r in result["runs"][:2]] == [False, True]
  assert result["verdict"] == "fail"


def test_inv_09_hospital_runs_have_no_passes_and_never_change_the_verdict():
  worst = ids(*range(6, 13), 1, 2, 3, 4, 5)
  extra = {(100, ("h2", "h3")): scenarios_of(worst), (100, ("h1", "h3")): scenarios_of(worst), (100, ("h1", "h2")): scenarios_of(worst)}
  result, _ = report(BASE_ORDER, BASE_ORDER, extra=extra)
  hospital_runs = [r for r in result["runs"] if r["kind"] == "hospital"]
  assert all("passes" not in r for r in hospital_runs) and hospital_runs[0]["top5_overlap"] == 0
  assert result["verdict"] == "pass"


def test_inv_10_fewer_than_five_units_with_impact_gives_insufficient_units_and_no_passes():
  baseline = scenarios_of(BASE_ORDER, with_impact=4)
  result, _ = report(BASE_ORDER, BASE_ORDER, baseline=baseline)
  assert result["verdict"] == "insufficient_units"
  assert result["baseline"]["units_with_impact"] == 4
  assert all("passes" not in r for r in result["runs"])


def test_inv_10_exactly_five_units_with_impact_is_enough_to_grade():
  baseline = scenarios_of(BASE_ORDER, with_impact=5)
  result, _ = report(BASE_ORDER, BASE_ORDER, baseline=baseline)
  assert result["verdict"] == "pass"


def test_inv_11_a_single_referral_hospital_skips_the_removal_and_says_so():
  graph = make_graph(hospitals=HOSPITALS[:1])
  scorer = Stub({}, default=scenarios_of(BASE_ORDER))
  result = build_report(graph, UNITS, scenarios_of(BASE_ORDER), scorer)
  assert [r["kind"] for r in result["runs"]] == ["speed", "speed"]
  assert result["skipped"] == [{"kind": "hospital", "reason": "only one referral hospital"}]
  assert len(scorer.calls) == 3  # baseline + two speeds, no hospital run


def test_inv_01_a_baseline_the_scorer_reproduces_is_accepted():
  scenarios = scenarios_of(BASE_ORDER)
  assert build_report(make_graph(), UNITS, scenarios, Stub({}, default=copy.deepcopy(scenarios)))["verdict"] == "pass"


def test_inv_02_a_baseline_the_scorer_does_not_reproduce_is_an_error():
  other = scenarios_of(ids(2, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12))
  with pytest.raises(SensitivityError, match="baseline is not reproducible"):
    build_report(make_graph(), UNITS, scenarios_of(BASE_ORDER), Stub({}, default=other))


def test_inv_02_a_difference_in_any_field_counts_not_only_the_ranking():
  scenarios = scenarios_of(BASE_ORDER)
  changed = copy.deepcopy(scenarios)
  changed["candidates"][0]["criticality"] = 1
  with pytest.raises(SensitivityError, match="baseline is not reproducible"):
    build_report(make_graph(), UNITS, scenarios, Stub({}, default=changed))


def test_the_report_is_deterministic():
  first, _ = report(BASE_ORDER, BASE_ORDER)
  second, _ = report(BASE_ORDER, BASE_ORDER)
  assert json.dumps(first, sort_keys=False) == json.dumps(second, sort_keys=False)
  assert "generated" not in json.dumps(first) and "queried_on" not in first


# --- files ---------------------------------------------------------------------------------------


def make_files(tmp_path: Path, scenarios: dict | None = None) -> tuple[Path, Path, Path]:
  output, work, reports = tmp_path / "output", tmp_path / "work", tmp_path / "reports"
  output.mkdir()
  work.mkdir()
  (output / "graph.json").write_text(json.dumps(make_graph()), encoding="utf-8")
  if scenarios is not None:
    (output / "scenarios.json").write_text(json.dumps(scenarios), encoding="utf-8")
  (work / "closure_units.json").write_text(json.dumps(UNITS), encoding="utf-8")
  return output, work, reports


def test_execute_writes_the_report_to_reports_and_returns_its_path(tmp_path: Path):
  output, work, reports = make_files(tmp_path, scenarios_of(BASE_ORDER))
  path = execute(output, work, reports, Stub({}, default=scenarios_of(BASE_ORDER)))
  assert path == reports / "sensitivity.json"
  assert json.loads(path.read_text(encoding="utf-8"))["verdict"] == "pass"


def test_inv_14_a_missing_scenarios_file_says_to_run_make_all_and_writes_no_report(tmp_path: Path):
  output, work, reports = make_files(tmp_path, scenarios=None)
  with pytest.raises(SensitivityError, match="make all"):
    execute(output, work, reports, Stub({}))
  assert not (reports / "sensitivity.json").exists()


def test_inv_02_a_non_reproducible_baseline_writes_no_report(tmp_path: Path):
  output, work, reports = make_files(tmp_path, scenarios_of(BASE_ORDER))
  other = scenarios_of(ids(2, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12))
  with pytest.raises(SensitivityError, match="not reproducible"):
    execute(output, work, reports, Stub({}, default=other))
  assert not (reports / "sensitivity.json").exists()


def test_inv_14_a_scenarios_file_that_is_not_json_is_a_clean_error(tmp_path: Path):
  output, work, reports = make_files(tmp_path, scenarios_of(BASE_ORDER))
  (output / "scenarios.json").write_text("{nope", encoding="utf-8")
  with pytest.raises(SensitivityError, match="scenarios.json"):
    execute(output, work, reports, Stub({}))
  assert not (reports / "sensitivity.json").exists()


def test_inv_01_exposure_added_after_scoring_does_not_break_the_baseline():
  scenarios = scenarios_of(BASE_ORDER)
  for unit in scenarios["candidates"]:
    unit["exposure"] = {"rain_mm_12d": 12.5}
  report = build_report(make_graph(), UNITS, scenarios, Stub({}))
  assert report["baseline"]["unit_ids"] == BASE_ORDER
