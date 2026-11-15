import json

import pytest
from test_closure_units import EAST, ROAD, build_units, dual_carriageway, make_graph, sample_graph, stretches, unit_of, write_graph

from pipeline import closure_units
from pipeline.closure_units import ClosureUnitsError


def two_stretches_and_a_dual_road() -> dict:
  nodes, edges = dual_carriageway(EAST, split=True)
  nodes |= {"m1": (0.5, 0.0), "m2": (0.51, 0.0), "r1": (0.005, -0.01)}
  edges += [("e5", "m1", "m2", ROAD, False, 1000), ("e6", "n2", "r1", "Ramp", False, 500)]
  return make_graph(nodes, edges)


def test_inv_04_the_edge_and_node_order_of_the_file_does_not_change_the_result():
  graph = two_stretches_and_a_dual_road()
  shuffled = {**graph, "edges": list(reversed(graph["edges"])), "nodes": list(reversed(graph["nodes"]))}
  assert build_units(shuffled, (ROAD,)) == build_units(graph, (ROAD,))


@pytest.mark.parametrize("gap, paired", [(0.00104, True), (0.00112, False)], ids=["116_m_apart", "125_m_apart"])
def test_inv_05_the_pairing_distance_is_120_m_not_a_looser_or_tighter_bound(gap, paired):
  nodes, edges = dual_carriageway(gap)
  owner = unit_of(build_units(make_graph(nodes, edges), (ROAD,)))
  assert (owner["e1"] == owner["e2"]) is paired


def test_inv_05_opposite_direction_is_judged_in_metres_not_in_degrees():
  # At 60 degrees north a degree of longitude is half as long as one of latitude. These chords are acute in metres
  # (about 62 degrees apart) but obtuse if longitude is taken at face value, so they are not opposite carriageways.
  nodes = {"a": (0.0, 60.0), "b": (0.001, 60.001), "c": (0.001, 60.0003), "d": (0.0, 60.0007)}
  graph = make_graph(nodes, [("e1", "a", "b", ROAD, True, 124), ("e2", "c", "d", ROAD, True, 62)])
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e1"] != owner["e2"]


def test_inv_05_the_midpoint_is_halfway_along_a_bent_edge_not_halfway_between_its_ends():
  # e1 goes east 1112 m then north 222 m: half its length is 667 m along, at lon 0.006. e2 sits 44 m north of that point
  # and 130 m from the chord midpoint, so only the true midpoint pairs them.
  nodes = {"a": (0.0, 0.0), "b": (0.01, 0.002), "c": (0.007, 0.0004), "d": (0.005, 0.0004)}
  graph = make_graph(nodes, [("e1", "a", "b", ROAD, True, 1334), ("e2", "c", "d", ROAD, True, 222)])
  graph["edges"][0]["geometry"] = [[0.0, 0.0], [0.01, 0.0], [0.01, 0.002]]
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e1"] == owner["e2"]


def test_inv_01_stale_ids_on_corridor_edges_are_replaced_by_the_new_ones(tmp_path):
  graph = sample_graph()
  graph["edges"][0]["candidate_id"], graph["edges"][1]["candidate_id"] = "T-07", "T-07"
  zone, work_dir = write_graph(tmp_path, graph)
  closure_units.run(zone, work_dir)
  edges = json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))["edges"]
  assert [e["candidate_id"] for e in edges] == ["T-01", "T-02", None]


def test_inv_12_running_twice_gives_the_same_files(tmp_path):
  zone, work_dir = write_graph(tmp_path, sample_graph())
  closure_units.run(zone, work_dir)
  names = [zone.output_dir / "graph.json", work_dir / "closure_units.json"]
  first = [p.read_bytes() for p in names]
  closure_units.run(zone, work_dir)
  assert [p.read_bytes() for p in names] == first


@pytest.mark.parametrize("content", ["not json", "[]", "null", '{"edges": []}', "﻿{"])
def test_inv_01_a_graph_file_that_is_not_a_valid_graph_is_a_clean_error_and_writes_nothing(tmp_path, content):
  zone, work_dir = write_graph(tmp_path, sample_graph())
  (zone.output_dir / "graph.json").write_text(content, encoding="utf-8")
  with pytest.raises(ClosureUnitsError):
    closure_units.run(zone, work_dir)
  assert not (work_dir / "closure_units.json").exists()


def test_inv_01_a_missing_graph_file_is_a_clean_error(tmp_path):
  zone, work_dir = write_graph(tmp_path, sample_graph())
  (zone.output_dir / "graph.json").unlink()
  with pytest.raises(ClosureUnitsError):
    closure_units.run(zone, work_dir)


def test_inv_01_an_edge_that_names_an_unknown_node_is_a_clean_error(tmp_path):
  graph = sample_graph()
  graph["edges"][0]["to"] = "n99"
  zone, work_dir = write_graph(tmp_path, graph)
  with pytest.raises(ClosureUnitsError, match="n99"):
    closure_units.run(zone, work_dir)
  assert not (work_dir / "closure_units.json").exists()


def test_inv_07_short_edges_next_to_an_aligned_junction_do_not_merge_across_it():
  # 55 m edges and 55 m between carriageways: the opposite edge across the junction is only 78 m from the midpoint,
  # inside PAIR_M, so only pairing each edge with its nearest opposite edge keeps the two sides apart.
  g = 0.0005
  nodes = {
    "a0": (-0.0005, 0.0), "aj": (0.0, 0.0), "a2": (0.0005, 0.0),
    "b2": (0.0005, g), "bj": (0.0, g), "b0": (-0.0005, g),
    "r1": (0.0, -0.01), "r2": (0.0, g + 0.01),
  }
  graph = make_graph(nodes, [
    ("e1", "a0", "aj", ROAD, True, 55), ("e2", "aj", "a2", ROAD, True, 55),
    ("e3", "b2", "bj", ROAD, True, 55), ("e4", "bj", "b0", ROAD, True, 55),
    ("e5", "aj", "r1", "Ramp", False, 500), ("e6", "bj", "r2", "Ramp", False, 500),
  ])
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e1"] == owner["e4"] and owner["e2"] == owner["e3"] and owner["e1"] != owner["e2"]


def test_inv_04_longitude_decides_the_order_before_latitude_does():
  graph = stretches(("east and south", 0.5, 0.0), ("west and north", 0.0, 0.05))
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e2"] == "T-01" and owner["e1"] == "T-02"


def test_inv_04_units_in_the_exact_same_place_are_numbered_by_their_lowest_edge_number():
  nodes, edges = {}, []
  for n in range(1, 7):  # six stretches with identical coordinates, so every sort key ties
    nodes |= {f"a{n}": (0.0, 0.0), f"b{n}": (0.01, 0.0)}
    edges.append((f"e{n}", f"a{n}", f"b{n}", ROAD, False, 1000))
  owner = unit_of(build_units(make_graph(nodes, edges), (ROAD,)))
  assert [owner[f"e{n}"] for n in range(1, 7)] == [f"T-{n:02d}" for n in range(1, 7)]
