import json
from dataclasses import replace
from pathlib import Path

import pytest

from pipeline import closure_units
from pipeline.area_config import Zone
from pipeline.closure_units import ClosureUnitsError, build_units
from pipeline.validate import _check_graph, _schema_errors

# Everything sits on the equator, so 0.001 degree of longitude or latitude is about 111 m: a pair 0.0009 degrees
# apart (100 m) is inside PAIR_M = 120 and one 0.0014 degrees apart (155 m) is outside.
ROAD = "Ruta 1"
EAST = 0.0009
FAR = 0.0014


def make_zone(tmp_path: Path, roads=(ROAD,)) -> Zone:
  return Zone(
    id="fixture", name="Fixture", validated=False, bbox=(0.0, -1.0, 1.0, 1.0), referral_hospitals=("way/1",),
    speed_model_kmh={"trunk": 60}, closure_roads=roads, closure_alternates=(),
    population_raster=str(tmp_path / "raster.tif"), population_url="https://example.invalid/raster.tif",
    rain_start="2026-01-01", rain_end="2026-01-14", detection_limits=None, output_dir=tmp_path / "output" / "fixture",
  )


def make_graph(nodes: dict[str, tuple[float, float]], edges: list[tuple]) -> dict:
  """`nodes` maps id -> (lon, lat); each edge is (id, from, to, road, oneway, length_m) with a straight geometry."""
  first = next(iter(nodes))
  return {
    "schema_version": "0.3",
    "nodes": [{"id": n, "lon": lon, "lat": lat} for n, (lon, lat) in nodes.items()],
    "edges": [
      {"id": e, "from": a, "to": b, "length_m": length, "time_s": 10, "road": road, "oneway": oneway, "candidate_id": None,
       "geometry": [list(nodes[a]), list(nodes[b])]}
      for e, a, b, road, oneway, length in edges
    ],
    "hospitals": [{"id": "h1", "name": "Hospital", "node": first}],
    "communities": [{"id": "c1", "name": "Place", "node": first, "population": None}],
  }


def unit_of(units: list[dict]) -> dict[str, str]:
  return {edge_id: u["id"] for u in units for edge_id in u["edge_ids"]}


def dual_carriageway(gap: float = EAST, split: bool = False) -> tuple[dict, list[tuple]]:
  """Eastbound A (n1 -> n3) and westbound B (n6 -> n4), both one-way; `split` cuts each in two at a plain node."""
  nodes = {"n1": (0.0, 0.0), "n3": (0.01, 0.0), "n6": (0.01, gap), "n4": (0.0, gap)}
  if not split:
    return nodes, [("e1", "n1", "n3", ROAD, True, 1000), ("e2", "n6", "n4", ROAD, True, 1000)]
  nodes |= {"n2": (0.005, 0.0), "n5": (0.005, gap)}
  return nodes, [
    ("e1", "n1", "n2", ROAD, True, 500), ("e2", "n2", "n3", ROAD, True, 500),
    ("e3", "n6", "n5", ROAD, True, 600), ("e4", "n5", "n4", ROAD, True, 600),
  ]


def test_inv_02_inv_03_only_edges_of_the_zone_roads_get_a_unit_and_each_gets_one():
  nodes = {"n1": (0.0, 0.0), "n2": (0.01, 0.0), "n3": (0.02, 0.0), "n4": (0.01, 0.01)}
  graph = make_graph(nodes, [("e1", "n1", "n2", ROAD, False, 1000), ("e2", "n2", "n3", ROAD, False, 1000), ("e3", "n2", "n4", "Calle", False, 1000)])
  units = build_units(graph, (ROAD,))
  assert set(unit_of(units)) == {"e1", "e2"}
  assert sorted(e for u in units for e in u["edge_ids"]) == ["e1", "e2"]


def test_inv_02_an_edge_with_no_road_name_is_never_a_corridor_edge():
  graph = make_graph({"n1": (0.0, 0.0), "n2": (0.01, 0.0)}, [("e1", "n1", "n2", None, False, 1000), ("e2", "n1", "n2", ROAD, False, 1000)])
  assert set(unit_of(build_units(graph, (ROAD,)))) == {"e2"}


def test_inv_06_a_junction_between_two_way_edges_splits_the_units():
  nodes = {"n1": (0.0, 0.0), "n2": (0.01, 0.0), "n3": (0.02, 0.0), "n4": (0.01, 0.01)}
  graph = make_graph(nodes, [("e1", "n1", "n2", ROAD, False, 1000), ("e2", "n2", "n3", ROAD, False, 1000), ("e3", "n2", "n4", "Calle", False, 1000)])
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e1"] != owner["e2"]


def test_inv_06_a_plain_node_where_an_edge_was_split_is_not_a_junction():
  nodes = {"n1": (0.0, 0.0), "n2": (0.01, 0.0), "n3": (0.02, 0.0)}
  graph = make_graph(nodes, [("e1", "n1", "n2", ROAD, False, 1000), ("e2", "n2", "n3", ROAD, False, 1000)])
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e1"] == owner["e2"]


def test_inv_06_a_road_that_changes_name_at_a_node_splits_the_units():
  nodes = {"n1": (0.0, 0.0), "n2": (0.01, 0.0), "n3": (0.02, 0.0)}
  graph = make_graph(nodes, [("e1", "n1", "n2", ROAD, False, 1000), ("e2", "n2", "n3", "Ruta 2", False, 1000)])
  assert len(build_units(graph, (ROAD,))) == 1  # the other road is not a corridor edge: e1 ends there


def test_inv_05_opposite_one_way_edges_within_120_m_share_a_unit():
  nodes, edges = dual_carriageway(EAST)
  owner = unit_of(build_units(make_graph(nodes, edges), (ROAD,)))
  assert owner["e1"] == owner["e2"]


def test_inv_05_opposite_one_way_edges_beyond_120_m_do_not():
  nodes, edges = dual_carriageway(FAR)
  owner = unit_of(build_units(make_graph(nodes, edges), (ROAD,)))
  assert owner["e1"] != owner["e2"]


def test_inv_05_one_way_edges_in_the_same_direction_are_not_paired():
  nodes = {"n1": (0.0, 0.0), "n2": (0.01, 0.0), "n3": (0.0, EAST), "n4": (0.01, EAST)}
  graph = make_graph(nodes, [("e1", "n1", "n2", ROAD, True, 1000), ("e2", "n3", "n4", ROAD, True, 1000)])
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e1"] != owner["e2"]


def test_inv_05_a_two_way_edge_is_never_paired_with_a_neighbour():
  nodes = {"n1": (0.0, 0.0), "n2": (0.01, 0.0), "n3": (0.0, EAST), "n4": (0.01, EAST)}
  graph = make_graph(nodes, [("e1", "n1", "n2", ROAD, False, 1000), ("e2", "n3", "n4", ROAD, True, 1000)])
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e1"] != owner["e2"]


def test_inv_07_a_junction_aligned_on_both_carriageways_splits_the_dual_road():
  nodes = {
    "n1": (0.0, 0.0), "n2": (0.01, 0.0), "n3": (0.02, 0.0),
    "n6": (0.02, EAST), "n5": (0.01, EAST), "n4": (0.0, EAST),
    "r1": (0.01, -0.01), "r2": (0.01, 0.01),
  }
  graph = make_graph(nodes, [
    ("e1", "n1", "n2", ROAD, True, 1000), ("e2", "n2", "n3", ROAD, True, 1000),
    ("e3", "n6", "n5", ROAD, True, 1000), ("e4", "n5", "n4", ROAD, True, 1000),
    ("e5", "n2", "r1", "Ramp", False, 500), ("e6", "n5", "r2", "Ramp", False, 500),
  ])
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e1"] == owner["e4"] and owner["e2"] == owner["e3"]
  assert owner["e1"] != owner["e2"]


def test_inv_09_two_parallel_carriageways_of_equal_length_count_once():
  nodes, edges = dual_carriageway(EAST)
  (unit,) = build_units(make_graph(nodes, edges), (ROAD,))
  assert unit["length_m"] == 1000


def test_inv_09_parallel_carriageways_of_unequal_length_take_the_longer():
  nodes, edges = dual_carriageway(EAST, split=True)
  (unit,) = build_units(make_graph(nodes, edges), (ROAD,))
  assert unit["length_m"] == 1200  # A is 500 + 500, B is 600 + 600


def test_inv_09_a_two_way_stretch_counts_the_sum_of_its_edges():
  nodes = {"n1": (0.0, 0.0), "n2": (0.003, 0.0), "n3": (0.007, 0.0), "n4": (0.012, 0.0)}
  graph = make_graph(nodes, [("e1", "n1", "n2", ROAD, False, 300), ("e2", "n2", "n3", ROAD, False, 400), ("e3", "n3", "n4", ROAD, False, 500)])
  (unit,) = build_units(graph, (ROAD,))
  assert unit["length_m"] == 1200


def stretches(first: tuple[str, float, float], second: tuple[str, float, float]) -> dict:
  """Two separate two-way stretches, each (name, lon of its west end, lat); the first listed comes first in the edge list."""
  nodes, edges = {}, []
  for number, (_, lon, lat) in enumerate((first, second), start=1):
    nodes |= {f"a{number}": (lon, lat), f"b{number}": (lon + 0.01, lat)}
    edges.append((f"e{number}", f"a{number}", f"b{number}", ROAD, False, 1000))
  return make_graph(nodes, edges)


def test_inv_04_ids_follow_ascending_longitude_whatever_the_edge_order():
  graph = stretches(("east", 0.5, 0.0), ("west", 0.0, 0.0))  # e1 is the eastern one
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e2"] == "T-01" and owner["e1"] == "T-02"


def test_inv_04_a_longitude_tie_is_broken_by_latitude():
  graph = stretches(("north", 0.0, 0.05), ("south", 0.0, 0.0))  # same longitude; e1 is the northern one
  owner = unit_of(build_units(graph, (ROAD,)))
  assert owner["e2"] == "T-01" and owner["e1"] == "T-02"


def test_inv_04_ids_are_unique_two_digit_and_sorted_in_the_output():
  graph = stretches(("east", 0.5, 0.0), ("west", 0.0, 0.0))
  units = build_units(graph, (ROAD,))
  assert [u["id"] for u in units] == ["T-01", "T-02"]
  assert all(sorted(u["edge_ids"], key=lambda e: int(e[1:])) == u["edge_ids"] for u in units)


def test_inv_04_more_than_ninety_nine_units_keep_unique_ids():
  nodes, edges = {}, []
  for n in range(1, 101):
    nodes |= {f"a{n}": (n * 0.1, 0.0), f"b{n}": (n * 0.1 + 0.01, 0.0)}
    edges.append((f"e{n}", f"a{n}", f"b{n}", ROAD, False, 1000))
  units = build_units(make_graph(nodes, edges), (ROAD,))
  assert [u["id"] for u in units][-2:] == ["T-99", "T-100"] and len({u["id"] for u in units}) == 100


def test_inv_11_no_matching_edge_is_an_error_naming_the_roads():
  graph = make_graph({"n1": (0.0, 0.0), "n2": (0.01, 0.0)}, [("e1", "n1", "n2", "Calle", False, 1000)])
  with pytest.raises(ClosureUnitsError, match="Ruta 32"):
    build_units(graph, ("Ruta 32",))


def write_graph(tmp_path: Path, graph: dict) -> tuple[Zone, Path]:
  zone, work_dir = make_zone(tmp_path), tmp_path / "work"
  zone.output_dir.mkdir(parents=True)
  (zone.output_dir / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
  return zone, work_dir


def sample_graph() -> dict:
  nodes = {"n1": (0.0, 0.0), "n2": (0.01, 0.0), "n3": (0.02, 0.0), "n4": (0.01, 0.01)}
  return make_graph(nodes, [("e1", "n1", "n2", ROAD, False, 1000), ("e2", "n2", "n3", ROAD, False, 1000), ("e3", "n2", "n4", "Calle", False, 1000)])


def test_inv_01_the_graph_it_writes_validates_and_differs_only_in_candidate_id(tmp_path):
  before = sample_graph()
  zone, work_dir = write_graph(tmp_path, before)
  closure_units.run(zone, work_dir)
  after = json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))
  assert _schema_errors("graph.json", after, "graph.schema.json") == [] and _check_graph(after) == []
  assert [e["candidate_id"] for e in after["edges"]] == ["T-01", "T-02", None]
  for edge in after["edges"] + before["edges"]:
    del edge["candidate_id"]
  assert after == before


def test_inv_01_an_old_candidate_id_on_a_non_corridor_edge_is_cleared(tmp_path):
  graph = sample_graph()
  graph["edges"][2]["candidate_id"] = "T-09"
  zone, work_dir = write_graph(tmp_path, graph)
  closure_units.run(zone, work_dir)
  assert json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))["edges"][2]["candidate_id"] is None


def test_inv_12_closure_units_json_holds_exactly_the_edges_carrying_each_id(tmp_path):
  zone, work_dir = write_graph(tmp_path, sample_graph())
  closure_units.run(zone, work_dir)
  graph = json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))
  units = json.loads((work_dir / "closure_units.json").read_text(encoding="utf-8"))
  by_id = {u["id"]: set(u["edge_ids"]) for u in units}
  assert by_id == {"T-01": {"e1"}, "T-02": {"e2"}}
  for unit_id, edge_ids in by_id.items():
    assert {e["id"] for e in graph["edges"] if e["candidate_id"] == unit_id} == edge_ids
  assert all(set(u) == {"id", "edge_ids", "length_m"} for u in units)


def test_inv_11_run_with_no_matching_road_writes_nothing(tmp_path):
  zone, work_dir = write_graph(tmp_path, sample_graph())
  zone = replace(zone, closure_roads=("Ruta 32",))
  before = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(ClosureUnitsError, match="Ruta 32"):
    closure_units.run(zone, work_dir)
  assert not (work_dir / "closure_units.json").exists()
  assert (zone.output_dir / "graph.json").read_bytes() == before


def test_inv_11_main_exits_non_zero_with_an_english_error(tmp_path, monkeypatch):
  zone, work_dir = write_graph(tmp_path, sample_graph())
  zone = replace(zone, closure_roads=("Ruta 32",))
  root = tmp_path / "work_root"
  root.mkdir()
  monkeypatch.setattr(closure_units, "load_zone", lambda _id: zone)
  monkeypatch.setattr(closure_units, "WORK_DIR", root)
  with pytest.raises(SystemExit) as exit_info:
    closure_units.main(["--area", zone.id])
  assert "Ruta 32" in str(exit_info.value)
