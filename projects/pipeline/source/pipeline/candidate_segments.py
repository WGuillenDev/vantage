"""Candidate stage (P4): road edges near a radar change zone -> provisional candidate segments."""

import argparse
import json
import sys
from pathlib import Path

import shapely
from pyproj import Transformer
from shapely.geometry import LineString, shape

from pipeline.validate import _schema_errors

PIPELINE = Path(__file__).resolve().parents[2]
OUTPUT = PIPELINE / "output"
CANDIDATES = PIPELINE / "work" / "candidates.json"

# shortcut: provisional margin, revisit with S2 zone sizes (Ron)
MARGIN_M = 50
# CRTM05 (EPSG:8908), Costa Rica's national projection: metres across the whole area, which spans UTM zones 16 and 17.
_metres = Transformer.from_crs("EPSG:4326", "EPSG:8908", always_xy=True).transform


class CandidateSegmentsError(Exception):
    pass


def _num(item_id: str) -> int:
    return int(item_id[1:])


def find_candidates(graph: dict, change: dict, margin_m: float = MARGIN_M) -> list[dict]:
    zones = [(f["properties"], shapely.transform(shape(f["geometry"]), _metres, interleaved=False)) for f in change["features"]]
    touched: dict[str, list[dict]] = {}
    for e in graph["edges"]:
        line = shapely.transform(LineString(e["geometry"]), _metres, interleaved=False)
        hits = [props for props, polygon in zones if line.distance(polygon) <= margin_m]
        if hits:
            touched[e["id"]] = hits

    # Union-find: touched edges that share a node and carry the same road value join one candidate.
    parent = {edge_id: edge_id for edge_id in touched}

    def root(edge_id: str) -> str:
        while parent[edge_id] != edge_id:
            parent[edge_id] = parent[parent[edge_id]]
            edge_id = parent[edge_id]
        return edge_id

    at_node: dict[tuple, str] = {}
    for e in graph["edges"]:
        if e["id"] not in touched:
            continue
        for end in (e["from"], e["to"]):
            key = (end, e["road"])
            if key in at_node:
                parent[root(e["id"])] = root(at_node[key])
            else:
                at_node[key] = e["id"]

    groups: dict[str, list[str]] = {}
    for edge_id in touched:
        groups.setdefault(root(edge_id), []).append(edge_id)

    candidates = []
    for edge_ids in sorted((sorted(g, key=_num) for g in groups.values()), key=lambda g: _num(g[0])):
        zone_props = {p["id"]: p for edge_id in edge_ids for p in touched[edge_id]}
        zone_ids = sorted(zone_props, key=_num)
        candidates.append({
            "id": f"T-{len(candidates) + 1:02d}",
            "edge_ids": edge_ids,
            "zone_ids": zone_ids,
            "mean_delta_db": _mean_delta(zone_props[z] for z in zone_ids),
        })
    return candidates


def _mean_delta(zones) -> float:
    zones = list(zones)
    area = sum(z["area_m2"] for z in zones)
    if area == 0:
        return sum(z["mean_delta_db"] for z in zones) / len(zones)
    return sum(z["mean_delta_db"] * z["area_m2"] for z in zones) / area


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateSegmentsError(f"Cannot read {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="candidate-segments", description="Mark road edges near change zones as candidates.")
    parser.add_argument("--graph", type=Path, default=OUTPUT / "graph.json", help="graph.json from road-graph (P3)")
    parser.add_argument("--change", type=Path, default=OUTPUT / "change.geojson", help="change zones from P2")
    parser.add_argument("--candidates", type=Path, default=CANDIDATES, help="candidate list for impact-scoring (P5)")
    parser.add_argument("--out", type=Path, default=OUTPUT, help="folder for the marked graph.json")
    args = parser.parse_args(argv)
    try:
        graph = _load(args.graph)
        change = _load(args.change)
        errors = _schema_errors("change.geojson", change, "change.schema.json")
        if errors:
            raise CandidateSegmentsError("; ".join(errors))
        for e in graph["edges"]:
            if e["candidate_id"] is not None:
                raise CandidateSegmentsError(f"graph.json edge {e['id']} already has candidate_id {e['candidate_id']}")
        candidates = find_candidates(graph, change)
    except CandidateSegmentsError as exc:
        sys.exit(f"candidate-segments: {exc}")

    owner = {edge_id: c["id"] for c in candidates for edge_id in c["edge_ids"]}
    marked = {**graph, "edges": [{**e, "candidate_id": owner.get(e["id"])} for e in graph["edges"]]}
    args.candidates.parent.mkdir(parents=True, exist_ok=True)
    args.candidates.write_text(json.dumps({"candidates": candidates}, indent=2) + "\n", encoding="utf-8")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "graph.json").write_text(json.dumps(marked, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(candidates)} candidates to {args.candidates} and marked {args.out / 'graph.json'}")
