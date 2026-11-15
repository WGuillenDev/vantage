import json
from pathlib import Path

import pytest

from pipeline.time_crosscheck import CrossCheckError, _positions, build_report, execute
from test_time_crosscheck import Router, make_zone_files, report_for, world

TODAY = "2026-11-15"


@pytest.mark.parametrize("n", range(1, 301))
def test_inv_01_positions_are_distinct_ascending_and_span_the_list(n: int):
  positions = _positions(n)
  k = min(20, n)
  assert len(positions) == k
  assert positions == sorted(set(positions))
  assert positions[0] == 0
  if k > 1:
    assert positions[-1] == n - 1
  assert all(0 <= p < n for p in positions)


def test_inv_01_positions_of_an_empty_list_is_empty():
  assert _positions(0) == []


def test_inv_05_an_even_number_of_pairs_averages_the_two_middle_errors():
  # 16 pairs: 8 with error 0.2 and 8 with error 0.3 -> median (0.2 + 0.3) / 2 = 0.25 -> pass (at most 0.25)
  times = [120.0] * 8 + [130.0] * 8
  report = report_for(times, [100.0] * 16)
  assert report["median_relative_error"] == pytest.approx(0.25)
  assert report["verdict"] == "pass"


def test_inv_04_a_baseline_time_of_zero_gives_a_relative_error_of_one():
  report = report_for([0.0], [100.0])
  assert report["pairs"][0]["relative_error"] == 1.0 and report["median_bias"] == -1.0


def test_inv_10_a_missing_graph_file_is_a_clean_error_and_writes_no_report(tmp_path: Path):
  output, reports = make_zone_files(tmp_path, [100.0])
  (output / "graph.json").unlink()
  with pytest.raises(CrossCheckError, match="graph.json"):
    execute(output, reports, Router([100.0]), lambda s: None, TODAY)
  assert not (reports / "time_crosscheck.json").exists()


def test_inv_10_a_scenarios_file_that_is_not_json_is_a_clean_error(tmp_path: Path):
  output, reports = make_zone_files(tmp_path, [100.0])
  (output / "scenarios.json").write_text("{not json", encoding="utf-8")
  with pytest.raises(CrossCheckError, match="scenarios.json"):
    execute(output, reports, Router([100.0]), lambda s: None, TODAY)


def test_a_graph_node_that_a_community_points_to_must_exist():
  graph, scenarios = world([100.0])
  graph["communities"][0]["node"] = "nowhere"
  with pytest.raises(CrossCheckError, match="nowhere"):
    build_report(graph, scenarios, [], Router([100.0]), lambda s: None, TODAY)


def test_the_written_report_is_strict_json_with_the_documented_fields(tmp_path: Path):
  output, reports = make_zone_files(tmp_path, [100.0, 200.0])
  path = execute(output, reports, Router([100.0, None]), lambda s: None, TODAY)

  def refuse(constant: str):
    raise ValueError(constant)

  report = json.loads(path.read_text(encoding="utf-8"), parse_constant=refuse)
  assert set(report) == {
    "router", "queried_on", "limitation", "threshold", "pairs", "excluded",
    "median_relative_error", "median_bias", "references", "verdict",
  }
  assert set(report["pairs"][0]) == {"community_id", "hospital_id", "model_s", "router_s", "relative_error"}
  assert report["excluded"] == 1


def test_inv_01_a_baseline_row_needs_both_a_time_and_a_hospital_to_enter_the_sample():
  graph, scenarios = world([100.0, 200.0, 300.0])
  scenarios["baseline"][0]["hospital_id"] = None  # time but no hospital
  scenarios["baseline"][1]["time_s"] = None  # hospital but no time
  report = build_report(graph, scenarios, [], Router([300.0]), lambda s: None, TODAY)
  assert [p["community_id"] for p in report["pairs"]] == ["c3"]
