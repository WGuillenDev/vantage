import builtins
import copy
import json
from pathlib import Path

import pytest

from pipeline import impact_scoring
from pipeline.area_config import Zone
from pipeline.impact_scoring import ImpactScoringError, score
from pipeline.validate import _check_graph, _check_scenarios, _schema_errors

MOCK = Path(__file__).resolve().parents[2] / "contract" / "examples" / "mock-validated"
ZONE_ALTERNATES = (("Ruta 126", "light"), ("Ruta 10", "freight"))


# --- builders: small graphs that also satisfy the graph schema ---


def edge(eid: str, a: str, b: str, seconds: int, oneway: bool = False, unit: str | None = None) -> dict:
  return {
    "id": eid, "from": a, "to": b, "length_m": seconds, "time_s": seconds, "road": None,
    "oneway": oneway, "candidate_id": unit, "geometry": [[10.0, 0.0], [10.0, 0.001]],
  }


def make_graph(edges: list[dict], hospitals: list[tuple[str, str]], communities: list[tuple]) -> dict:
  ends = sorted({n for e in edges for n in (e["from"], e["to"])} | {n for _, n in hospitals} | {c[1] for c in communities})
  return {
    "schema_version": "0.3",
    "nodes": [{"id": n, "lon": 10.0, "lat": 0.0} for n in ends],
    "edges": edges,
    "hospitals": [{"id": h, "name": f"Hospital {h}", "node": n} for h, n in hospitals],
    "communities": [{"id": c, "name": f"Community {c}", "node": n, "population": p} for c, n, p in communities],
  }


def unit(uid: str, *edge_ids: str, length: int = 1000) -> dict:
  return {"id": uid, "edge_ids": list(edge_ids), "length_m": length}


def two_paths(pop1=10, pop2=20, pop3=None) -> dict:
  """Hospital h1 at n1. c1 at n2 and c2 at n3 reach it through e1 (n1-n2) or, the long way, e3 (n3-n1).

  Closing e1: c1 goes 100 -> 400 (+300) and c2 goes 200 -> 300 (+100). Closing e1 and e3 cuts both off.
  c3 at n4 hangs from n3 by e4; e5 is a stray edge that nobody uses.
  """
  return make_graph(
    [edge("e1", "n1", "n2", 100), edge("e2", "n2", "n3", 100), edge("e3", "n3", "n1", 300), edge("e4", "n4", "n3", 50), edge("e5", "n6", "n7", 10)],
    [("h1", "n1")],
    [("c1", "n2", pop1), ("c2", "n3", pop2), ("c3", "n4", pop3)],
  )


def by_unit(scenarios: dict) -> dict[str, dict]:
  return {c["id"]: c for c in scenarios["candidates"]}


def mock_inputs() -> tuple[dict, list[dict], dict]:
  graph = json.loads((MOCK / "graph.json").read_text(encoding="utf-8"))
  expected = json.loads((MOCK / "scenarios.json").read_text(encoding="utf-8"))
  units = [{"id": c["id"], "edge_ids": c["edge_ids"], "length_m": c["length_m"]} for c in expected["candidates"]]
  return graph, units, expected


# --- baseline, affected, isolated (INV-02 to INV-06, INV-09, INV-13) ---


def test_inv02_baseline_lists_every_community_once_with_its_nearest_hospital():
  graph = make_graph(
    [edge("e1", "n3", "n1", 100), edge("e2", "n3", "n5", 100), edge("e3", "n7", "n8", 50)],
    [("h10", "n5"), ("h2", "n1")],
    [("c2", "n7", None), ("c1", "n3", 5)],
  )
  baseline = score(graph, [])["baseline"]
  assert [b["community_id"] for b in baseline] == ["c1", "c2"]
  assert baseline[0] == {"community_id": "c1", "time_s": 100, "hospital_id": "h2"}
  assert baseline[1] == {"community_id": "c2", "time_s": None, "hospital_id": None}  # no route even before any closure


def test_inv13_equal_route_times_go_to_the_lowest_hospital_number():
  graph = make_graph(
    [edge("e1", "n3", "n1", 100), edge("e2", "n3", "n5", 100)], [("h10", "n5"), ("h2", "n1")], [("c1", "n3", None)]
  )
  assert score(graph, [])["baseline"][0]["hospital_id"] == "h2"  # h2 before h10, not by text order


def test_inv03_affected_means_it_had_a_route_and_lost_time_or_the_route():
  graph = two_paths()
  graph["edges"].append(edge("e6", "n8", "n9", 10))
  graph["communities"].append({"id": "c4", "name": "No route", "node": "n8", "population": 7})
  scenarios = score(graph, [unit("T-01", "e2"), unit("T-02", "e1")])
  # e2 closed: c2 loses its short way (200 -> 300) and c3 hangs from c2's node; c1 keeps its direct edge.
  assert by_unit(scenarios)["T-01"]["affected_community_ids"] == ["c2", "c3"]
  # c4 never had a route, so it is never affected, whatever is closed.
  assert "c4" not in by_unit(scenarios)["T-02"]["affected_community_ids"]


def test_inv03_a_community_whose_time_does_not_change_is_not_affected():
  scenarios = score(two_paths(), [unit("T-01", "e3")])
  assert by_unit(scenarios)["T-01"]["affected_community_ids"] == []


def test_inv04_per_community_lists_exactly_the_affected_ones():
  unit_t = by_unit(score(two_paths(), [unit("T-01", "e1")]))["T-01"]
  assert [p["community_id"] for p in unit_t["per_community"]] == unit_t["affected_community_ids"] == ["c1", "c2", "c3"]
  c1 = unit_t["per_community"][0]
  assert (c1["time_s"], c1["extra_s"], c1["hospital_id"]) == (400, 300, "h1")


def test_inv05_a_community_with_no_route_left_is_isolated_with_null_values():
  unit_t = by_unit(score(two_paths(), [unit("T-01", "e1", "e3")]))["T-01"]
  assert unit_t["isolated_community_ids"] == ["c1", "c2", "c3"]
  for row in unit_t["per_community"]:
    assert (row["time_s"], row["extra_s"], row["hospital_id"]) == (None, None, None)


def test_inv06_extra_time_is_the_maximum_over_affected_non_isolated_communities():
  scenarios = by_unit(score(two_paths(), [unit("T-01", "e1"), unit("T-02", "e1", "e3"), unit("T-03", "e3")]))
  assert scenarios["T-01"]["extra_time_s"] == 300  # c1 +300, c2 +100, c3 +100
  assert scenarios["T-02"]["extra_time_s"] is None  # every affected community is isolated
  assert scenarios["T-03"]["extra_time_s"] == 0  # nobody is affected: measured, not unknown


def test_inv09_population_dependent_sums_the_known_populations_of_the_affected():
  full = by_unit(score(two_paths(10, 20, 5), [unit("T-01", "e1")]))["T-01"]
  assert full["population_dependent"] == 35
  partial = by_unit(score(two_paths(10, None, None), [unit("T-01", "e1")]))["T-01"]
  assert partial["population_dependent"] == 10
  unknown = by_unit(score(two_paths(None, None, None), [unit("T-01", "e1")]))["T-01"]
  assert unknown["population_dependent"] is None  # affected, but nobody's population is known


# --- criticality and the penalty (INV-07, INV-08) ---


def test_inv07_criticality_is_population_times_extra_and_null_population_adds_zero():
  graph = two_paths(10, 20, None)
  # c1 +300 x 10, c2 +100 x 20, c3 (+100) has no population.
  assert by_unit(score(graph, [unit("T-01", "e1")]))["T-01"]["criticality"] == 3000 + 2000


def test_inv07_isolated_communities_use_the_penalty_as_their_extra():
  scenarios = by_unit(score(two_paths(10, 20, 4), [unit("T-01", "e1"), unit("T-02", "e1", "e3")]))
  # The penalty is 300 (the largest finite extra of T-01), so T-02 is (10 + 20 + 4) x 300.
  assert scenarios["T-02"]["criticality"] == 34 * 300


def test_inv08_penalty_is_the_largest_finite_extra_across_all_the_units_together():
  graph = two_paths(10, 20, 4)
  alone = score(graph, [unit("T-02", "e4")])
  # c3 hangs from e4 only. With no finite extra anywhere the penalty is 0, so it adds nothing.
  assert by_unit(alone)["T-02"]["criticality"] == 0
  together = score(graph, [unit("T-02", "e4"), unit("T-01", "e1")])
  # T-01 is a different unit, yet its +300 sets the penalty used for T-02's isolated c3.
  assert by_unit(together)["T-02"]["criticality"] == 4 * 300


# --- ranking and fixed fields (INV-10, INV-11, INV-12, INV-18, ACC-01, ACC-04) ---


def test_inv10_ranking_breaks_ties_by_isolated_count_then_extra_time_then_smallest_edge():
  graph = two_paths(None, None, None)  # criticality 0 everywhere, so the tie-breaks decide
  units = [unit("T-05", "e5"), unit("T-03", "e3"), unit("T-02", "e2"), unit("T-01", "e1"), unit("T-04", "e1", "e3")]
  scenarios = score(graph, units)
  order = [c["id"] for c in scenarios["candidates"]]
  # T-04: 3 isolated. T-01: extra 300. T-02: extra 100. Then no impact: smallest edge first (e3 before e5).
  assert order == ["T-04", "T-01", "T-02", "T-03", "T-05"]
  assert [c["rank"] for c in scenarios["candidates"]] == [1, 2, 3, 4, 5]


def test_inv10_extra_time_decides_before_the_smallest_edge():
  graph = two_paths(None, None, None)
  for e in graph["edges"]:
    if e["id"] == "e1":
      e["id"] = "e8"  # the +300 closure now has the larger edge number, so the edge tie-break would put it last
  scenarios = score(graph, [unit("T-02", "e2"), unit("T-01", "e8")])
  assert [c["id"] for c in scenarios["candidates"]] == ["T-01", "T-02"]


def test_inv10_criticality_comes_before_the_isolated_count():
  graph = two_paths(10, 20, 4)
  scenarios = by_unit(score(graph, [unit("T-02", "e2"), unit("T-03", "e4"), unit("T-01", "e1")]))
  # T-02 isolates nobody but weighs 2400; T-03 isolates c3 but weighs only 4 x 300 = 1200.
  assert scenarios["T-03"]["isolated_community_ids"] == ["c3"] and not scenarios["T-02"]["isolated_community_ids"]
  assert scenarios["T-01"]["rank"] < scenarios["T-02"]["rank"] < scenarios["T-03"]["rank"]


def test_acc04_a_unit_with_an_isolated_community_outranks_one_with_only_extra_time():
  graph = two_paths(None, None, None)
  scenarios = by_unit(score(graph, [unit("T-01", "e1"), unit("T-02", "e1", "e3")]))
  assert scenarios["T-02"]["extra_time_s"] is None and scenarios["T-02"]["criticality"] == 0
  assert scenarios["T-01"]["extra_time_s"] == 300 and scenarios["T-01"]["criticality"] == 0
  assert scenarios["T-02"]["rank"] < scenarios["T-01"]["rank"]


def test_inv11_each_unit_keeps_its_id_edges_and_length_and_nothing_is_renumbered():
  units = [unit("T-07", "e1", length=4321), unit("T-02", "e2", length=99)]
  scenarios = by_unit(score(two_paths(), units))
  assert scenarios["T-07"]["edge_ids"] == ["e1"] and scenarios["T-07"]["length_m"] == 4321
  assert scenarios["T-02"]["edge_ids"] == ["e2"] and scenarios["T-02"]["length_m"] == 99


def test_inv12_fixed_fields_and_no_exposure():
  for c in score(two_paths(), [unit("T-01", "e1")])["candidates"]:
    assert c["source"] == "network_consequence"
    assert c["zone_ids"] == [] and c["mean_delta_db"] is None
    assert "exposure" not in c


def test_inv18_every_unit_appears_once_including_those_with_no_impact():
  units = [unit("T-01", "e1"), unit("T-02", "e5"), unit("T-03", "e3")]
  scenarios = score(two_paths(), units)
  assert sorted(c["id"] for c in scenarios["candidates"]) == ["T-01", "T-02", "T-03"]


def test_acc01_the_larger_criticality_wins_even_with_the_smaller_extra_time():
  graph, units, _ = mock_inputs()
  scenarios = score(graph, units)
  top = scenarios["candidates"][0]
  assert top["edge_ids"] == ["e3"] and top["rank"] == 1 and top["criticality"] == 2_622_000
  other = next(c for c in scenarios["candidates"] if c["edge_ids"] == ["e2"])
  assert other["extra_time_s"] == 1200 > top["extra_time_s"]


# --- suspect isolations (INV-19, INV-20) ---


def oneway_graph() -> dict:
  """c1 at n2 reaches h1 only by n2 -> n3 -> n1 (e3, e1). e2 (n1 -> n2) joins them one way only."""
  return make_graph(
    [edge("e1", "n3", "n1", 100, oneway=True), edge("e2", "n1", "n2", 100, oneway=True), edge("e3", "n2", "n3", 50)],
    [("h1", "n1")],
    [("c1", "n2", 10)],
  )


def test_inv19_isolation_at_an_endpoint_of_a_closed_edge_is_suspect():
  unit_t = by_unit(score(two_paths(), [unit("T-01", "e1", "e3")]))["T-01"]
  # c1 sits on n2 (end of e1) and c2 on n3 (end of e3); c3 sits on n4, away from both and cut off for real.
  assert unit_t["isolated_community_ids"] == ["c1", "c2", "c3"]
  assert unit_t["suspect_isolated_community_ids"] == ["c1", "c2"]


def test_inv19_isolation_only_because_of_direction_is_suspect():
  unit_t = by_unit(score(oneway_graph(), [unit("T-01", "e1")]))["T-01"]
  # c1 is not at an end of e1, and n2 - n1 is still joined by e2, but only n1 -> n2 can be driven.
  assert unit_t["isolated_community_ids"] == ["c1"]
  assert unit_t["suspect_isolated_community_ids"] == ["c1"]


def test_inv19_a_real_isolation_is_not_suspect():
  graph = make_graph([edge("e1", "n1", "n2", 100), edge("e2", "n2", "n3", 100)], [("h1", "n1")], [("c1", "n3", 10)])
  unit_t = by_unit(score(graph, [unit("T-01", "e1")]))["T-01"]
  assert unit_t["isolated_community_ids"] == ["c1"] and unit_t["suspect_isolated_community_ids"] == []


def test_inv20_suspect_isolations_still_count_everywhere():
  graph = two_paths(10, 20, None)
  scenarios = by_unit(score(graph, [unit("T-01", "e1"), unit("T-02", "e1", "e3")]))
  t2 = scenarios["T-02"]
  assert {"c1", "c2"} <= set(t2["suspect_isolated_community_ids"])
  assert {"c1", "c2"} <= set(t2["isolated_community_ids"]) and {"c1", "c2"} <= set(t2["affected_community_ids"])
  assert t2["criticality"] == (10 + 20) * 300  # suspects pay the penalty like any other isolated community


def test_inv20_suspect_isolations_count_in_the_isolated_count_used_for_ranking():
  graph = two_paths(None, None, None)
  scenarios = score(graph, [unit("T-01", "e1"), unit("T-02", "e1", "e2")])
  by_id = by_unit(scenarios)
  assert by_id["T-02"]["isolated_community_ids"] and set(by_id["T-02"]["isolated_community_ids"]) == set(by_id["T-02"]["suspect_isolated_community_ids"])
  assert by_id["T-02"]["rank"] < by_id["T-01"]["rank"]


# --- the public function (INV-21, INV-23, INV-24) ---


def test_inv21_score_takes_graph_units_and_alternates_and_returns_the_scenarios_dict():
  scenarios = score(two_paths(), [unit("T-01", "e1")])
  assert isinstance(scenarios, dict)
  assert set(scenarios) == {"schema_version", "baseline", "candidates"} and scenarios["schema_version"] == "0.3"
  with_alternates = score(two_paths(), [unit("T-01", "e1")], [{"name": "Ruta 126", "vehicles": "light"}])
  assert with_alternates["candidates"][0]["alternates"] == [{"name": "Ruta 126", "vehicles": "light"}]


def test_inv21_alternates_default_to_none_and_do_not_depend_on_the_road_names():
  graph = two_paths()
  graph["edges"][0]["road"] = "Ruta 32"
  assert score(graph, [unit("T-01", "e1")])["candidates"][0]["alternates"] == []


def test_inv23_score_reads_no_file_config_or_module_value_and_leaves_its_arguments_alone(monkeypatch):
  graph, units, _ = mock_inputs()
  alternates = [{"name": "Ruta 126", "vehicles": "light"}]
  before = copy.deepcopy((graph, units, alternates))
  touched: list[str] = []

  def spy(owner, name):
    real = getattr(owner, name)

    def wrapper(*args, **kwargs):
      touched.append(name)
      return real(*args, **kwargs)

    monkeypatch.setattr(owner, name, wrapper)

  # Recorded, not raised: an exception here would break pytest's own report when the claim fails.
  for owner, name in [(builtins, "open"), (Path, "read_text"), (Path, "read_bytes"), (Path, "exists"), (Path, "is_file"), (Path, "open")]:
    spy(owner, name)
  score(graph, units, alternates)
  monkeypatch.undo()
  assert touched == []
  assert (graph, units, alternates) == before


def test_inv23_the_result_follows_the_graph_it_is_given():
  graph, units, _ = mock_inputs()
  base = score(graph, units)
  slower = copy.deepcopy(graph)
  for e in slower["edges"]:
    e["time_s"] *= 2
  doubled = score(slower, units)
  assert [b["time_s"] for b in doubled["baseline"]] == [None if b["time_s"] is None else 2 * b["time_s"] for b in base["baseline"]]
  assert [c["criticality"] for c in doubled["candidates"]] == [2 * c["criticality"] for c in base["candidates"]]
  fewer = copy.deepcopy(graph)
  fewer["hospitals"] = [h for h in fewer["hospitals"] if h["id"] != "h3"]
  assert score(fewer, units)["baseline"] != base["baseline"]  # one referral hospital less changes the routes


def test_inv24_equal_arguments_give_results_that_serialize_to_the_same_json():
  graph, units, _ = mock_inputs()
  first = json.dumps(score(graph, units, [{"name": "Ruta 10", "vehicles": "freight"}]))
  second = json.dumps(score(copy.deepcopy(graph), copy.deepcopy(units), [{"name": "Ruta 10", "vehicles": "freight"}]))
  assert first == second


# --- the file writer (INV-01, INV-15, INV-22) ---


def make_zone(tmp_path: Path, alternates=ZONE_ALTERNATES) -> Zone:
  return Zone(
    id="fixture", name="Fixture", validated=False, bbox=(9.9, -0.1, 10.1, 0.1), referral_hospitals=("way/1",),
    speed_model_kmh={"trunk": 60}, closure_roads=("Ruta 32",), closure_alternates=tuple(alternates),
    population_raster="work/none.tif", population_url="https://example.invalid/none.tif",
    rain_start="2026-01-01", rain_end="2026-01-02", detection_limits=None, output_dir=tmp_path / "output" / "fixture",
  )


def stage(tmp_path: Path, graph: dict | None = None, units: list | None = None, alternates=ZONE_ALTERNATES) -> tuple[Zone, Path, dict, list]:
  mock_graph, mock_units, _ = mock_inputs()
  graph, units = graph or mock_graph, units if units is not None else mock_units
  zone = make_zone(tmp_path, alternates)
  zone.output_dir.mkdir(parents=True)
  (zone.output_dir / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
  work = tmp_path / "work" / "fixture"
  work.mkdir(parents=True)
  (work / "closure_units.json").write_text(json.dumps(units), encoding="utf-8")
  return zone, work, graph, units


def test_inv01_the_written_scenarios_pass_the_schema_and_the_cross_reference_checks(tmp_path):
  zone, work, graph, _ = stage(tmp_path)
  impact_scoring.run(zone, work)
  scenarios = json.loads((zone.output_dir / "scenarios.json").read_text(encoding="utf-8"))
  assert _schema_errors("scenarios.json", scenarios, "scenarios.schema.json") == []
  assert _check_graph(graph) == [] and _check_scenarios(graph, scenarios, set()) == []


def test_inv22_the_file_is_exactly_what_score_returns_for_the_same_inputs(tmp_path):
  zone, work, graph, units = stage(tmp_path)
  impact_scoring.run(zone, work)
  written = (zone.output_dir / "scenarios.json").read_text(encoding="utf-8")
  alternates = [{"name": n, "vehicles": v} for n, v in ZONE_ALTERNATES]
  assert json.loads(written) == score(graph, units, alternates)


def test_inv15_every_unit_carries_the_zones_alternates(tmp_path):
  zone, work, _, _ = stage(tmp_path)
  impact_scoring.run(zone, work)
  scenarios = json.loads((zone.output_dir / "scenarios.json").read_text(encoding="utf-8"))
  expected = [{"name": n, "vehicles": v} for n, v in ZONE_ALTERNATES]
  assert all(c["alternates"] == expected for c in scenarios["candidates"])
  zone2, work2, _, _ = stage(tmp_path / "none", alternates=())
  impact_scoring.run(zone2, work2)
  assert all(c["alternates"] == [] for c in json.loads((zone2.output_dir / "scenarios.json").read_text(encoding="utf-8"))["candidates"])


# --- duplicate unit ids (INV-25, INV-26) ---


def agreeing_duplicate_graph() -> dict:
  """Both entries are named T-01 and the graph agrees with both, so the cross-reference checks have nothing to object to."""
  graph = two_paths()
  for e in graph["edges"]:
    if e["id"] in ("e1", "e2"):
      e["candidate_id"] = "T-01"
  return graph


def test_inv25_score_rejects_two_units_with_the_same_id():
  with pytest.raises(ImpactScoringError, match="T-01"):
    score(two_paths(), [unit("T-01", "e1"), unit("T-01", "e2")])


def test_inv26_run_stops_when_closure_units_lists_the_same_id_twice(tmp_path):
  zone, work, _, _ = stage(tmp_path, graph=agreeing_duplicate_graph(), units=[unit("T-01", "e1"), unit("T-01", "e2")])
  with pytest.raises(ImpactScoringError, match="T-01"):
    impact_scoring.run(zone, work)
  assert not (zone.output_dir / "scenarios.json").exists()


# --- acceptance against the contract mock (ACC-02, ACC-03) ---


def test_acc02_the_contract_mock_is_reproduced():
  graph, units, expected = mock_inputs()
  scenarios = score(graph, units)
  assert scenarios["baseline"] == expected["baseline"]
  theirs = {tuple(c["edge_ids"]): c for c in expected["candidates"]}
  for c in scenarios["candidates"]:
    t = theirs[tuple(c["edge_ids"])]
    for field in ("rank", "criticality", "extra_time_s", "population_dependent", "per_community"):
      assert c[field] == t[field], (c["edge_ids"], field)


def test_acc03_a_unit_that_affects_nobody_has_zero_extra_time_zero_criticality_and_null_population():
  unit_t = by_unit(score(two_paths(10, 20, 4), [unit("T-01", "e3")]))["T-01"]
  assert unit_t["extra_time_s"] == 0 and unit_t["criticality"] == 0 and unit_t["population_dependent"] is None
  assert unit_t["affected_community_ids"] == [] and unit_t["isolated_community_ids"] == []
  assert unit_t["suspect_isolated_community_ids"] == []


# --- the file boundary: unreadable inputs end in an English error, not a traceback ---


def test_a_unit_with_an_edge_the_graph_does_not_have_stops_naming_it():
  with pytest.raises(ImpactScoringError, match="e99"):
    score(two_paths(), [unit("T-01", "e99")])


def test_a_missing_graph_file_stops_naming_it(tmp_path):
  zone, work, _, _ = stage(tmp_path)
  (zone.output_dir / "graph.json").unlink()
  with pytest.raises(ImpactScoringError, match="graph.json"):
    impact_scoring.run(zone, work)
  assert not (zone.output_dir / "scenarios.json").exists()


def test_a_closure_units_file_that_is_not_json_stops_naming_it(tmp_path):
  zone, work, _, _ = stage(tmp_path)
  (work / "closure_units.json").write_text("{not json", encoding="utf-8")
  with pytest.raises(ImpactScoringError, match="closure_units.json"):
    impact_scoring.run(zone, work)
  assert not (zone.output_dir / "scenarios.json").exists()
