import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline import time_crosscheck
from pipeline.time_crosscheck import CrossCheckError, build_report, build_sample, execute, load_references, main

TODAY = "2026-11-15"


def world(times: list[float | None]) -> tuple[dict, dict]:
  """One community per entry (c1..cn) and one hospital; a None time means no baseline route."""
  nodes = [{"id": f"n{i}", "lon": -84.0 + 0.01 * i, "lat": 10.0} for i in range(1, len(times) + 1)]
  nodes.append({"id": "nh", "lon": -83.9, "lat": 10.1})
  graph = {
    "nodes": nodes,
    "hospitals": [{"id": "h1", "name": "Hospital", "node": "nh"}],
    "communities": [{"id": f"c{i}", "name": f"C{i}", "node": f"n{i}", "population": None} for i in range(1, len(times) + 1)],
  }
  baseline = [
    {"community_id": f"c{i}", "time_s": t, "hospital_id": None if t is None else "h1"}
    for i, t in enumerate(times, start=1)
  ]
  return graph, {"baseline": baseline}


class Router:
  """Stub for the OSRM server: answers the durations in order, records the URLs and the headers."""

  def __init__(self, durations: list[float | None], status: int = 200):
    self.durations = durations
    self.status = status
    self.urls: list[str] = []
    self.headers: list[dict] = []

  def __call__(self, url: str, headers: dict) -> tuple[int, str]:
    self.urls.append(url)
    self.headers.append(headers)
    duration = self.durations[len(self.urls) - 1]
    if duration is None:
      return self.status, json.dumps({"code": "NoRoute", "message": "Impossible route between points"})
    return self.status, json.dumps({"code": "Ok", "routes": [{"duration": duration}]})


def report_for(times, durations, references=None):
  graph, scenarios = world(times)
  sleeps: list[float] = []
  return build_report(graph, scenarios, references or [], Router(durations), sleeps.append, TODAY)


def test_inv_01_sample_takes_every_community_when_there_are_20_or_fewer():
  graph, scenarios = world([300.0, 100.0, 200.0])
  assert [p["community_id"] for p in build_sample(graph, scenarios["baseline"])] == ["c2", "c3", "c1"]


def test_inv_01_sample_sorts_by_time_then_by_id_number_not_text():
  graph, scenarios = world([100.0] * 12)
  sample = build_sample(graph, scenarios["baseline"])
  assert [p["community_id"] for p in sample] == [f"c{i}" for i in range(1, 13)]  # c2 before c10


def test_inv_01_sample_takes_20_evenly_spaced_of_a_longer_list():
  graph, scenarios = world([float(i) for i in range(1, 42)])  # 41 communities, times ascend with the id
  ids = [p["community_id"] for p in build_sample(graph, scenarios["baseline"])]
  assert len(ids) == 20
  assert ids[0] == "c1" and ids[-1] == "c41"
  assert ids == sorted(set(ids), key=lambda cid: int(cid[1:]))  # no repeats, ascending
  gaps = {int(b[1:]) - int(a[1:]) for a, b in zip(ids, ids[1:])}
  assert gaps <= {2, 3}


def test_inv_01_sample_skips_communities_without_a_baseline_route_and_is_deterministic():
  graph, scenarios = world([100.0, None, 300.0, 200.0])
  first = build_sample(graph, scenarios["baseline"])
  assert [p["community_id"] for p in first] == ["c1", "c4", "c3"]
  assert build_sample(graph, list(reversed(scenarios["baseline"]))) == first


def test_inv_01_sample_of_nothing_is_empty():
  graph, scenarios = world([None, None])
  assert build_sample(graph, scenarios["baseline"]) == []


def test_inv_02_queries_use_the_graph_coordinates_of_the_community_and_its_hospital():
  graph, scenarios = world([100.0])
  router = Router([90.0])
  build_report(graph, scenarios, [], router, lambda s: None, TODAY)
  assert len(router.urls) == 1
  assert "/route/v1/driving/-83.99,10.0;-83.9,10.1" in router.urls[0]


def test_inv_06_a_pair_without_a_route_is_null_left_out_of_the_medians_and_counted():
  report = report_for([100.0, 200.0, 300.0], [100.0, None, 300.0])
  by_id = {p["community_id"]: p for p in report["pairs"]}
  assert by_id["c2"]["router_s"] is None and by_id["c2"]["relative_error"] is None
  assert report["excluded"] == 1
  assert report["median_relative_error"] == 0 and report["median_bias"] == 0


def test_inv_06_a_router_duration_of_zero_counts_as_no_route():
  report = report_for([100.0, 200.0], [0.0, 200.0])
  assert [p["router_s"] for p in report["pairs"]] == [None, 200.0]
  assert report["excluded"] == 1


def test_inv_04_medians_are_over_the_pairs_with_a_router_time():
  # Pairs go in baseline-time order (60, 100, 100): 60/100 (-0.4), 100/50 (+1.0), 100/100 (0); median error 0.4, signed median 0
  report = report_for([100.0, 100.0, 60.0], [100.0, 50.0, 100.0])
  assert report["median_relative_error"] == pytest.approx(0.4)
  assert report["median_bias"] == pytest.approx(0.0)
  errors = {p["model_s"]: p["relative_error"] for p in report["pairs"] if p["router_s"] == 100.0}
  assert errors == {100.0: 0.0, 60.0: pytest.approx(0.4)}


def test_inv_04_bias_keeps_its_sign_when_the_model_is_slower_or_faster():
  slower = report_for([200.0, 300.0, 400.0], [100.0, 100.0, 100.0])
  faster = report_for([50.0, 40.0, 30.0], [100.0, 100.0, 100.0])
  assert slower["median_bias"] == pytest.approx(2.0) and slower["median_relative_error"] == pytest.approx(2.0)
  assert faster["median_bias"] == pytest.approx(-0.6) and faster["median_relative_error"] == pytest.approx(0.6)


def test_inv_04_no_pair_with_a_router_time_gives_null_medians():
  report = report_for([100.0], [None])
  assert report["median_relative_error"] is None and report["median_bias"] is None


def verdict(n_pairs: int, router_times: list[float | None] | None = None, model: float = 100.0, router: float = 100.0):
  durations = router_times if router_times is not None else [router] * n_pairs
  return report_for([model] * n_pairs, durations)["verdict"]


def test_inv_05_pass_needs_15_pairs_and_a_median_within_the_threshold():
  assert verdict(15) == "pass"
  assert verdict(15, model=125.0) == "pass"  # exactly 0.25
  assert verdict(15, model=125.01) == "fail"


def test_inv_05_fewer_than_15_pairs_with_a_router_time_is_insufficient():
  assert verdict(14) == "insufficient_pairs"
  assert verdict(15, [100.0] * 14 + [None]) == "insufficient_pairs"
  assert verdict(15, [100.0] * 14 + [None], model=1000.0) == "insufficient_pairs"  # bad median, still not graded


def test_inv_05_threshold_and_fixed_text_are_in_the_report():
  report = report_for([100.0], [100.0])
  assert report["threshold"] == {"median_relative_error": 0.25, "min_pairs": 15}
  assert report["router"] == "OSRM public demo, driving profile"
  assert report["queried_on"] == TODAY
  assert report["limitation"] == "the router uses OpenStreetMap too, so it checks the calculation, not ground truth"


def reference(**over) -> dict:
  entry = {"community_id": "c1", "hospital_id": "h1", "minutes": 2.0, "source": "A cited page", "accessed_on": "2026-11-14"}
  entry.update(over)
  return entry


def test_references_report_model_time_and_error_without_grading():
  report = report_for([100.0, 200.0], [100.0, 200.0], [reference(minutes=2.0)])
  assert report["references"] == [{**reference(minutes=2.0), "model_s": 100.0, "relative_error": pytest.approx(1 / 6)}]
  assert report["verdict"] == "insufficient_pairs"


def test_references_to_a_hospital_other_than_the_baseline_one_have_no_model_time():
  report = report_for([100.0], [100.0], [reference(hospital_id="h2")])
  assert report["references"][0]["model_s"] is None and report["references"][0]["relative_error"] is None


def write_references(tmp_path: Path, entries) -> Path:
  path = tmp_path / "reference_times.json"
  path.write_text(json.dumps(entries), encoding="utf-8")
  return path


@pytest.mark.parametrize("missing", ["source", "accessed_on"])
@pytest.mark.parametrize("value", [None, "", "  "])
def test_inv_07_a_reference_without_source_or_date_is_an_error_naming_the_entry(tmp_path: Path, missing: str, value):
  entries = [reference(), reference(community_id="c7")]
  entries[1][missing] = value
  with pytest.raises(CrossCheckError, match=rf"entry 2 \(c7\).*{missing}"):
    load_references(write_references(tmp_path, entries))


def test_inv_07_an_absent_key_is_also_an_error(tmp_path: Path):
  entry = reference()
  del entry["source"]
  with pytest.raises(CrossCheckError, match="entry 1 .*source"):
    load_references(write_references(tmp_path, [entry]))


def test_inv_07_a_missing_references_file_means_no_references(tmp_path: Path):
  assert load_references(tmp_path / "nope.json") == []


def make_zone_files(tmp_path: Path, times: list[float | None]) -> tuple[Path, Path]:
  graph, scenarios = world(times)
  output = tmp_path / "output"
  output.mkdir()
  (output / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
  (output / "scenarios.json").write_text(json.dumps(scenarios), encoding="utf-8")
  return output, tmp_path / "reports"


def test_inv_07_a_bad_reference_stops_before_any_request_and_writes_no_report(tmp_path: Path):
  output, reports = make_zone_files(tmp_path, [100.0])
  reports.mkdir()
  write_references(reports, [reference(source="")]).rename(reports / "reference_times.json")
  router = Router([100.0])
  with pytest.raises(CrossCheckError, match="source"):
    execute(output, reports, router, lambda s: None, TODAY)
  assert router.urls == []
  assert not (reports / "time_crosscheck.json").exists()


def test_inv_07_main_exits_with_a_non_zero_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
  output, reports = make_zone_files(tmp_path, [100.0])
  reports.mkdir()
  write_references(reports, [reference(accessed_on="")]).rename(reports / "reference_times.json")
  monkeypatch.setattr(time_crosscheck, "load_zone", lambda zone_id: SimpleNamespace(id="z", output_dir=output))
  monkeypatch.setattr(time_crosscheck, "REPORTS_DIR", tmp_path / "all_reports")
  (tmp_path / "all_reports" / "z").mkdir(parents=True)
  (tmp_path / "all_reports" / "z" / "reference_times.json").write_text((reports / "reference_times.json").read_text())
  monkeypatch.setattr(time_crosscheck, "http_fetch", Router([100.0]))
  with pytest.raises(SystemExit) as exit_info:
    main(["--area", "z"])
  assert "accessed_on" in str(exit_info.value)
  assert not (tmp_path / "all_reports" / "z" / "time_crosscheck.json").exists()


def test_inv_09_requests_carry_a_generic_client_name_and_wait_a_second_between_them():
  graph, scenarios = world([100.0, 200.0, 300.0])
  router, sleeps = Router([100.0, 200.0, 300.0]), []
  build_report(graph, scenarios, [], router, sleeps.append, TODAY)
  assert len(sleeps) == 2 and all(s >= 1.0 for s in sleeps)
  for headers in router.headers:
    agent = headers["User-Agent"]
    assert agent == time_crosscheck.USER_AGENT
    assert "@" not in agent and "/Users" not in agent and "\\" not in agent


@pytest.mark.parametrize("status", [400, 429, 500])
def test_inv_10_an_error_status_is_an_error_naming_it_and_writes_no_report(tmp_path: Path, status: int):
  output, reports = make_zone_files(tmp_path, [100.0, 200.0])
  with pytest.raises(CrossCheckError, match=str(status)):
    execute(output, reports, Router([100.0, 200.0], status=status), lambda s: None, TODAY)
  assert not (reports / "time_crosscheck.json").exists()


def test_inv_10_a_network_failure_is_an_error_and_writes_no_report(tmp_path: Path):
  output, reports = make_zone_files(tmp_path, [100.0])

  def broken(url: str, headers: dict):
    raise OSError("connection refused")

  with pytest.raises(CrossCheckError, match="network"):
    execute(output, reports, broken, lambda s: None, TODAY)
  assert not (reports / "time_crosscheck.json").exists()


def test_inv_10_a_failure_in_a_later_pair_still_writes_no_report(tmp_path: Path):
  output, reports = make_zone_files(tmp_path, [100.0, 200.0])
  calls = []

  def second_fails(url: str, headers: dict):
    calls.append(url)
    return (200, json.dumps({"code": "Ok", "routes": [{"duration": 100.0}]})) if len(calls) == 1 else (503, "")

  with pytest.raises(CrossCheckError, match="503"):
    execute(output, reports, second_fails, lambda s: None, TODAY)
  assert not (reports / "time_crosscheck.json").exists()


def test_execute_writes_the_report_to_reports_and_returns_its_path(tmp_path: Path):
  output, reports = make_zone_files(tmp_path, [100.0, 200.0])
  path = execute(output, reports, Router([100.0, 200.0]), lambda s: None, TODAY)
  assert path == reports / "time_crosscheck.json"
  assert json.loads(path.read_text(encoding="utf-8"))["verdict"] == "insufficient_pairs"
