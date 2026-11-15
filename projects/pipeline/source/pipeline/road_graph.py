"""Road graph stage (P3): the zone's OSM roads, referral hospitals and named places -> graph.json."""

import argparse
import json
import logging
import math
import re
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
from osmnx._errors import InsufficientResponseError  # shortcut: osmnx 2.1 has no public errors module; recheck on upgrade
from shapely.geometry import LineString

from .area_config import PIPELINE_DIR, ConfigError, Zone, load_zone

log = logging.getLogger(__name__)

WORK_DIR = PIPELINE_DIR / "work"
ROAD_CLASSES = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified")
PLACE_TYPES = {"city", "town", "village", "hamlet"}
MAX_EDGE_M = 1000
MAX_SNAP_M = 3000
MAX_GRAPH_BYTES = 3 * 1024 * 1024
SIMPLIFY_TOLERANCE_DEG = 0.0001  # ~11 m at Costa Rica's latitude
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "vantage-pipeline"  # generic on purpose: no name, email or machine data
OSM_ID = re.compile(r"(node|way|relation)/([0-9]+)")


class RoadGraphError(Exception):
  pass


def round_half_up(x: float) -> int:
  return math.floor(x + 0.5)


def _first(value) -> str | None:
  """First value of a multi-valued OSM tag (a list from merged ways, or `a;b`)."""
  if isinstance(value, list):
    value = value[0]
  if not isinstance(value, str):
    return None
  return value.split(";")[0].strip() or None


def _road_class(data: dict) -> str:
  return _first(data["highway"]).removesuffix("_link")


def _road_name(data: dict) -> str | None:
  ref = _first(data.get("ref"))
  if ref:
    return f"Ruta {ref}"
  name = data.get("name")
  name = name[0] if isinstance(name, list) else name
  return name if isinstance(name, str) and name else None


def _check_speeds(pieces: list, speeds: dict[str, float]) -> None:
  for cls in sorted({_road_class(data) for _, _, _, data in pieces}):
    if cls not in speeds:
      raise RoadGraphError(f"No speed for road class '{cls}': add it to speed_model_kmh in the zone config")


def _metres(a: tuple, b: tuple) -> float:
  return float(ox.distance.great_circle(a[1], a[0], b[1], b[0]))


def _split(coords: list[tuple], max_edge_m: float) -> tuple[list[list[tuple]], float]:
  """Cut a polyline into equal-length parts no longer than max_edge_m; returns the parts and their length."""
  lengths = [_metres(a, b) for a, b in pairwise(coords)]
  total = sum(lengths)
  count = max(1, math.ceil(total / max_edge_m))
  step = total / count
  parts, current, walked, k = [], [coords[0]], 0.0, 1
  for (a, b), length in zip(pairwise(coords), lengths):
    while k < count and walked + length >= k * step:
      t = (k * step - walked) / length if length else 0.0
      point = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
      current.append(point)
      parts.append(current)
      current, k = [point], k + 1
    current.append(b)
    walked += length
  parts.append(current)
  return parts, step


def _point(xy: tuple) -> list[float]:
  return [round(xy[0], 5), round(xy[1], 5)]


def _geometry(part: list[tuple], start: list[float], end: list[float]) -> list[list[float]]:
  simple = LineString(part).simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=False).coords
  points = [start] + [_point(xy) for xy in list(simple)[1:-1]] + [end]
  deduped = [p for i, p in enumerate(points) if i == 0 or p != points[i - 1]]
  return deduped if len(deduped) >= 2 else [start, end]


def _smallest_way_id(data: dict) -> int:
  osmid = data["osmid"]
  return min(osmid) if isinstance(osmid, list) else osmid


def _coords(graph, u: int, v: int, data: dict) -> list[tuple]:
  start = (graph.nodes[u]["x"], graph.nodes[u]["y"])
  end = (graph.nodes[v]["x"], graph.nodes[v]["y"])
  inner = list(data["geometry"].coords)[1:-1] if "geometry" in data else []
  return [start, *inner, end]


def _load_network(roads_osm: Path, bbox: tuple) -> list:
  """Kept road pieces as (u, v, key, data): largest weakly connected component, simplified, one per piece."""
  graph = ox.graph_from_xml(roads_osm, simplify=False, retain_all=True)
  graph = ox.truncate.truncate_graph_bbox(graph, bbox)
  if len(graph) == 0:
    raise RoadGraphError(f"No roads of the extract lie inside the bbox {list(bbox)}")
  graph = ox.truncate.largest_component(graph, strongly=False)
  graph = ox.simplify_graph(graph)
  pieces = [
    (u, v, k, {**data, "_coords": _coords(graph, u, v, data)})
    for u, v, k, data in graph.edges(keys=True, data=True)
    # A two-way road is stored in both directions; keep the copy that starts at the lower OSM id.
    if u != v and (data["oneway"] or u < v)
  ]
  return sorted(pieces, key=lambda p: (p[0], p[1], _smallest_way_id(p[3])))


def _node_number(node_id: str) -> int:
  return int(node_id[1:])


def _largest_strong_component(nodes: list[dict], edges: list[dict]) -> list[dict]:
  """Nodes of the largest strongly connected component; a tie goes to the one holding the lowest node id."""
  graph = nx.DiGraph()
  graph.add_nodes_from(n["id"] for n in nodes)
  for e in edges:
    graph.add_edge(e["from"], e["to"])
    if not e["oneway"]:
      graph.add_edge(e["to"], e["from"])
  best = max(nx.strongly_connected_components(graph), key=lambda c: (len(c), -min(map(_node_number, c))))
  return [n for n in nodes if n["id"] in best]


class _Snapper:
  def __init__(self, nodes: list[dict]):
    self.ids = [n["id"] for n in nodes]
    self.lons = np.array([n["lon"] for n in nodes])
    self.lats = np.array([n["lat"] for n in nodes])

  def nearest(self, lon: float, lat: float) -> tuple[str, float]:
    distances = ox.distance.great_circle(lat, lon, self.lats, self.lons)
    i = int(np.argmin(distances))
    return self.ids[i], float(distances[i])


def _osm_key(entry: str) -> tuple[int, str]:
  match = OSM_ID.fullmatch(entry)
  if match is None:
    raise RoadGraphError(f"Referral hospital id {entry!r} must look like 'way/123', 'node/123' or 'relation/123'")
  return int(match.group(2)), match.group(1)


def _build_edges(pieces: list, speeds: dict[str, float]) -> tuple[list[dict], list[dict]]:
  osm_nodes = sorted({end for u, v, _, _ in pieces for end in (u, v)})
  node_ids = {osm: f"n{i}" for i, osm in enumerate(osm_nodes, start=1)}
  first_coords = {}
  for u, v, _, data in pieces:
    first_coords.setdefault(u, data["_coords"][0])
    first_coords.setdefault(v, data["_coords"][-1])
  nodes = [{"id": node_ids[osm], "lon": _point(first_coords[osm])[0], "lat": _point(first_coords[osm])[1]} for osm in osm_nodes]
  position = {node["id"]: [node["lon"], node["lat"]] for node in nodes}

  edges = []
  for u, v, _, data in pieces:
    parts, length = _split(data["_coords"], MAX_EDGE_M)
    length_m = round_half_up(length)
    time_s = round_half_up(length_m / (speeds[_road_class(data)] / 3.6))
    start = node_ids[u]
    for i, part in enumerate(parts):
      if i == len(parts) - 1:
        end = node_ids[v]
      else:
        end = f"n{len(nodes) + 1}"
        nodes.append({"id": end, "lon": _point(part[-1])[0], "lat": _point(part[-1])[1]})
        position[end] = [nodes[-1]["lon"], nodes[-1]["lat"]]
      edges.append({
        "id": f"e{len(edges) + 1}",
        "from": start,
        "to": end,
        "length_m": length_m,
        "time_s": time_s,
        "road": _road_name(data),
        "oneway": bool(data["oneway"]),
        "candidate_id": None,
        "geometry": _geometry(part, position[start], position[end]),
      })
      start = end
  return nodes, edges


def _hospitals(features, referral: tuple[str, ...], snapper: _Snapper) -> list[dict]:
  hospitals = []
  for entry in sorted(referral, key=_osm_key):
    number, kind = _osm_key(entry)
    if (kind, number) not in features.index:
      raise RoadGraphError(f"Referral hospital {entry} was not found in the OSM extract")
    row = features.loc[(kind, number)]
    name = row.get("name")
    if not isinstance(name, str) or not name:
      raise RoadGraphError(f"Referral hospital {entry} has no OSM name")
    point = row["geometry"].centroid
    node, distance = snapper.nearest(point.x, point.y)
    if distance > MAX_SNAP_M:
      raise RoadGraphError(f"Referral hospital {entry} ({name}) is {round_half_up(distance)} m from the road network (limit {MAX_SNAP_M} m)")
    hospitals.append({"id": f"h{len(hospitals) + 1}", "name": name, "node": node})
  return hospitals


def _communities(features, snapper: _Snapper) -> tuple[list[dict], list[dict]]:
  communities, originals = [], []
  places = features[features["place"].isin(PLACE_TYPES)] if "place" in features else features.iloc[0:0]
  for (kind, number), row in sorted(places.iterrows(), key=lambda item: item[0][1]):
    name = row.get("name")
    if kind != "node" or not isinstance(name, str) or not name:
      continue
    lon, lat = row["geometry"].x, row["geometry"].y
    node, distance = snapper.nearest(lon, lat)
    if distance > MAX_SNAP_M:
      log.warning("Dropped community %r: nearest node of the road network is %d m away (limit %d m)", name, round_half_up(distance), MAX_SNAP_M)
      continue
    cid = f"c{len(communities) + 1}"
    communities.append({"id": cid, "name": name, "node": node, "population": None})
    originals.append({"id": cid, "osm_id": f"{kind}/{number}", "lon": lon, "lat": lat})
  return communities, originals


def build(roads_osm: Path, features_osm: Path, zone: Zone) -> tuple[dict, list[dict]]:
  """The zone's graph.json content and the original coordinates of its communities (work/communities.json)."""
  pieces = _load_network(roads_osm, zone.bbox)
  _check_speeds(pieces, zone.speed_model_kmh)
  nodes, edges = _build_edges(pieces, zone.speed_model_kmh)
  snapper = _Snapper(_largest_strong_component(nodes, edges))
  try:
    features = ox.features_from_xml(features_osm)
  except InsufficientResponseError:
    # The zone config always lists at least one referral hospital, so an extract with no features misses it.
    raise RoadGraphError(f"Referral hospital {min(zone.referral_hospitals, key=_osm_key)} was not found in the OSM extract") from None
  hospitals =_hospitals(features, zone.referral_hospitals, snapper)
  communities, originals = _communities(features, snapper)
  graph = {"schema_version": "0.3", "nodes": nodes, "edges": edges, "hospitals": hospitals, "communities": communities}
  return graph, originals


def _write(path: Path, data: bytes) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_bytes(data)


def run(zone: Zone, work_dir: Path) -> Path:
  """Builds the zone's graph from `work_dir/osm`; writes nothing unless every check passed."""
  osm_dir = work_dir / "osm"
  roads, features = osm_dir / "roads.osm", osm_dir / "features.osm"
  if not (roads.is_file() and features.is_file()):
    raise RoadGraphError(f"OSM extract not found in {osm_dir}; run `make osm AREA={zone.id}` to download it")
  graph, originals = build(roads, features, zone)
  data = json.dumps(graph, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
  if len(data) > MAX_GRAPH_BYTES:
    raise RoadGraphError(f"graph.json would be {len(data)} bytes, over the {MAX_GRAPH_BYTES} bytes limit")
  _write(work_dir / "communities.json", (json.dumps(originals, indent=2) + "\n").encode("utf-8"))
  _write(zone.output_dir / "graph.json", data)
  return zone.output_dir / "graph.json"


def download(zone: Zone, osm_dir: Path) -> None:
  w, s, e, n = zone.bbox
  area = f"({s},{w},{n},{e})"
  classes = "|".join(ROAD_CLASSES)
  places = "|".join(sorted(PLACE_TYPES))
  queries = {
    "roads.osm": f'[out:xml][timeout:600];way["highway"~"^({classes})(_link)?$"]{area};(._;>;);out body;',
    "features.osm": (
      f'[out:xml][timeout:600];(nwr["amenity"="hospital"]{area};'
      f'node["place"~"^({places})$"]["name"]{area};);(._;>;);out body;'
    ),
  }
  osm_dir.mkdir(parents=True, exist_ok=True)
  for name, query in queries.items():
    log.info("Downloading %s from Overpass", name)
    request = urllib.request.Request(
      OVERPASS_URL,
      data=urllib.parse.urlencode({"data": query}).encode(),
      headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=900) as response:
      (osm_dir / name).write_bytes(response.read())
  # pipeline-run writes this date into the OSM line of meta.json -> attributions.
  (osm_dir / "extract_date.txt").write_text(datetime.now(UTC).date().isoformat() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="road-graph", description="Build a zone's graph.json from OpenStreetMap data.")
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  parser.add_argument("--download", action="store_true", help="only fetch the OSM extract from Overpass into work/<id>/osm")
  args = parser.parse_args(argv)
  logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
  try:
    zone = load_zone(args.area)
    work_dir = WORK_DIR / zone.id
    if args.download:
      download(zone, work_dir / "osm")
      log.info("Saved the OSM extract in %s", work_dir / "osm")
      return
    path = run(zone, work_dir)
  except (ConfigError, RoadGraphError) as exc:
    raise SystemExit(f"road-graph: {exc}") from None
  log.info("Wrote %s", path)
