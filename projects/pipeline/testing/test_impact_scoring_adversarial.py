import itertools
import json
import os
import subprocess
import sys
from functools import partial
from pathlib import Path

import pytest

from pipeline import impact_scoring, manual_review, rank_sensitivity, time_crosscheck
from pipeline.impact_scoring import ImpactScoringError, score
from test_impact_scoring import by_unit, edge, make_graph, mock_inputs, stage, two_paths, unit


# --- the real consumers of score(): the stages that call it or read what it writes ---


def test_rank_sensitivity_accepts_score_as_its_scorer_and_the_baseline_reproduces():
  graph, units, _ = mock_inputs()
  alternates = [{"name": "Ruta 126", "vehicles": "light"}]
  scenarios = score(graph, units, alternates)
  # rank-sensitivity calls scorer(graph, units) and compares it with the whole file; the caller binds the alternates.
  report = rank_sensitivity.build_report(graph, units, scenarios, partial(score, alternates=alternates))
  assert report["baseline"]["unit_ids"] == [c["id"] for c in scenarios["candidates"]]
  assert {run["kind"] for run in report["runs"]} == {"speed", "hospital"}


def test_manual_review_and_time_crosscheck_read_what_score_writes():
  graph, units, _ = mock_inputs()
  scenarios = score(graph, units)
  assert manual_review.choose_units(scenarios)
  assert time_crosscheck.build_sample(graph, scenarios["baseline"])


# --- order and repetition ---


def test_inv24_the_order_of_the_units_does_not_change_the_result():
  graph, units, _ = mock_inputs()
  reference = json.dumps(score(graph, units), sort_keys=True)
  for ordering in itertools.permutations(units):
    assert json.dumps(score(graph, list(ordering)), sort_keys=True) == reference


SEED_SCRIPT = """
import json, sys
from pipeline.impact_scoring import score
graph, units = json.load(sys.stdin)
print(json.dumps(score(graph, units)))
"""


def test_inv24_the_result_does_not_depend_on_the_python_hash_seed():
  units = [unit("T-01", "e1"), unit("T-02", "e1", "e3"), unit("T-03", "e4"), unit("T-04", "e2"), unit("T-05", "e5")]
  payload = json.dumps([two_paths(10, 20, 4), units])
  outputs = set()
  for seed in ("0", "1", "42"):
    done = subprocess.run(
      [sys.executable, "-c", SEED_SCRIPT], input=payload, capture_output=True, text=True, check=True,
      env={**os.environ, "PYTHONHASHSEED": seed},
    )
    outputs.add(done.stdout)
  assert len(outputs) == 1


# --- boundaries: where the graph gives the search nothing, or everything ---


def test_inv03_a_community_on_the_hospital_node_is_never_affected_or_isolated():
  graph = make_graph([edge("e1", "n1", "n2", 100)], [("h1", "n1")], [("c1", "n1", 5), ("c2", "n2", 7)])
  scenarios = score(graph, [unit("T-01", "e1")])
  assert scenarios["baseline"][0] == {"community_id": "c1", "time_s": 0, "hospital_id": "h1"}
  t = by_unit(scenarios)["T-01"]
  assert t["affected_community_ids"] == ["c2"] and t["isolated_community_ids"] == ["c2"]


def test_a_graph_with_no_hospital_has_no_routes_and_no_impact_and_does_not_fail():
  graph = make_graph([edge("e1", "n1", "n2", 100)], [], [("c1", "n2", 5)])
  scenarios = score(graph, [unit("T-01", "e1")])
  assert scenarios["baseline"] == [{"community_id": "c1", "time_s": None, "hospital_id": None}]
  t = scenarios["candidates"][0]
  assert t["extra_time_s"] == 0 and t["criticality"] == 0 and t["affected_community_ids"] == []


def test_a_graph_with_no_community_scores_every_unit_as_no_impact():
  graph = make_graph([edge("e1", "n1", "n2", 100)], [("h1", "n1")], [])
  scenarios = score(graph, [unit("T-01", "e1")])
  assert scenarios["baseline"] == []
  assert scenarios["candidates"][0]["extra_time_s"] == 0 and scenarios["candidates"][0]["population_dependent"] is None


def test_inv07_a_unit_that_closes_every_edge_isolates_every_community_with_a_route():
  graph = two_paths(10, 20, 4)
  every = [e["id"] for e in graph["edges"]]
  t = by_unit(score(graph, [unit("T-01", *every)]))["T-01"]
  assert t["isolated_community_ids"] == ["c1", "c2", "c3"] and t["extra_time_s"] is None


# --- the file boundary: malformed units end in an English error and write nothing ---


def stops_cleanly(tmp_path: Path, units: list, *expected: str, graph: dict | None = None) -> None:
  zone, work, _, _ = stage(tmp_path, graph=graph, units=units)
  with pytest.raises(ImpactScoringError) as error:
    impact_scoring.run(zone, work)
  for text in expected:
    assert text in str(error.value)
  assert not (zone.output_dir / "scenarios.json").exists()


def test_unit_with_a_null_edge_id_stops_cleanly(tmp_path):
  stops_cleanly(tmp_path, [{"id": "T-01", "edge_ids": [None], "length_m": 1000}], "T-01")


def test_unit_with_a_nested_list_as_edge_id_stops_cleanly(tmp_path):
  stops_cleanly(tmp_path, [{"id": "T-01", "edge_ids": [["e1"]], "length_m": 1000}], "T-01")


@pytest.mark.parametrize("length", [0, -5, "1000", None])
def test_unit_with_an_invalid_length_stops_cleanly(tmp_path, length):
  stops_cleanly(tmp_path, [{"id": "T-01", "edge_ids": ["e2"], "length_m": length}])


def test_unit_without_edges_stops_cleanly(tmp_path):
  stops_cleanly(tmp_path, [{"id": "T-01", "edge_ids": [], "length_m": 1000}], "edge_ids")


def test_two_units_that_share_an_edge_stop_naming_it(tmp_path):
  graph, units, _ = mock_inputs()
  stops_cleanly(tmp_path, [units[0], {**units[1], "edge_ids": units[0]["edge_ids"]}], units[0]["edge_ids"][0], graph=graph)


def test_graph_whose_edges_have_no_unit_ids_says_so(tmp_path):
  stops_cleanly(tmp_path, [unit("T-01", "e1")], "candidate_id", graph=two_paths())


def test_failed_run_leaves_the_previous_scenarios_file_untouched(tmp_path):
  zone, work, _, _ = stage(tmp_path)
  target = zone.output_dir / "scenarios.json"
  target.write_text("PREVIOUS", encoding="utf-8")
  (work / "closure_units.json").write_text(json.dumps([{"id": "T-01", "edge_ids": ["e999"], "length_m": 5}]), encoding="utf-8")
  with pytest.raises(ImpactScoringError):
    impact_scoring.run(zone, work)
  assert target.read_text(encoding="utf-8") == "PREVIOUS"


def test_graph_missing_a_required_list_stops_naming_the_file(tmp_path):
  graph = two_paths()
  del graph["hospitals"]
  stops_cleanly(tmp_path, [unit("T-01", "e1")], "graph.json", graph=graph)


def test_graph_with_an_edge_to_an_unknown_node_stops_naming_it(tmp_path):
  graph = two_paths()
  graph["edges"][0]["from"] = "n99"
  stops_cleanly(tmp_path, [unit("T-01", "e1")], "graph.json", "n99", graph=graph)
