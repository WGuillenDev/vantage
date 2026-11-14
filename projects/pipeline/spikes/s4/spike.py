"""S4 spike: OSM road graph + impact metric. Exploration only, not production code."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox

DL = Path(sys.argv[1])
AREA = sys.argv[2]
BBOXES = {  # (west, south, east, north)
    "corridor": (-84.10, 9.90, -83.72, 10.25),
    "regional": (-84.30, 9.80, -83.40, 10.45),
}
MAJOR = '["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified)(_link)?$"]'
ox.settings.cache_folder = str(DL / "cache")
ox.settings.use_cache = True
ox.settings.requests_timeout = 300

bbox = BBOXES[AREA]
out = {"area": AREA, "bbox": bbox}

G = ox.graph_from_bbox(bbox, custom_filter=MAJOR, simplify=True, retain_all=True, truncate_by_edge=True)
out["nodes"], out["edges_directed"] = G.number_of_nodes(), G.number_of_edges()
U = ox.convert.to_undirected(G)
out["edges_undirected"] = U.number_of_edges()
comps = sorted((len(c) for c in nx.connected_components(U)), reverse=True)
out["components"] = len(comps)
out["largest_components"] = comps[:5]
out["share_in_largest"] = round(comps[0] / G.number_of_nodes(), 4)
out["strong_components_directed"] = nx.number_strongly_connected_components(G)


def first(v):
    return v[0] if isinstance(v, list) else v


cls = Counter(first(d["highway"]) for _, _, d in U.edges(data=True))
out["edges_by_class"] = dict(cls.most_common())
out["oneway_edges"] = sum(1 for _, _, d in G.edges(data=True) if d.get("oneway"))

# maxspeed tags per class (proposal source for speed_model_kmh)
speeds = defaultdict(list)
for _, _, d in U.edges(data=True):
    ms = first(d.get("maxspeed"))
    if ms and re.fullmatch(r"\d+", str(ms)):
        speeds[first(d["highway"]).replace("_link", "")].append(int(ms))
out["maxspeed_tags"] = {
    k: {"n_tagged": len(v), "n_edges": sum(c for h, c in cls.items() if h.replace("_link", "") == k),
        "median": float(np.median(v)), "mean": round(float(np.mean(v)), 1), "values": dict(Counter(v).most_common(5))}
    for k, v in sorted(speeds.items())
}

# keep largest component for routing
Gm = G.subgraph(max(nx.weakly_connected_components(G), key=len)).copy()
nid = np.array(list(Gm.nodes))
xy = np.array([[Gm.nodes[n]["x"], Gm.nodes[n]["y"]] for n in nid])


def snap(lon, lat):
    dx = (xy[:, 0] - lon) * np.cos(np.radians(lat)) * 111320
    dy = (xy[:, 1] - lat) * 110540
    d = np.hypot(dx, dy)
    i = int(np.argmin(d))
    return nid[i], float(d[i])


def features(tags):
    f = ox.features_from_bbox(bbox, tags)
    f = f.reset_index()
    f["pt"] = f.geometry.representative_point()
    return f


hosp_tags = {"amenity": ["hospital", "clinic", "doctors"], "healthcare": ["hospital", "clinic", "centre"]}
H = features(hosp_tags)
hlist = []
for _, r in H.iterrows():
    tag = "amenity=" + str(r.get("amenity")) if isinstance(r.get("amenity"), str) else "healthcare=" + str(r.get("healthcare"))
    node, dist = snap(r["pt"].x, r["pt"].y)
    hlist.append({"name": r.get("name") if isinstance(r.get("name"), str) else None, "tag": tag,
                  "osm": f"{r['element']}/{r['id']}", "lon": round(r["pt"].x, 5), "lat": round(r["pt"].y, 5),
                  "snap_m": round(dist)})
out["health_by_tag"] = dict(Counter(h["tag"] for h in hlist))
out["hospitals_amenity_hospital"] = sorted([h for h in hlist if h["tag"] == "amenity=hospital"], key=lambda h: h["lon"])

P = features({"place": ["city", "town", "village", "hamlet", "suburb", "neighbourhood", "locality", "isolated_dwelling"]})
P = P[P["element"] == "node"]
out["places_by_type"] = dict(Counter(P["place"]).most_common())
out["places_with_population_tag"] = int(P["population"].notna().sum()) if "population" in P else 0
comm = []
for _, r in P[P["place"].isin(["city", "town", "village", "hamlet"])].iterrows():
    node, dist = snap(r["pt"].x, r["pt"].y)
    comm.append({"name": r.get("name"), "place": r["place"], "node": node, "snap_m": round(dist),
                 "lon": r["pt"].x, "lat": r["pt"].y})
out["communities_city_town_village_hamlet"] = len(comm)
out["community_snap_m_p50_p90_max"] = [int(np.percentile([c["snap_m"] for c in comm], q)) for q in (50, 90, 100)]

# ---- impact metric test case ----
SPEED = {"motorway": 80, "trunk": 60, "primary": 60, "secondary": 50, "tertiary": 40, "unclassified": 30}  # spike proposal
for u, v, k, d in Gm.edges(keys=True, data=True):
    c = first(d["highway"]).replace("_link", "")
    d["time_s"] = d["length"] / (SPEED.get(c, 30) / 3.6)

hosp_nodes = {}
for h in out["hospitals_amenity_hospital"]:
    n, dist = snap(h["lon"], h["lat"])
    hosp_nodes.setdefault(n, h["name"])


def nearest(G_):
    R = G_.reverse(copy=False)
    dist, paths = nx.multi_source_dijkstra(R, set(hosp_nodes) & set(G_.nodes), weight="time_s")
    return {c["name"]: (dist.get(c["node"]), hosp_nodes.get(paths[c["node"]][0]) if c["node"] in paths else None) for c in comm}


base = nearest(Gm)
# cut: Ruta 32 edges between the Zurquí tunnel and Quebrada González (mid-park)
CUT_W, CUT_E = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (-83.98, -83.92)
cut = [(u, v, k) for u, v, k, d in Gm.edges(keys=True, data=True)
       if "32" in [r.strip() for r in str(first(d.get("ref")) or "").split(";")] and CUT_W <= (Gm.nodes[u]["x"] + Gm.nodes[v]["x"]) / 2 <= CUT_E]
out["cut_window_lon"] = [CUT_W, CUT_E]
out["cut_edges"] = len(cut)
out["cut_length_m"] = round(sum(Gm.edges[e]["length"] for e in cut) / 2)
G2 = Gm.copy()
G2.remove_edges_from(cut)
after = nearest(G2)
affected = []
for name, (t0, h0) in base.items():
    t1, h1 = after[name]
    if t0 is None:
        continue
    if t1 is None:
        affected.append({"community": name, "base_min": round(t0 / 60, 1), "base_h": h0, "after_min": None, "extra_min": None, "isolated": True, "lon": round(next(c["lon"] for c in comm if c["name"] == name), 4), "lat": round(next(c["lat"] for c in comm if c["name"] == name), 4)})
    elif t1 - t0 > 0.5:
        affected.append({"community": name, "base_min": round(t0 / 60, 1), "base_h": h0, "after_min": round(t1 / 60, 1),
                         "after_h": h1, "extra_min": round((t1 - t0) / 60, 1)})
out["no_path_baseline"] = sum(1 for t, _ in base.values() if t is None)
out["affected"] = sorted(affected, key=lambda a: -(a["extra_min"] or 1e9))
out["affected_count"] = len(affected)

# OD check: Calderon Guardia (San Jose) -> Hospital Guapiles
od = {}
for h in out["hospitals_amenity_hospital"]:
    if h["name"] and ("Guardia" in h["name"] or "Guápiles" in h["name"]):
        od[h["name"]] = snap(h["lon"], h["lat"])[0]
if len(od) == 2:
    a, b = list(od.values())
    for label, g in (("od_base_min", Gm), ("od_cut_min", G2)):
        try:
            out[label] = round(nx.shortest_path_length(g, a, b, weight="time_s") / 60, 1)
        except nx.NetworkXNoPath:
            out[label] = None
out["hospital_named_hospital"] = sum(1 for h in out["hospitals_amenity_hospital"] if (h["name"] or "").startswith("Hospital"))
SUFFIX = f"_{CUT_W}_{CUT_E}" if len(sys.argv) > 4 else ""
json.dump(out, open(DL / f"s4_{AREA}{SUFFIX}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

# plot
import matplotlib
matplotlib.use("Agg")
fig, ax = ox.plot_graph(ox.convert.to_undirected(Gm), show=False, close=False, node_size=0, edge_linewidth=0.4,
                        edge_color="#999", bgcolor="white", figsize=(10, 8))
for u, v, k in cut:
    ax.plot([Gm.nodes[u]["x"], Gm.nodes[v]["x"]], [Gm.nodes[u]["y"], Gm.nodes[v]["y"]], color="red", lw=3)
for h in out["hospitals_amenity_hospital"]:
    ax.plot(h["lon"], h["lat"], "P", color="blue", ms=8)
for a in affected:
    c = next(c for c in comm if c["name"] == a["community"])
    ax.plot(c["lon"], c["lat"], "o", color="orange", ms=5)
ax.set_title(f"S4 {AREA}: cut (red), hospitals (blue), affected communities (orange)")
fig.savefig(DL / f"s4_{AREA}{SUFFIX}.png", dpi=110)
print(json.dumps({k: v for k, v in out.items() if k not in ("hospitals_amenity_hospital", "affected")}, ensure_ascii=False, default=str))
