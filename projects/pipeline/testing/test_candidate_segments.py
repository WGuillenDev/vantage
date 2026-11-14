import json
from pathlib import Path

import pytest

from pipeline import candidate_segments
from pipeline.validate import _schema_errors

# Synthetic coordinates near lon -84 / lat 10 (CRTM05 needs Costa Rica positions); not real data.
LON, LAT = -84.0, 10.0
DEG_LAT_M = 110_600  # metres per degree of latitude near 10° N


def node(i: int, dlon: float, dlat: float = 0.0) -> dict:
    return {"id": f"n{i}", "lon": round(LON + dlon, 6), "lat": round(LAT + dlat, 6)}


def make_graph(nodes: list[dict], edges: list[tuple]) -> dict:
    """Edges are (from, to, road), numbered e1… in order, with straight geometry."""
    pos = {n["id"]: [n["lon"], n["lat"]] for n in nodes}
    return {
        "schema_version": "0.1",
        "nodes": nodes,
        "edges": [
            {"id": f"e{i}", "from": a, "to": b, "length_m": 100, "time_s": 9, "road": road,
             "oneway": False, "candidate_id": None, "geometry": [pos[a], pos[b]]}
            for i, (a, b, road) in enumerate(edges, start=1)
        ],
        "hospitals": [{"id": "h1", "name": "Fixture Hospital", "node": nodes[0]["id"]}],
        "communities": [],
    }


def box(zone_id: str, west: float, south: float, east: float, north: float,
        area_m2: float = 1000, delta: float = -4.0, multi: bool = False) -> dict:
    ring = [[LON + west, LAT + south], [LON + east, LAT + south], [LON + east, LAT + north],
            [LON + west, LAT + north], [LON + west, LAT + south]]
    geometry = {"type": "MultiPolygon", "coordinates": [[ring]]} if multi else {"type": "Polygon", "coordinates": [ring]}
    return {"type": "Feature", "geometry": geometry,
            "properties": {"id": zone_id, "area_m2": area_m2, "mean_delta_db": delta}}


def change(*zones: dict) -> dict:
    return {"type": "FeatureCollection", "schema_version": "0.1", "features": list(zones)}


def run(tmp_path: Path, graph: dict, zones: dict) -> tuple[dict, dict]:
    (tmp_path / "in").mkdir(exist_ok=True)
    (tmp_path / "in" / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
    (tmp_path / "in" / "change.geojson").write_text(json.dumps(zones), encoding="utf-8")
    candidate_segments.main(cli(tmp_path))
    return load(tmp_path / "work" / "candidates.json"), load(tmp_path / "out" / "graph.json")


def cli(tmp_path: Path) -> list[str]:
    return [
        "--graph", str(tmp_path / "in" / "graph.json"),
        "--change", str(tmp_path / "in" / "change.geojson"),
        "--candidates", str(tmp_path / "work" / "candidates.json"),
        "--out", str(tmp_path / "out"),
    ]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fails_without_output(tmp_path: Path, graph: dict, zones: dict, *expected: str) -> None:
    with pytest.raises(SystemExit) as exit_info:
        run(tmp_path, graph, zones)
    assert exit_info.value.code not in (0, None)
    for text in expected:
        assert text in str(exit_info.value.code)
    assert not (tmp_path / "work" / "candidates.json").exists()
    assert not (tmp_path / "out" / "graph.json").exists()


def straight_road() -> dict:
    """One road of four ~548 m edges along lat 10; a zone around n3 touches e2 and e3 only."""
    nodes = [node(i, (i - 3) * 0.005) for i in range(1, 6)]
    return make_graph(nodes, [(f"n{i}", f"n{i + 1}", "Fixture Road") for i in range(1, 5)])


def grouping_graph() -> tuple[dict, dict]:
    """Ruta 32 along lat 10 (e1–e5, ~219 m each), a side road and a null-road spur.

    z1 around n2 touches e1, e2 and the side road e6. z2 (a MultiPolygon) around n5 touches
    e4, e5 and the null-road edges e7, e8. e3 lies between the zones and is not touched.
    """
    nodes = [node(i, (i - 1) * 0.002) for i in range(1, 7)]
    nodes += [node(7, 0.002, 0.002), node(8, 0.008, 0.0002), node(9, 0.008, 0.0004)]
    edges = [(f"n{i}", f"n{i + 1}", "Ruta 32") for i in range(1, 6)]
    edges += [("n2", "n7", "Fixture Side Road"), ("n5", "n8", None), ("n8", "n9", None)]
    zones = change(
        box("z1", 0.0017, -0.0003, 0.0023, 0.0003, area_m2=100, delta=-2.0),
        box("z2", 0.0077, -0.0003, 0.0083, 0.0003, area_m2=300, delta=-6.0, multi=True),
    )
    return make_graph(nodes, edges), zones


def test_acc01_one_zone_one_candidate(tmp_path):
    candidates, _ = run(tmp_path, straight_road(), change(box("z1", -0.0005, -0.0005, 0.0005, 0.0005, delta=-4.2)))
    assert candidates == {"candidates": [{"id": "T-01", "edge_ids": ["e2", "e3"], "zone_ids": ["z1"], "mean_delta_db": -4.2}]}


def test_acc02_road_change_splits_candidates(tmp_path):
    nodes = [node(1, -0.005), node(2, 0.0), node(3, 0.0, 0.005)]
    graph = make_graph(nodes, [("n1", "n2", "Ruta 32"), ("n2", "n3", "Fixture Side Road")])
    candidates, _ = run(tmp_path, graph, change(box("z1", -0.0003, -0.0003, 0.0003, 0.0003)))
    assert [c["edge_ids"] for c in candidates["candidates"]] == [["e1"], ["e2"]]


def test_inv01_output_graph_is_valid_and_ids_resolve(tmp_path):
    graph, zones = grouping_graph()
    candidates, out = run(tmp_path, graph, zones)
    assert _schema_errors("graph.json", out, "graph.schema.json") == []
    ids = {c["id"] for c in candidates["candidates"]}
    assert {e["candidate_id"] for e in out["edges"]} - {None} <= ids


def test_inv02_inv03_margin_is_in_metres(tmp_path):
    # Two separate roads along lat 10; a zone 40 m north of the first and one 60 m north of the second.
    nodes = [node(1, -0.02), node(2, -0.01), node(3, 0.01), node(4, 0.02)]
    graph = make_graph(nodes, [("n1", "n2", "Fixture Road A"), ("n3", "n4", "Fixture Road B")])
    near, far = 40 / DEG_LAT_M, 60 / DEG_LAT_M
    zones = change(box("z1", -0.016, near, -0.014, near + 0.001), box("z2", 0.014, far, 0.016, far + 0.001))
    candidates, out = run(tmp_path, graph, zones)
    assert candidates["candidates"] == [{"id": "T-01", "edge_ids": ["e1"], "zone_ids": ["z1"], "mean_delta_db": -4.0}]
    assert [e["candidate_id"] for e in out["edges"]] == ["T-01", None]


def test_inv03_every_touched_edge_in_exactly_one_candidate(tmp_path):
    graph, zones = grouping_graph()
    candidates, _ = run(tmp_path, graph, zones)
    listed = [e for c in candidates["candidates"] for e in c["edge_ids"]]
    assert sorted(listed, key=lambda e: int(e[1:])) == ["e1", "e2", "e4", "e5", "e6", "e7", "e8"]
    assert len(listed) == len(set(listed))


def test_inv04_inv05_inv07_grouping_and_ids(tmp_path):
    graph, zones = grouping_graph()
    candidates, out = run(tmp_path, graph, zones)
    got = [(c["id"], c["edge_ids"], c["zone_ids"]) for c in candidates["candidates"]]
    assert got == [
        ("T-01", ["e1", "e2"], ["z1"]),  # Ruta 32 next to z1
        ("T-02", ["e4", "e5"], ["z2"]),  # Ruta 32 next to z2: not joined to T-01, e3 is untouched
        ("T-03", ["e6"], ["z1"]),  # side road: another road value
        ("T-04", ["e7", "e8"], ["z2"]),  # null road counts as one value
    ]
    roads = {e["id"]: e["road"] for e in out["edges"]}
    for c in candidates["candidates"]:
        assert len({roads[e] for e in c["edge_ids"]}) == 1


def test_inv06_area_weighted_mean(tmp_path):
    # e2 spans from z1 to z2: (-2 * 100 + -6 * 300) / 400 = -5.0
    nodes = [node(1, -0.01), node(2, 0.0), node(3, 0.002)]
    graph = make_graph(nodes, [("n1", "n2", "Fixture Road"), ("n2", "n3", "Fixture Road")])
    zones = change(box("z1", 0.0019, -0.0002, 0.0021, 0.0002, area_m2=100, delta=-2.0),
                   box("z2", 0.0009, -0.0002, 0.0011, 0.0002, area_m2=300, delta=-6.0))
    candidates, _ = run(tmp_path, graph, zones)
    assert candidates["candidates"][0]["zone_ids"] == ["z1", "z2"]
    assert candidates["candidates"][0]["mean_delta_db"] == -5.0


def test_inv06_plain_mean_when_area_is_zero(tmp_path):
    nodes = [node(1, -0.01), node(2, 0.0), node(3, 0.002)]
    graph = make_graph(nodes, [("n1", "n2", "Fixture Road"), ("n2", "n3", "Fixture Road")])
    zones = change(box("z1", 0.0019, -0.0002, 0.0021, 0.0002, area_m2=0, delta=-2.0),
                   box("z2", 0.0009, -0.0002, 0.0011, 0.0002, area_m2=0, delta=-6.0))
    candidates, _ = run(tmp_path, graph, zones)
    assert candidates["candidates"][0]["mean_delta_db"] == -4.0


def test_inv08_only_candidate_ids_change(tmp_path):
    graph, zones = grouping_graph()
    candidates, out = run(tmp_path, graph, zones)
    owner = {e: c["id"] for c in candidates["candidates"] for e in c["edge_ids"]}
    for before, after in zip(graph["edges"], out["edges"], strict=True):
        assert after["candidate_id"] == owner.get(before["id"])
        assert {k: v for k, v in after.items() if k != "candidate_id"} == {k: v for k, v in before.items() if k != "candidate_id"}
    assert {k: v for k, v in out.items() if k != "edges"} == {k: v for k, v in graph.items() if k != "edges"}


def test_inv08_no_zones_leaves_graph_unchanged(tmp_path):
    graph = straight_road()
    candidates, out = run(tmp_path, graph, change())
    assert candidates == {"candidates": []}
    assert out == graph


def test_inv09_existing_candidate_id_stops_the_run(tmp_path):
    graph = straight_road()
    graph["edges"][1]["candidate_id"] = "T-01"
    fails_without_output(tmp_path, graph, change(), "e2")


def test_inv10_invalid_change_stops_the_run(tmp_path):
    zones = change(box("z1", -0.0005, -0.0005, 0.0005, 0.0005))
    del zones["features"][0]["properties"]["area_m2"]
    fails_without_output(tmp_path, straight_road(), zones, "change.geojson", "area_m2")


def test_inv11_same_inputs_same_bytes(tmp_path):
    graph, zones = grouping_graph()
    run(tmp_path, graph, zones)
    files = [tmp_path / "work" / "candidates.json", tmp_path / "out" / "graph.json"]
    first = [f.read_bytes() for f in files]
    run(tmp_path, graph, zones)
    assert [f.read_bytes() for f in files] == first
