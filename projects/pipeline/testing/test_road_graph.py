import dataclasses
import json
import math
from pathlib import Path

import networkx as nx
import osmnx as ox
import pytest

from pipeline import road_graph
from pipeline.validate import _check_graph, _schema_errors

FIXTURE = Path(__file__).parent / "fixtures" / "road_graph"
REAL_OSM = road_graph.OSM_DIR
# Fixture-only values so every class in the fixture has a speed; not real speeds.
FALLBACKS = {"primary": 30, "secondary": 35, "unclassified": 25}
PLACES = {"Fixture Village": (0.0052, 10.0102), "Fixture Town": (0.0003, 10.0195)}


@pytest.fixture
def env(tmp_path: Path, monkeypatch) -> Path:
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("# fixture allowlist\nway/301\nnode/30\n", encoding="utf-8")
    settings = road_graph.Settings(
        bbox=(9.995, -0.005, 10.05, 0.02),
        allowlist=allowlist,
        min_tagged=2,
        fallback_speeds_kmh=FALLBACKS,
    )
    monkeypatch.setattr(road_graph, "SETTINGS", settings)
    monkeypatch.setattr(road_graph, "OSM_DIR", FIXTURE)
    monkeypatch.setattr(road_graph, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(road_graph, "WORK", tmp_path / "work")
    return tmp_path


def run(env: Path) -> dict:
    road_graph.main([])
    return json.loads((env / "output" / "graph.json").read_text(encoding="utf-8"))


def speeds(env: Path) -> dict:
    return json.loads((env / "work" / "speed_model_kmh.json").read_text(encoding="utf-8"))


def fails_without_graph(env: Path, *expected: str) -> None:
    with pytest.raises(SystemExit) as exit_info:
        road_graph.main([])
    message = str(exit_info.value.code)
    assert exit_info.value.code not in (0, None)
    for text in expected:
        assert text in message
    assert not (env / "output" / "graph.json").exists()


def edge_class(edge: dict) -> str:
    # The fixture's roads tell their class apart by name and direction.
    if edge["road"] in ("Ruta 901", "Ruta 903"):
        return "trunk"
    if edge["road"] == "Fixture Primary":
        return "primary"
    return "secondary" if edge["oneway"] else "unclassified"


def test_inv01_output_passes_schema_and_node_refs(env):
    graph = run(env)
    assert _schema_errors("graph.json", graph, "graph.schema.json") == []
    assert _check_graph(graph) == []


def test_inv02_geometry_ends_on_its_nodes(env):
    graph = run(env)
    nodes = {n["id"]: [n["lon"], n["lat"]] for n in graph["nodes"]}
    for e in graph["edges"]:
        assert e["geometry"][0] == nodes[e["from"]]
        assert e["geometry"][-1] == nodes[e["to"]]


def test_inv03_integer_costs_rounded_half_up(env):
    graph = run(env)
    table = speeds(env)
    for e in graph["edges"]:
        assert isinstance(e["length_m"], int) and isinstance(e["time_s"], int)
        expected = math.floor(e["length_m"] / (table[edge_class(e)] / 3.6) + 0.5)
        assert e["time_s"] == expected
    assert road_graph.round_half_up(2.5) == 3
    assert road_graph.round_half_up(3.5) == 4


def test_inv04_long_edges_are_split(env):
    graph = run(env)
    assert max(e["length_m"] for e in graph["edges"]) <= 1000
    assert len(graph["nodes"]) > 6  # split nodes were added to the 6 kept OSM nodes


def test_inv05_no_candidate_ids(env):
    assert all(e["candidate_id"] is None for e in run(env)["edges"])


def test_inv06_hospitals_are_the_allowlist(env):
    graph = run(env)
    assert [h["name"] for h in graph["hospitals"]] == ["Fixture Hospital North", "Fixture Hospital East"]
    assert [h["id"] for h in graph["hospitals"]] == ["h1", "h2"]


def test_inv07_unknown_allowlisted_id_stops_the_run(env):
    with (env / "allowlist.txt").open("a", encoding="utf-8") as fh:
        fh.write("way/999\n")
    fails_without_graph(env, "way/999")


def test_inv08_communities_are_named_places_near_their_node(env):
    graph = run(env)
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert [c["name"] for c in graph["communities"]] == ["Fixture Village", "Fixture Town"]
    for c in graph["communities"]:
        lat, lon = PLACES[c["name"]]
        node = nodes[c["node"]]
        assert ox.distance.great_circle(lat, lon, node["lat"], node["lon"]) <= 3000


def test_inv09_far_community_is_dropped_and_logged(env, caplog):
    graph = run(env)
    assert "Fixture Far Hamlet" not in [c["name"] for c in graph["communities"]]
    logged = [r.getMessage() for r in caplog.records if "Fixture Far Hamlet" in r.getMessage()]
    assert logged and " m " in logged[0]


def test_inv10_population_is_null(env):
    assert all(c["population"] is None for c in run(env)["communities"])


def test_inv11_speed_table_covers_every_class(env):
    run(env)
    # trunk: median of first maxspeed values 60, 80 (from "80;100") and 90.
    assert speeds(env) == {"primary": 30, "secondary": 35, "trunk": 80, "unclassified": 25}


def test_inv12_same_input_gives_same_bytes(env):
    run(env)
    first = (env / "output" / "graph.json").read_bytes()
    run(env)
    assert (env / "output" / "graph.json").read_bytes() == first


def test_inv13_file_is_at_most_3_mb(env):
    run(env)
    assert (env / "output" / "graph.json").stat().st_size <= 3 * 1024 * 1024


def test_inv14_graph_is_weakly_connected(env):
    graph = run(env)
    g = nx.Graph()
    g.add_nodes_from(n["id"] for n in graph["nodes"])
    g.add_edges_from((e["from"], e["to"]) for e in graph["edges"])
    assert nx.is_connected(g)


def test_inv15_no_self_loops(env):
    assert all(e["from"] != e["to"] for e in run(env)["edges"])


def test_inv16_unnamed_hospital_stops_the_run(env):
    with (env / "allowlist.txt").open("a", encoding="utf-8") as fh:
        fh.write("node/36\n")
    fails_without_graph(env, "node/36")


def test_inv17_class_without_speed_stops_the_run(env, monkeypatch):
    settings = dataclasses.replace(road_graph.SETTINGS, fallback_speeds_kmh={"primary": 30, "secondary": 35})
    monkeypatch.setattr(road_graph, "SETTINGS", settings)
    fails_without_graph(env, "unclassified")


def test_inv18_oversized_graph_stops_the_run(env, monkeypatch):
    monkeypatch.setattr(road_graph, "MAX_GRAPH_BYTES", 100)
    fails_without_graph(env, "bytes")


def test_acc01_ruta32_cut_in_braulio_carrillo_keeps_a_path(tmp_path):
    if not all((REAL_OSM / name).is_file() for name in ("roads.osm", "features.osm")):
        pytest.skip(f"ACC-01 needs the real OSM download in {REAL_OSM}; run `road-graph --download` first")
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("way/1168011056\nway/326924912\n", encoding="utf-8")
    settings = dataclasses.replace(road_graph.SETTINGS, allowlist=allowlist)
    graph, _ = road_graph.build(REAL_OSM / "roads.osm", REAL_OSM / "features.osm", settings)
    lon = {n["id"]: n["lon"] for n in graph["nodes"]}
    g = nx.DiGraph()
    g.add_nodes_from(lon)
    cut = 0
    for e in graph["edges"]:
        if e["road"] == "Ruta 32" and -83.98 <= (lon[e["from"]] + lon[e["to"]]) / 2 <= -83.92:
            cut += 1
            continue
        g.add_edge(e["from"], e["to"])
        if not e["oneway"]:
            g.add_edge(e["to"], e["from"])
    assert cut > 0
    # Hospitals are numbered by ascending OSM id: h1 = way/326924912 (Guápiles), h2 = way/1168011056.
    node = {h["id"]: h["node"] for h in graph["hospitals"]}
    assert nx.has_path(g, node["h2"], node["h1"])
