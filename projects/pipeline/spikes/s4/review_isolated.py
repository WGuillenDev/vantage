"""S4 hand review: the 18 communities isolated by the Guapiles-Siquirres cut (regional net to -83.40).

Rebuilds the network up to Limon with road_graph.build (edges <= 1 km), same hospital set as the
S4 spike (every amenity=hospital), same cut (Ruta 32 edges with midpoint lon in [-83.70, -83.55]),
and reports for each of the 18 whether it is still isolated, and why.
Spike-only assumption: unclassified = 30 km/h.
"""
import json
import sys
from pathlib import Path

import networkx as nx
import osmnx as ox

from pipeline import road_graph as rg

work, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
NAMES = ["La Isleta", "Las Colinas", "Parismina", "La Argentina", "Mercedes", "Pocora", "Portón de Iberia",
         "Codela", "Altos de Germania", "Milano", "Germania", "Herediana", "Bellavista", "El Cairo",
         "Louisiana", "El Peje", "3 Millas", "Trinidad"]
CUT = (-83.70, -83.55)

F = ox.features_from_xml(work / "features.osm").reset_index()
hosp = F[(F.get("amenity") == "hospital") & F["name"].notna()]
allow = out_dir / "allowlist_all_hospitals.txt"
allow.write_text("\n".join(f"{r.element}/{r.id}" for r in hosp.itertuples()), encoding="utf-8")
settings = rg.Settings(bbox=rg.SETTINGS.bbox, allowlist=allow)
rg.SPEED_MODEL_KMH.setdefault("unclassified", 30)
graph = rg.build(work / "roads.osm", work / "features.osm", settings)

node_xy = {n["id"]: (n["lon"], n["lat"]) for n in graph["nodes"]}
G = nx.MultiDiGraph()
for e in graph["edges"]:
    G.add_edge(e["from"], e["to"], key=e["id"], t=e["time_s"])
    if not e["oneway"]:
        G.add_edge(e["to"], e["from"], key=e["id"], t=e["time_s"])
hosp_node = {h["node"]: h["name"] for h in graph["hospitals"]}
cut = [e for e in graph["edges"] if e["road"] == "Ruta 32"
       and CUT[0] <= (node_xy[e["from"]][0] + node_xy[e["to"]][0]) / 2 <= CUT[1]]
G2 = G.copy()
for e in cut:
    G2.remove_edges_from([(e["from"], e["to"], e["id"]), (e["to"], e["from"], e["id"])])


def nearest(g):
    dist, paths = nx.multi_source_dijkstra(g.reverse(copy=False), set(hosp_node), weight="t")
    return dist, paths


d0, p0 = nearest(G)
d1, p1 = nearest(G2)
U2 = G2.to_undirected(as_view=True)
rows = []
for name in NAMES:
    c = next((c for c in graph["communities"] if c["name"] == name), None)
    if c is None:
        rows.append({"community": name, "status": "not in graph (dropped by MAX_SNAP_M or not a city/town/village/hamlet)"})
        continue
    n = c["node"]
    comp = nx.node_connected_component(U2, n)
    row = {"community": name, "base_min": round(d0[n] / 60, 1) if n in d0 else None,
           "base_hospital": hosp_node.get(p0[n][0]) if n in p0 else None,
           "after_min": round(d1[n] / 60, 1) if n in d1 else None,
           "after_hospital": hosp_node.get(p1[n][0]) if n in p1 else None,
           "isolated": n not in d1, "component_nodes_after_cut": len(comp),
           "hospitals_in_component": sorted({hosp_node[h] for h in comp if h in hosp_node})}
    rows.append(row)
summary = {"cut_edges": len(cut), "cut_length_km": round(sum(e["length_m"] for e in cut) / 1000, 1),
           "hospitals": len(graph["hospitals"]), "still_isolated": sum(1 for r in rows if r.get("isolated")),
           "rows": rows}
(out_dir / "review_isolated.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
