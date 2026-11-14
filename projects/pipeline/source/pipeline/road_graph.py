"""Road graph stage (P3): OSM roads, allowlisted hospitals and named places -> graph.json."""

import argparse
import json
import logging
import math
import statistics
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

import numpy as np
import osmnx as ox
from shapely.geometry import LineString

log = logging.getLogger(__name__)

PIPELINE = Path(__file__).resolve().parents[2]
WORK = PIPELINE / "work"
OSM_DIR = WORK / "osm"
OUTPUT = PIPELINE / "output"

ROAD_CLASSES = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified")
PLACE_TYPES = {"city", "town", "village", "hamlet"}
MAX_GRAPH_BYTES = 3 * 1024 * 1024
SIMPLIFY_TOLERANCE_DEG = 0.0001  # ~11 m at Costa Rica's latitude
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class RoadGraphError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    bbox: tuple[float, float, float, float]  # west, south, east, north
    allowlist: Path
    min_tagged: int = 20
    fallback_speeds_kmh: dict[str, float] = field(default_factory=dict)
    max_edge_m: float = 1000
    max_snap_m: float = 3000


SETTINGS = Settings(
    bbox=(-84.30, 9.80, -82.95, 10.45),
    allowlist=PIPELINE / "settings" / "hospital_allowlist.txt",
    # shortcut: no fallback speeds until Ian sets them with a cited source; a class under MIN_TAGGED stops the run.
    fallback_speeds_kmh={},
)


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


def _maxspeed(data: dict) -> float | None:
    try:
        return float(_first(data.get("maxspeed")))
    except (TypeError, ValueError):
        return None


def _road_name(data: dict) -> str | None:
    ref = _first(data.get("ref"))
    if ref:
        return f"Ruta {ref}"
    name = data.get("name")
    name = name[0] if isinstance(name, list) else name
    return name if isinstance(name, str) and name else None


def _speed_table(pieces: list, settings: Settings) -> dict[str, float]:
    tagged: dict[str, list[float]] = defaultdict(list)
    classes = set()
    for _, _, _, data in pieces:
        cls = _road_class(data)
        classes.add(cls)
        speed = _maxspeed(data)
        if speed is not None:
            tagged[cls].append(speed)
    table = {}
    for cls in sorted(classes):
        if len(tagged[cls]) >= settings.min_tagged:
            median = statistics.median(tagged[cls])
            table[cls] = int(median) if median.is_integer() else median
        elif cls in settings.fallback_speeds_kmh:
            table[cls] = settings.fallback_speeds_kmh[cls]
        else:
            raise RoadGraphError(
                f"No speed for road class '{cls}': {len(tagged[cls])} edges tag maxspeed "
                f"(at least {settings.min_tagged} needed) and no fallback speed is configured"
            )
    return table


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


def _load_network(roads_osm: Path, bbox: tuple) -> list:
    """Kept road pieces as (u, v, key, data): largest weakly connected component, simplified, one per piece."""
    graph = ox.graph_from_xml(roads_osm, simplify=False, retain_all=True)
    graph = ox.truncate.truncate_graph_bbox(graph, bbox)
    graph = ox.truncate.largest_component(graph, strongly=False)
    graph = ox.simplify_graph(graph)
    pieces = [
        (u, v, k, {**data, "_coords": _coords(graph, u, v, data)})
        for u, v, k, data in graph.edges(keys=True, data=True)
        # A two-way road is stored in both directions; keep the copy that starts at the lower OSM id.
        if u != v and (data["oneway"] or u < v)
    ]
    return sorted(pieces, key=lambda p: p[:3])


def _coords(graph, u: int, v: int, data: dict) -> list[tuple]:
    start = (graph.nodes[u]["x"], graph.nodes[u]["y"])
    end = (graph.nodes[v]["x"], graph.nodes[v]["y"])
    inner = list(data["geometry"].coords)[1:-1] if "geometry" in data else []
    return [start, *inner, end]


def _nearest(lon: float, lat: float, node_ids: list[str], lons: np.ndarray, lats: np.ndarray) -> tuple[str, float]:
    distances = ox.distance.great_circle(lat, lon, lats, lons)
    i = int(np.argmin(distances))
    return node_ids[i], float(distances[i])


def _read_allowlist(path: Path) -> list[str]:
    lines = (line.split("#")[0].strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line]


def _osm_key(entry: str) -> tuple[int, str]:
    kind, _, number = entry.partition("/")
    return int(number), kind


def build(roads_osm: Path, features_osm: Path, settings: Settings) -> tuple[dict, dict[str, float]]:
    w, s, e, n = settings.bbox
    pieces = _load_network(roads_osm, (w, s, e, n))
    speeds = _speed_table(pieces, settings)

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
        parts, length = _split(data["_coords"], settings.max_edge_m)
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

    ids = [node["id"] for node in nodes]
    lons = np.array([node["lon"] for node in nodes])
    lats = np.array([node["lat"] for node in nodes])
    features = ox.features_from_xml(features_osm)

    hospitals = []
    for entry in sorted(set(_read_allowlist(settings.allowlist)), key=_osm_key):
        number, kind = _osm_key(entry)
        if (kind, number) not in features.index:
            raise RoadGraphError(f"Hospital {entry} from the allowlist was not found in the network area")
        row = features.loc[(kind, number)]
        name = row.get("name")
        if not isinstance(name, str) or not name:
            raise RoadGraphError(f"Hospital {entry} from the allowlist has no OSM name")
        point = row["geometry"].centroid
        node, _ = _nearest(point.x, point.y, ids, lons, lats)
        hospitals.append({"id": f"h{len(hospitals) + 1}", "name": name, "node": node})

    communities = []
    places = features[features.get("place").isin(PLACE_TYPES)] if "place" in features else features.iloc[0:0]
    for (kind, number), row in sorted(places.iterrows(), key=lambda item: item[0][1]):
        name = row.get("name")
        if kind != "node" or not isinstance(name, str) or not name:
            continue
        node, distance = _nearest(row["geometry"].x, row["geometry"].y, ids, lons, lats)
        if distance > settings.max_snap_m:
            log.warning("Dropped community %r: nearest kept node is %d m away (limit %d m)", name, round_half_up(distance), settings.max_snap_m)
            continue
        communities.append({"id": f"c{len(communities) + 1}", "name": name, "node": node, "population": None})

    graph = {"schema_version": "0.1", "nodes": nodes, "edges": edges, "hospitals": hospitals, "communities": communities}
    return graph, speeds


def write_graph(graph: dict, path: Path) -> None:
    data = json.dumps(graph, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_GRAPH_BYTES:
        raise RoadGraphError(f"graph.json would be {len(data)} bytes, over the {MAX_GRAPH_BYTES} bytes limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def download(bbox: tuple, osm_dir: Path) -> None:
    w, s, e, n = bbox
    area = f"({s},{w},{n},{e})"
    classes = "|".join(ROAD_CLASSES)
    queries = {
        "roads.osm": f'[out:xml][timeout:600];way["highway"~"^({classes})(_link)?$"]{area};(._;>;);out body;',
        "features.osm": (
            f'[out:xml][timeout:600];(nwr["amenity"="hospital"]{area};'
            f'node["place"~"^({"|".join(sorted(PLACE_TYPES))})$"]["name"]{area};);(._;>;);out body;'
        ),
    }
    osm_dir.mkdir(parents=True, exist_ok=True)
    for name, query in queries.items():
        log.info("Downloading %s from Overpass", name)
        request = urllib.request.Request(
            OVERPASS_URL,
            data=urllib.parse.urlencode({"data": query}).encode(),
            headers={"User-Agent": "vantage-pipeline"},
        )
        with urllib.request.urlopen(request, timeout=900) as response:
            (osm_dir / name).write_bytes(response.read())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="road-graph", description="Build graph.json from OpenStreetMap data.")
    parser.add_argument("--download", action="store_true", help="fetch OSM data from Overpass into work/osm first")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        if args.download:
            download(SETTINGS.bbox, OSM_DIR)
        roads, features = OSM_DIR / "roads.osm", OSM_DIR / "features.osm"
        if not (roads.is_file() and features.is_file()):
            raise RoadGraphError(f"OSM data not found in {OSM_DIR}; run `road-graph --download` first")
        graph, speeds = build(roads, features, SETTINGS)
        write_graph(graph, OUTPUT / "graph.json")
        # shortcut: speed table hand-off to meta.json (P7) is not agreed with Ron yet; it waits in work/ until then.
        WORK.mkdir(parents=True, exist_ok=True)
        (WORK / "speed_model_kmh.json").write_text(json.dumps(speeds, sort_keys=True) + "\n", encoding="utf-8")
    except RoadGraphError as exc:
        sys.exit(f"road-graph: {exc}")
    log.info("Wrote %s (%d nodes, %d edges)", OUTPUT / "graph.json", len(graph["nodes"]), len(graph["edges"]))
