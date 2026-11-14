"""Adversarial tests for road-graph (P3): cases the spec's own tests do not reach."""

import os
import subprocess
import sys
from pathlib import Path

from pipeline import road_graph

FIXTURE = Path(__file__).parent / "fixtures" / "road_graph"
BBOX = (9.995, -0.005, 10.05, 0.02)

# Builds graph.json in a fresh interpreter, so string hashing uses that process's seed.
BUILD = """
import sys
from pathlib import Path
from pipeline import road_graph
roads, features, allowlist, out = map(Path, sys.argv[1:5])
settings = road_graph.Settings(bbox=(9.995, -0.005, 10.05, 0.02), allowlist=allowlist)
road_graph.write_graph(road_graph.build(roads, features, settings), out)
"""


def build_in_process(tmp_path: Path, roads: Path, seed: int) -> bytes:
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("node/30\n", encoding="utf-8")
    out = tmp_path / f"graph-{seed}.json"
    env = {**os.environ, "PYTHONHASHSEED": str(seed)}
    subprocess.run(
        [sys.executable, "-c", BUILD, str(roads), str(FIXTURE / "features.osm"), str(allowlist), str(out)],
        check=True, env=env, capture_output=True,
    )
    return out.read_bytes()


def build_fixture(tmp_path: Path, allowlist_text: str) -> dict:
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text(allowlist_text, encoding="utf-8")
    return road_graph.build(FIXTURE / "roads.osm", FIXTURE / "features.osm", road_graph.Settings(bbox=BBOX, allowlist=allowlist))


def test_inv12_adversarial_base_fixture_is_hash_seed_independent(tmp_path):
    # INV-12 must hold across processes (`make all` twice), not only within one test process.
    outputs = {build_in_process(tmp_path, FIXTURE / "roads.osm", seed) for seed in range(4)}
    assert len(outputs) == 1


def test_direction_adversarial_oneway_edges_keep_osm_direction(tmp_path):
    graph = build_fixture(tmp_path, "node/30\n")
    node = {n["id"]: (n["lon"], n["lat"]) for n in graph["nodes"]}
    oneway = [e for e in graph["edges"] if e["oneway"]]
    # Way 103 runs north (3 -> 5 -> 6) and way 105 runs south (7 -> 4): both must keep that direction.
    primary = next(e for e in oneway if e["road"] == "Fixture Primary")
    assert node[primary["to"]][1] > node[primary["from"]][1]
    link = next(e for e in oneway if e["road"] is None)
    assert node[link["to"]][1] < node[link["from"]][1]
    # Two-way roads appear once, never as a reversed duplicate.
    pairs = {(e["from"], e["to"]) for e in graph["edges"]}
    assert not any((b, a) in pairs for a, b in pairs)


def test_inv06_adversarial_hospitals_snap_to_their_nearest_node(tmp_path):
    graph = build_fixture(tmp_path, "way/301\nnode/30\n")
    node = {n["id"]: (n["lon"], n["lat"]) for n in graph["nodes"]}
    # node/30 sits next to OSM node 1 (10.0000, 0.0000); way/301 is centred on OSM node 7 (10.0200, 0.0100).
    assert [node[h["node"]] for h in graph["hospitals"]] == [(10.0, 0.0), (10.02, 0.01)]
