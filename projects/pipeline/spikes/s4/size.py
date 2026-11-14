import json, sys
from pathlib import Path
import osmnx as ox
DL = Path(sys.argv[1]); bbox = tuple(map(float, sys.argv[2:6]))
ox.settings.cache_folder = str(DL / "cache"); ox.settings.use_cache = True
MAJOR = '["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified)(_link)?$"]'
G = ox.graph_from_bbox(bbox, custom_filter=MAJOR, simplify=True, retain_all=True, truncate_by_edge=True)
U = ox.convert.to_undirected(G)
ids = {n: f"n{i}" for i, n in enumerate(U.nodes, 1)}
nodes = [{"id": ids[n], "lon": round(d["x"], 5), "lat": round(d["y"], 5)} for n, d in U.nodes(data=True)]
edges = []
for i, (u, v, d) in enumerate(U.edges(data=True), 1):
    geom = [[round(x, 5), round(y, 5)] for x, y in d["geometry"].coords] if "geometry" in d else [[round(U.nodes[u]["x"],5), round(U.nodes[u]["y"],5)], [round(U.nodes[v]["x"],5), round(U.nodes[v]["y"],5)]]
    edges.append({"id": f"e{i}", "from": ids[u], "to": ids[v], "length_m": round(d["length"]), "time_s": 0, "road": None, "oneway": bool(d.get("oneway")), "candidate_id": None, "geometry": geom})
s = json.dumps({"schema_version": "0.1", "nodes": nodes, "edges": edges, "hospitals": [], "communities": []}, separators=(",", ":"))
pts = sum(len(e["geometry"]) for e in edges)
geoms = [ox.utils_geo.LineString(e["geometry"]) for e in edges]
s2 = json.dumps({"nodes": nodes, "edges": [{**e, "geometry": [list(c) for c in g.simplify(0.0001).coords]} for e, g in zip(edges, geoms)]}, separators=(",", ":"))
print(f"nodes={len(nodes)} edges={len(edges)} geom_points={pts} size_kb={len(s)//1024} size_kb_simplified_10m={len(s2)//1024}")
