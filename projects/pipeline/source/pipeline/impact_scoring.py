"""Impact stage (P5): close one candidate at a time, rank by criticality, write scenarios.json and graph.json."""

import argparse
import heapq
import json
import sys
from pathlib import Path

from pipeline.validate import _check_graph, _check_scenarios, _schema_errors

PIPELINE = Path(__file__).resolve().parents[2]
OUTPUT = PIPELINE / "output"
# shortcut: provisional hand-off from candidate-segments (P4), which has no spec yet; replace once P4 fixes it.
# Shape: {"candidates": [{"id": "T-xx" (provisional), "edge_ids": [...], "zone_ids": [...], "mean_delta_db": float | null}]}
CANDIDATES = PIPELINE / "work" / "candidates.json"
ALTERNATES = [{"name": "Ruta 126", "vehicles": "light"}, {"name": "Ruta 10", "vehicles": "freight"}]


class ImpactScoringError(Exception):
    pass


def _num(item_id: str) -> int:
    """Number of an id such as c12, e3 or h10, so h2 sorts before h10."""
    return int("".join(ch for ch in item_id if ch.isdigit()))


def final_id(rank: int) -> str:
    return f"T-{rank:02d}"


def _nearest_hospitals(graph: dict, closed: set[str]) -> dict[str, tuple[int, str]]:
    """Per node: (route time, hospital id) to the nearest hospital, ties to the lowest hospital number."""
    reverse: dict[str, list[tuple[str, int]]] = {}
    for e in graph["edges"]:
        if e["id"] in closed:
            continue
        # Routes run community -> hospital, so the search walks edges backwards from the hospitals.
        reverse.setdefault(e["to"], []).append((e["from"], e["time_s"]))
        if not e["oneway"]:
            reverse.setdefault(e["from"], []).append((e["to"], e["time_s"]))
    heap = [(0, _num(h["id"]), h["node"], h["id"]) for h in graph["hospitals"]]
    heapq.heapify(heap)
    best: dict[str, tuple[int, str]] = {}
    while heap:
        time, number, node, hospital = heapq.heappop(heap)
        if node in best:
            continue
        best[node] = (time, hospital)
        for previous, cost in reverse.get(node, []):
            if previous not in best:
                heapq.heappush(heap, (time + cost, number, previous, hospital))
    return best


def _routes(graph: dict, closed: set[str]) -> dict[str, tuple[int, str] | None]:
    nearest = _nearest_hospitals(graph, closed)
    return {c["id"]: nearest.get(c["node"]) for c in graph["communities"]}


def score(graph: dict, candidates: list[dict]) -> tuple[dict, dict]:
    communities = sorted(graph["communities"], key=lambda c: _num(c["id"]))
    population = {c["id"]: c["population"] for c in communities}
    roads = {e["id"]: e["road"] for e in graph["edges"]}
    baseline = _routes(graph, set())

    results = []
    for given in candidates:
        after = _routes(graph, set(given["edge_ids"]))
        per_community = []
        for c in communities:
            base, now = baseline[c["id"]], after[c["id"]]
            if base is None:
                continue  # never affected without a baseline route
            if now is None:
                per_community.append({"community_id": c["id"], "time_s": None, "extra_s": None, "hospital_id": None})
            elif now[0] > base[0]:
                per_community.append({"community_id": c["id"], "time_s": now[0], "extra_s": now[0] - base[0], "hospital_id": now[1]})
        results.append((given, per_community))

    penalty = max((p["extra_s"] for _, pc in results for p in pc if p["extra_s"] is not None), default=0)
    scored = []
    for given, per_community in results:
        affected = [p["community_id"] for p in per_community]
        isolated = [p["community_id"] for p in per_community if p["time_s"] is None]
        finite = [p["extra_s"] for p in per_community if p["extra_s"] is not None]
        known = [population[c] for c in affected if population[c] is not None]
        criticality = sum(
            (population[p["community_id"]] or 0) * (penalty if p["extra_s"] is None else p["extra_s"]) for p in per_community
        )
        edge_ids = sorted(given["edge_ids"], key=_num)
        scored.append({
            "edge_ids": edge_ids,
            "zone_ids": sorted(given["zone_ids"], key=_num),
            "mean_delta_db": given["mean_delta_db"],
            "criticality": criticality,
            "extra_time_s": max(finite) if finite else (None if affected else 0),
            "population_dependent": sum(known) if known else None,
            "affected_community_ids": affected,
            "isolated_community_ids": isolated,
            "per_community": per_community,
            "alternates": ALTERNATES if any(roads.get(e) == "Ruta 32" for e in edge_ids) else [],
        })

    scored.sort(key=lambda c: (
        -c["criticality"],
        -len(c["isolated_community_ids"]),
        c["extra_time_s"] is None,
        -(c["extra_time_s"] or 0),
        min((_num(e) for e in c["edge_ids"]), default=0),
    ))
    ranked = [{"id": final_id(rank), "rank": rank, **c} for rank, c in enumerate(scored, start=1)]

    edge_final = {e: c["id"] for c in ranked for e in c["edge_ids"]}
    out_graph = {**graph, "edges": [{**e, "candidate_id": edge_final.get(e["id"])} for e in graph["edges"]]}
    scenarios = {
        "schema_version": "0.1",
        "baseline": [_baseline_row(c["id"], baseline[c["id"]]) for c in communities],
        "candidates": ranked,
    }
    return scenarios, out_graph


def _baseline_row(community_id: str, route: tuple[int, str] | None) -> dict:
    time_s, hospital_id = route if route else (None, None)
    return {"community_id": community_id, "time_s": time_s, "hospital_id": hospital_id}


def _check_inputs(graph: dict, candidates: list[dict]) -> None:
    """The provisional ids on graph edges must match the candidate list from P4."""
    listed = {e: c["id"] for c in candidates for e in c["edge_ids"]}
    for e in graph["edges"]:
        if e["candidate_id"] != listed.get(e["id"]):
            raise ImpactScoringError(
                f"graph.json edge {e['id']} has candidate_id {e['candidate_id']} "
                f"but the candidate list gives {listed.get(e['id'])}"
            )


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImpactScoringError(f"Cannot read {path}: {exc}") from exc


def write_pair(graph: dict, scenarios: dict, zone_ids: set[str], out: Path) -> None:
    """Write both files only if the contracts.md section 8 checks pass on the pair."""
    errors = _schema_errors("graph.json", graph, "graph.schema.json")
    errors += _schema_errors("scenarios.json", scenarios, "scenarios.schema.json")
    if not errors:
        errors = _check_graph(graph) + _check_scenarios(graph, scenarios, zone_ids)
    if errors:
        raise ImpactScoringError("Cross-reference checks failed, nothing written: " + "; ".join(errors))
    out.mkdir(parents=True, exist_ok=True)
    (out / "graph.json").write_text(json.dumps(graph, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    (out / "scenarios.json").write_text(json.dumps(scenarios, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="impact-scoring", description="Rank candidate segments by hospital-access impact.")
    parser.add_argument("--graph", type=Path, default=OUTPUT / "graph.json", help="graph.json from candidate-segments (P4)")
    parser.add_argument("--candidates", type=Path, default=CANDIDATES, help="provisional candidate list from P4")
    parser.add_argument("--change", type=Path, default=OUTPUT / "change.geojson", help="change.geojson the zone ids refer to")
    parser.add_argument("--out", type=Path, default=OUTPUT, help="folder for graph.json and scenarios.json")
    args = parser.parse_args(argv)
    try:
        graph = _load(args.graph)
        candidates = _load(args.candidates)["candidates"]
        zones = {f["properties"]["id"] for f in _load(args.change)["features"]}
        _check_inputs(graph, candidates)
        scenarios, out_graph = score(graph, candidates)
        write_pair(out_graph, scenarios, zones, args.out)
    except ImpactScoringError as exc:
        sys.exit(f"impact-scoring: {exc}")
    print(f"Wrote {args.out / 'graph.json'} and {args.out / 'scenarios.json'} ({len(scenarios['candidates'])} candidates)")
