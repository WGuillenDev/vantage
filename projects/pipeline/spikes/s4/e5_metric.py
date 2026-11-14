"""Spike S4' (E5): compare the nearest-hospital metric (N) with a reference-hospital metric (R).

Criteria are in SPIKING.md (S4'), written before running. Reuses road_graph.build from the
feat/road-graph branch. Spike-only assumptions: hospitals = amenity=hospital named "Hospital*";
unclassified = 30 km/h; no population, so only affected counts and extra time are measured.
Usage: uv run --project <pipeline> python -I e5_metric.py <osm_dir> <out_dir>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox

from pipeline import road_graph as rg

work, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
REFERENCE = ("Calderón Guardia", "Guápiles", "Tony Facio")
PARK = (-83.98, -83.92)

F = ox.features_from_xml(work / "features.osm").reset_index()
hosp = F[(F.get("amenity") == "hospital") & F["name"].fillna("").str.startswith("Hospital")]
allow = out_dir / "allowlist_spike.txt"
allow.write_text("\n".join(f"{r.element}/{r.id}" for r in hosp.itertuples()), encoding="utf-8")
rg.SPEED_MODEL_KMH.setdefault("unclassified", 30)
graph = rg.build(work / "roads.osm", work / "features.osm", rg.Settings(bbox=rg.SETTINGS.bbox, allowlist=allow))

by_id = {e["id"]: e for e in graph["edges"]}
node_xy = {n["id"]: (n["lon"], n["lat"]) for n in graph["nodes"]}
G = nx.MultiDiGraph()
for e in graph["edges"]:
    G.add_edge(e["from"], e["to"], key=e["id"], t=e["time_s"])
    if not e["oneway"]:
        G.add_edge(e["to"], e["from"], key=e["id"], t=e["time_s"])
hosp_nodes = {h["node"]: h["name"] for h in graph["hospitals"]}
ref_nodes = {n: name for n, name in hosp_nodes.items() if any(k in name for k in REFERENCE)}
missing = [k for k in REFERENCE if not any(k in name for name in ref_nodes.values())]
comm = graph["communities"]


def times(g, targets, comm):
    d = nx.multi_source_dijkstra_path_length(g.reverse(copy=False), targets & set(g.nodes), weight="t")
    return {c["id"]: d.get(c["node"]) for c in comm}


# Ruta 32 segments split at junctions (undirected degree != 2)
U = nx.Graph()
for e in graph["edges"]:
    U.add_edge(e["from"], e["to"])
junction = {n for n in U if U.degree(n) != 2}
adj = defaultdict(list)
for e in graph["edges"]:
    if e["road"] == "Ruta 32":
        adj[e["from"]].append(e["id"])
        adj[e["to"]].append(e["id"])
seen, segments = set(), []
for e in graph["edges"]:
    if e["road"] != "Ruta 32" or e["id"] in seen:
        continue
    seg, stack = [], [e["id"]]
    while stack:
        eid = stack.pop()
        if eid in seen:
            continue
        seen.add(eid)
        seg.append(eid)
        for n in (by_id[eid]["from"], by_id[eid]["to"]):
            if n not in junction:
                stack += [x for x in adj[n] if x not in seen]
    segments.append(seg)


def measure(targets, comm, clean_q1, segments):
    base = times(G, targets, comm)
    rows = []
    for seg in segments:
        g2 = G.copy()
        for x in seg:
            e = by_id[x]
            g2.remove_edges_from([(e["from"], e["to"], x), (e["to"], e["from"], x)])
        after = times(g2, targets, comm)
        cut_ends = {n for x in seg for n in (by_id[x]["from"], by_id[x]["to"])}
        comp_has_target = {}
        U2 = g2.to_undirected(as_view=True)
        aff = [c for c in comm if base[c["id"]] is not None and (after[c["id"]] is None or after[c["id"]] > base[c["id"]])]
        iso = [c for c in aff if after[c["id"]] is None]
        suspect = 0
        why = {"on_cut_node": 0, "oneway_only": 0}
        for c in iso:
            n = c["node"]
            if n in cut_ends:
                suspect += 1
                why["on_cut_node"] += 1
                continue
            comp_has_target[n] = bool(nx.node_connected_component(U2, n) & targets)
            suspect += comp_has_target[n]
            why["oneway_only"] += comp_has_target[n]
        xs = [node_xy[by_id[x]["from"]][0] for x in seg] + [node_xy[by_id[x]["to"]][0] for x in seg]
        mids = [(node_xy[by_id[x]["from"]][0] + node_xy[by_id[x]["to"]][0]) / 2 for x in seg]
        rows.append({"edges": len(seg), "length_km": round(sum(by_id[x]["length_m"] for x in seg) / 1000, 1),
                     "lon_range": [round(min(xs), 3), round(max(xs), 3)],
                     "park": any(PARK[0] <= m <= PARK[1] for m in mids),
                     "affected": len(aff), "isolated": len(iso), "suspect_isolated": suspect, "why": why, "isolated_ids": [c["id"] for c in iso],
                     "max_extra_min": round(max([after[c["id"]] - base[c["id"]] for c in aff if after[c["id"]] is not None], default=0) / 60, 1)})
    no_path = sum(1 for t in base.values() if t is None)
    share_aff = sum(1 for r in rows if r["affected"]) / len(rows)
    pairs = sum(r["isolated"] for r in rows)
    sus = sum(r["suspect_isolated"] for r in rows)
    park = [r for r in rows if r["park"]]
    return {"no_path_baseline": no_path, "segments": len(rows), "share_with_affected": round(share_aff, 3),
            "park_segments_affected": [r["affected"] for r in park], "isolated_pairs": pairs, "suspect_pairs": sus,
            "suspect_share": round(sus / pairs, 3) if pairs else 0.0,
            "why_totals": {k: sum(r["why"][k] for r in rows) for k in ("on_cut_node", "oneway_only")},
            "unique_isolated_communities": len({i for r in rows for i in r["isolated_ids"]}),
            "segments_with_isolated": sum(1 for r in rows if r["isolated"]),
            "share_with_clean_affected": round(sum(1 for r in rows if r["affected"] - r["suspect_isolated"] > 0) / len(rows), 3),
            "park_clean_affected": [r["affected"] - r["suspect_isolated"] for r in park],
            "Q1": (sum(1 for r in rows if r["affected"] - r["suspect_isolated"] > 0) / len(rows) >= 0.5
                   and bool(park) and all(r["affected"] - r["suspect_isolated"] > 0 for r in park)) if clean_q1
                  else (share_aff >= 0.5 and all(r["affected"] > 0 for r in park) and bool(park)),
            "Q2": (sus / pairs <= 0.2) if pairs else True}, rows


# v3: both carriageways. Add Ruta 32 edges whose midpoint is within ~120 m of the segment, then merge overlapping groups.
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

K = np.cos(np.radians(10.0))
r32_edges = [e for e in graph["edges"] if e["road"] == "Ruta 32"]


def line(e):
    return LineString([(p[0] * K, p[1]) for p in e["geometry"]])


mid = {e["id"]: line(e).interpolate(0.5, normalized=True) for e in r32_edges}
groups = []
for seg in segments:
    area = unary_union([line(by_id[x]) for x in seg]).buffer(120 / 111_000)
    groups.append(set(seg) | {e["id"] for e in r32_edges if area.contains(mid[e["id"]])})
merged = []
for g_ in groups:
    hit = [m for m in merged if m & g_]
    for m in hit:
        merged.remove(m)
        g_ = g_ | m
    merged.append(g_)
segments_v3 = [sorted(m) for m in merged]

# v2: re-snap to the largest strongly connected component (approximate, see SPIKING.md S4' v2)
scc = max(nx.strongly_connected_components(G), key=len)
scc_ids = sorted(scc)
xy = np.array([[node_xy[n][0] * np.cos(np.radians(10.0)), node_xy[n][1]] for n in scc_ids])


def resnap(n):
    if n in scc:
        return n, 0.0
    p = np.array([node_xy[n][0] * np.cos(np.radians(10.0)), node_xy[n][1]])
    d = np.hypot(*(xy - p).T)
    j = int(d.argmin())
    return scc_ids[j], float(d[j]) * 111_000


moved = [resnap(c["node"]) for c in comm]
comm_v2 = [dict(c, node=m[0]) for c, m in zip(comm, moved)]
hosp_v2 = {resnap(n)[0]: name for n, name in hosp_nodes.items()}
ref_v2 = {n: name for n, name in hosp_v2.items() if any(k in name for k in REFERENCE)}
NATIONAL = ("Calderón Guardia", "México", "San Juan de Dios")
nat_v2 = {n: name for n, name in hosp_v2.items() if any(k in name for k in NATIONAL)}
out = {"graph": {"nodes": len(graph["nodes"]), "edges": len(graph["edges"]), "hospitals": sorted(hosp_nodes.values()),
                 "communities": len(comm), "scc_nodes": len(scc),
                 "communities_moved": sum(1 for m in moved if m[1] > 0), "max_move_m": round(max(m[1] for m in moved)),
                 "median_move_m": round(float(np.median([m[1] for m in moved if m[1] > 0] or [0])))},
       "reference_found": sorted(ref_nodes.values()), "reference_missing": missing,
       "national_found": sorted(nat_v2.values())}
variants = [("v1_N", set(hosp_nodes), comm, False), ("v1_R", set(ref_nodes), comm, False),
            ("v2_N", set(hosp_v2), comm_v2, True), ("v2_R", set(ref_v2), comm_v2, True), ("v2_R2", set(nat_v2), comm_v2, True),
            ("v3_N", set(hosp_v2), comm_v2, True), ("v3_R", set(ref_v2), comm_v2, True), ("v3_R2", set(nat_v2), comm_v2, True)]
for name, targets, cm, clean in variants:
    if not targets:
        out[name] = "no target hospitals"
        continue
    summary, rows = measure(targets, cm, clean, segments_v3 if name.startswith("v3") else segments)
    out[name] = {"summary": summary, "segments": rows}
(out_dir / "e5_metric.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: (v["summary"] if isinstance(v, dict) and "summary" in v else v) for k, v in out.items() if k != "graph"} | {"graph": {k: v for k, v in out["graph"].items() if k != "hospitals"}}, ensure_ascii=False, indent=1))
