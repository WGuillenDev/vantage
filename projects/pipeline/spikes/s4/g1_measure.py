"""G1 measurement (spike, not P5): one-at-a-time closure of test segments on the real network.

Spike-only assumptions: unclassified = 30 km/h (S4 regional OSM median, 20 tags);
hospitals = amenity=hospital features whose name starts with "Hospital".
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import osmnx as ox

from pipeline import road_graph as rg

work, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
F = ox.features_from_xml(work / "features.osm").reset_index()
hosp = F[(F.get("amenity") == "hospital") & F["name"].fillna("").str.startswith("Hospital")]
allow = out_dir / "allowlist_spike.txt"
allow.write_text("\n".join(f"{r.element}/{r.id}" for r in hosp.itertuples()), encoding="utf-8")
settings = rg.Settings(bbox=rg.SETTINGS.bbox, allowlist=allow)
rg.SPEED_MODEL_KMH.setdefault("unclassified", 30)
speeds = dict(rg.SPEED_MODEL_KMH)
graph = rg.build(work / "roads.osm", work / "features.osm", settings)

G = nx.MultiDiGraph()
for e in graph["edges"]:
    G.add_edge(e["from"], e["to"], key=e["id"], t=e["time_s"])
    if not e["oneway"]:
        G.add_edge(e["to"], e["from"], key=e["id"], t=e["time_s"])
hnode = {h["node"] for h in graph["hospitals"]}
comm = graph["communities"]


def times(g):
    d = nx.multi_source_dijkstra_path_length(g.reverse(copy=False), hnode & set(g.nodes), weight="t")
    return {c["id"]: d.get(c["node"]) for c in comm}


base = times(G)

# test segments: Ruta 32 and the numbered routes that touch it, split at junctions (undirected degree != 2)
by_id = {e["id"]: e for e in graph["edges"]}
r32_nodes = {n for e in graph["edges"] if e["road"] == "Ruta 32" for n in (e["from"], e["to"])}
roads = {"Ruta 32"} | {e["road"] for e in graph["edges"]
                       if e["road"] and e["road"].startswith("Ruta ") and ({e["from"], e["to"]} & r32_nodes)}
U = nx.Graph()
for e in graph["edges"]:
    U.add_edge(e["from"], e["to"])
junction = {n for n in U if U.degree(n) != 2}
adj = defaultdict(list)
for e in graph["edges"]:
    if e["road"] in roads:
        adj[e["from"]].append(e["id"])
        adj[e["to"]].append(e["id"])
seen, segments = set(), []
for e in graph["edges"]:
    if e["road"] not in roads or e["id"] in seen:
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
                stack += [x for x in adj[n] if by_id[x]["road"] == e["road"] and x not in seen]
    segments.append((e["road"], seg))

results = []
finite = []
for road, seg in segments:
    g2 = G.copy()
    g2.remove_edges_from([(by_id[x]["from"], by_id[x]["to"], x) for x in seg] + [(by_id[x]["to"], by_id[x]["from"], x) for x in seg if not by_id[x]["oneway"]])
    after = times(g2)
    aff = [c for c, t0 in base.items() if t0 is not None and (after[c] is None or after[c] - t0 > 0)]
    iso = [c for c in aff if after[c] is None]
    ext = [after[c] - base[c] for c in aff if after[c] is not None]
    finite += ext
    results.append({"road": road, "edges": len(seg), "length_km": round(sum(by_id[x]["length_m"] for x in seg) / 1000, 1),
                    "affected": len(aff), "isolated": len(iso), "extra_time_s": max(ext) if ext else (None if aff else 0)})

summary = {
    "graph": {"nodes": len(graph["nodes"]), "edges": len(graph["edges"]), "hospitals": len(graph["hospitals"]), "communities": len(comm),
              "no_path_baseline": sum(1 for t in base.values() if t is None)},
    "speeds_kmh": speeds, "roads_tested": sorted(roads), "segments": len(segments),
    "criticality_gt0": 0, "note_criticality": "population is null everywhere, so criticality = 0 for all",
    "with_affected": sum(1 for r in results if r["affected"]),
    "with_extra_time_gt0": sum(1 for r in results if (r["extra_time_s"] or 0) > 0),
    "with_isolated": sum(1 for r in results if r["isolated"]),
    "tied_all_zero": sum(1 for r in results if not r["affected"]),
    "by_road": {rd: dict(Counter("affected" if r["affected"] else "zero" for r in results if r["road"] == rd)) for rd in sorted(roads)},
    "ruta32_top": sorted([r for r in results if r["road"] == "Ruta 32"], key=lambda r: (-r["isolated"], -(r["extra_time_s"] or 0)))[:8],
}
(out_dir / "g1_measure.json").write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
