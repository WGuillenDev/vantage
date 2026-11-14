import json
import shutil
from pathlib import Path

import pytest

from pipeline import impact_scoring
from pipeline.validate import validate_dir

EXAMPLES = Path(__file__).resolve().parents[2] / "contract" / "examples"
BOTH_ALTERNATES = [{"name": "Ruta 126", "vehicles": "light"}, {"name": "Ruta 10", "vehicles": "freight"}]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mock_candidates() -> list[dict]:
    """The mock's four candidates as P4 would hand them over (provisional ids = the mock graph's ids)."""
    return [
        {"id": c["id"], "edge_ids": c["edge_ids"], "zone_ids": c["zone_ids"], "mean_delta_db": c["mean_delta_db"]}
        for c in load(EXAMPLES / "scenarios.json")["candidates"]
    ]


def score(tmp_path: Path, graph: dict, candidates: list[dict]) -> tuple[dict, dict]:
    (tmp_path / "in").mkdir(exist_ok=True)
    (tmp_path / "in" / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
    (tmp_path / "in" / "candidates.json").write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    impact_scoring.main(cli(tmp_path))
    return load(tmp_path / "out" / "scenarios.json"), load(tmp_path / "out" / "graph.json")


def cli(tmp_path: Path) -> list[str]:
    return [
        "--graph", str(tmp_path / "in" / "graph.json"),
        "--candidates", str(tmp_path / "in" / "candidates.json"),
        "--change", str(EXAMPLES / "change.geojson"),
        "--out", str(tmp_path / "out"),
    ]


def run_mock(tmp_path: Path) -> tuple[dict, dict]:
    return score(tmp_path, load(EXAMPLES / "graph.json"), mock_candidates())


def by_edges(scenarios: dict) -> dict:
    return {tuple(c["edge_ids"]): c for c in scenarios["candidates"]}


def tiny_graph(nodes: int, edges: list[tuple], hospitals: list[tuple], communities: list[tuple]) -> dict:
    """Hand-made graph: edges (from, to, time_s[, oneway]) numbered e1…, synthetic coordinates."""
    graph = {
        "schema_version": "0.1",
        "nodes": [{"id": f"n{i}", "lon": 10.0 + i / 1000, "lat": 0.0} for i in range(1, nodes + 1)],
        "edges": [],
        "hospitals": [{"id": h, "name": f"Fixture Hospital {h}", "node": n} for h, n in hospitals],
        "communities": [{"id": c, "name": f"Fixture Community {c}", "node": n, "population": p} for c, n, p in communities],
    }
    for i, (a, b, t, *oneway) in enumerate(edges, start=1):
        geometry = [[10.0 + int(a[1:]) / 1000, 0.0], [10.0 + int(b[1:]) / 1000, 0.0]]
        graph["edges"].append({
            "id": f"e{i}", "from": a, "to": b, "length_m": t, "time_s": t, "road": None,
            "oneway": bool(oneway and oneway[0]), "candidate_id": None, "geometry": geometry,
        })
    return graph


def mark(graph: dict, candidates: list[dict]) -> list[dict]:
    """Put provisional candidate ids on the graph edges, as P4 does."""
    edges = {e["id"]: e for e in graph["edges"]}
    for c in candidates:
        for edge_id in c["edge_ids"]:
            edges[edge_id]["candidate_id"] = c["id"]
    return candidates


def candidate(pid: str, *edge_ids: str) -> dict:
    return {"id": pid, "edge_ids": list(edge_ids), "zone_ids": ["z1"], "mean_delta_db": None}


def test_acc01_population_outranks_longer_extra_time(tmp_path):
    scenarios, _ = run_mock(tmp_path)
    c = by_edges(scenarios)
    assert c[("e3",)]["rank"] == 1 and c[("e3",)]["criticality"] == 2622000
    assert c[("e2",)]["extra_time_s"] == 1200 and c[("e2",)]["rank"] > 1


def test_acc02_matches_contract_mock(tmp_path):
    scenarios, _ = run_mock(tmp_path)
    oracle = load(EXAMPLES / "scenarios.json")
    assert scenarios["baseline"] == oracle["baseline"]
    got = by_edges(scenarios)
    for expected in oracle["candidates"]:
        actual = got[tuple(expected["edge_ids"])]
        for key in ("per_community", "extra_time_s", "population_dependent", "criticality", "rank",
                    "affected_community_ids", "isolated_community_ids"):
            assert actual[key] == expected[key], (expected["edge_ids"], key)


def test_acc03_candidate_that_affects_nobody(tmp_path):
    # c1 reaches h1 over e1; e2 is a dead end beyond the hospital.
    graph = tiny_graph(3, [("n1", "n2", 100), ("n2", "n3", 100)], [("h1", "n2")], [("c1", "n1", 500)])
    scenarios, _ = score(tmp_path, graph, mark(graph, [candidate("T-01", "e2")]))
    c = scenarios["candidates"][0]
    assert (c["extra_time_s"], c["criticality"], c["population_dependent"]) == (0, 0, None)
    assert c["affected_community_ids"] == [] and c["isolated_community_ids"] == [] and c["per_community"] == []


def test_acc04_isolation_outranks_extra_time_without_population(tmp_path):
    # e1 closed: c2 detours over e2+e3 (+100 s). e4 closed: c1 is isolated. Edge-id order alone would put e1 first.
    graph = tiny_graph(
        4,
        [("n3", "n1", 100), ("n3", "n4", 100), ("n4", "n1", 100), ("n2", "n1", 100)],
        [("h1", "n1")],
        [("c1", "n2", None), ("c2", "n3", None)],
    )
    scenarios, _ = score(tmp_path, graph, mark(graph, [candidate("T-01", "e1"), candidate("T-02", "e4")]))
    c = by_edges(scenarios)
    assert c[("e1",)]["criticality"] == c[("e4",)]["criticality"] == 0
    assert c[("e4",)]["extra_time_s"] is None and c[("e1",)]["extra_time_s"] == 100
    assert c[("e4",)]["rank"] == 1 and c[("e1",)]["rank"] == 2


def test_inv01_outputs_validate_with_change(tmp_path):
    run_mock(tmp_path)
    folder = tmp_path / "validate"
    shutil.copytree(EXAMPLES, folder)
    for name in ("graph.json", "scenarios.json"):
        shutil.copy(tmp_path / "out" / name, folder / name)
    assert validate_dir(folder) == []


def test_inv02_baseline_lists_every_community_once(tmp_path):
    # c2 can only be left by a one-way edge pointing into it, so it has no route.
    graph = tiny_graph(3, [("n1", "n2", 100), ("n2", "n3", 100, True)], [("h1", "n1")],
                       [("c1", "n2", 10), ("c2", "n3", 10)])
    scenarios, _ = score(tmp_path, graph, mark(graph, [candidate("T-01", "e1")]))
    assert scenarios["baseline"] == [
        {"community_id": "c1", "time_s": 100, "hospital_id": "h1"},
        {"community_id": "c2", "time_s": None, "hospital_id": None},
    ]
    # INV-03: a community without a baseline route is never affected.
    assert scenarios["candidates"][0]["affected_community_ids"] == ["c1"]


def test_inv03_inv04_affected_are_isolated_or_slower(tmp_path):
    scenarios, _ = run_mock(tmp_path)
    base = {b["community_id"]: b["time_s"] for b in scenarios["baseline"]}
    for c in scenarios["candidates"]:
        listed = [p["community_id"] for p in c["per_community"]]
        assert listed == c["affected_community_ids"]
        for p in c["per_community"]:
            assert base[p["community_id"]] is not None
            assert p["time_s"] is None or p["extra_s"] == p["time_s"] - base[p["community_id"]] > 0


def test_inv05_isolated_have_null_values(tmp_path):
    scenarios, _ = run_mock(tmp_path)
    isolated = by_edges(scenarios)[("e9",)]
    assert isolated["isolated_community_ids"] == ["c4"]
    assert isolated["per_community"] == [{"community_id": "c4", "time_s": None, "extra_s": None, "hospital_id": None}]


def test_inv06_extra_time_is_max_over_non_isolated(tmp_path):
    scenarios, _ = run_mock(tmp_path)
    for c in scenarios["candidates"]:
        finite = [p["extra_s"] for p in c["per_community"] if p["extra_s"] is not None]
        expected = max(finite) if finite else (None if c["per_community"] else 0)
        assert c["extra_time_s"] == expected


def test_inv07_inv08_inv09_criticality_penalty_population(tmp_path):
    scenarios, _ = run_mock(tmp_path)
    c = by_edges(scenarios)
    assert c[("e9",)]["criticality"] == 300 * 1200  # isolated c4 uses the penalty: largest finite extra_s
    assert c[("e4",)]["criticality"] == 0 and c[("e4",)]["population_dependent"] is None  # c5 has no population
    assert c[("e3",)]["population_dependent"] == 1200 + 800 + 300


def test_inv08_penalty_is_zero_without_finite_extra(tmp_path):
    graph = tiny_graph(2, [("n1", "n2", 100)], [("h1", "n1")], [("c1", "n2", 50)])
    scenarios, _ = score(tmp_path, graph, mark(graph, [candidate("T-01", "e1")]))
    c = scenarios["candidates"][0]
    assert c["isolated_community_ids"] == ["c1"] and c["criticality"] == 0


def test_inv10_inv11_rank_order_and_ids(tmp_path):
    scenarios, graph = run_mock(tmp_path)
    assert [c["edge_ids"] for c in scenarios["candidates"]] == [["e3"], ["e2"], ["e9"], ["e4"]]
    assert [(c["rank"], c["id"]) for c in scenarios["candidates"]] == [(1, "T-01"), (2, "T-02"), (3, "T-03"), (4, "T-04")]
    assert impact_scoring.final_id(7) == "T-07" and impact_scoring.final_id(123) == "T-123"


def test_inv12_graph_only_changes_candidate_ids(tmp_path):
    scenarios, graph = run_mock(tmp_path)
    original = load(EXAMPLES / "graph.json")
    final = {e: c["id"] for c in scenarios["candidates"] for e in c["edge_ids"]}
    for before, after in zip(original["edges"], graph["edges"], strict=True):
        assert after["candidate_id"] == final.get(before["id"])
        assert {k: v for k, v in after.items() if k != "candidate_id"} == {k: v for k, v in before.items() if k != "candidate_id"}
    assert {k: v for k, v in graph.items() if k != "edges"} == {k: v for k, v in original.items() if k != "edges"}


def test_inv13_zones_and_delta_copied(tmp_path):
    scenarios, _ = run_mock(tmp_path)
    got = by_edges(scenarios)
    for given in mock_candidates():
        actual = got[tuple(given["edge_ids"])]
        assert (actual["zone_ids"], actual["mean_delta_db"]) == (given["zone_ids"], given["mean_delta_db"])


def test_inv14_hospital_tie_goes_to_lowest_number(tmp_path):
    # h2 and h10 are both 100 s from c1; by text "h10" < "h2", by number h2 wins.
    graph = tiny_graph(3, [("n1", "n2", 100), ("n1", "n3", 100)], [("h10", "n2"), ("h2", "n3")], [("c1", "n1", 5)])
    scenarios, _ = score(tmp_path, graph, mark(graph, [candidate("T-01", "e1")]))
    assert scenarios["baseline"] == [{"community_id": "c1", "time_s": 100, "hospital_id": "h2"}]


def test_inv15_same_inputs_same_bytes(tmp_path):
    run_mock(tmp_path)
    first = [(tmp_path / "out" / n).read_bytes() for n in ("graph.json", "scenarios.json")]
    run_mock(tmp_path)
    assert [(tmp_path / "out" / n).read_bytes() for n in ("graph.json", "scenarios.json")] == first


def test_inv16_alternates_only_for_ruta_32(tmp_path):
    scenarios, _ = run_mock(tmp_path)
    c = by_edges(scenarios)
    assert c[("e2",)]["alternates"] == BOTH_ALTERNATES
    assert c[("e9",)]["alternates"] == []  # e9 has road null


def test_inv17_failed_cross_check_writes_nothing(tmp_path):
    candidates = mock_candidates()
    candidates[0]["zone_ids"] = ["z99"]
    with pytest.raises(SystemExit) as exit_info:
        score(tmp_path, load(EXAMPLES / "graph.json"), candidates)
    assert exit_info.value.code not in (0, None) and "z99" in str(exit_info.value.code)
    assert not (tmp_path / "out" / "graph.json").exists()
    assert not (tmp_path / "out" / "scenarios.json").exists()
