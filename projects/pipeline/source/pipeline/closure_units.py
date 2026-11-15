"""Closure-units stage (P9): cuts the studied road into closure units and writes their ids into graph.json."""

import argparse
import json
import logging
import math
import os
from pathlib import Path

from .area_config import ConfigError, Zone, load_zone
from .road_graph import WORK_DIR, _metres
from .validate import _check_graph, _schema_errors

log = logging.getLogger(__name__)

PAIR_M = 120  # a one-way carriageway is paired with an opposite one whose midpoint is this close


class ClosureUnitsError(Exception):
  pass


def _number(edge_id: str) -> int:
  return int(edge_id.removeprefix("e"))


class _Groups:
  """Union-find over edge ids."""

  def __init__(self, ids):
    self.parent = {i: i for i in ids}

  def find(self, i):
    while self.parent[i] != i:
      self.parent[i] = self.parent[self.parent[i]]
      i = self.parent[i]
    return i

  def union(self, a, b):
    root_a, root_b = self.find(a), self.find(b)
    if root_a != root_b:
      self.parent[max(root_a, root_b, key=_number)] = min(root_a, root_b, key=_number)


def _midpoint(geometry: list[list[float]]) -> tuple[float, float]:
  """The point halfway along the geometry."""
  steps = [_metres(a, b) for a, b in zip(geometry, geometry[1:])]
  half, walked = sum(steps) / 2, 0.0
  for (a, b), step in zip(zip(geometry, geometry[1:]), steps):
    if walked + step >= half and step > 0:
      t = (half - walked) / step
      return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    walked += step
  return geometry[-1][0], geometry[-1][1]


def _direction(geometry: list[list[float]]) -> tuple[float, float]:
  (lon1, lat1), (lon2, lat2) = geometry[0], geometry[-1]
  return (lon2 - lon1) * math.cos(math.radians(lat1)), lat2 - lat1


def _opposite(a: dict, b: dict) -> bool:
  (ax, ay), (bx, by) = _direction(a["geometry"]), _direction(b["geometry"])
  return ax * bx + ay * by < 0


def _pair_edges(corridor: list[dict], groups: _Groups) -> None:
  """Joins each one-way edge with the nearest opposite one-way edge whose midpoint is within PAIR_M.

  shortcut: compares every pair of one-way corridor edges (quadratic); fine for a corridor of a few hundred edges,
  index the midpoints if a zone ever has tens of thousands.
  """
  one_way = [e for e in corridor if e["oneway"]]
  mids = {e["id"]: _midpoint(e["geometry"]) for e in one_way}
  for e in one_way:
    best = min(
      ((d, _number(f["id"]), f) for f in one_way if f is not e and _opposite(e, f) and (d := _metres(mids[e["id"]], mids[f["id"]])) <= PAIR_M),
      default=None, key=lambda c: c[:2],
    )
    if best:
      groups.union(e["id"], best[2]["id"])


def build_units(graph: dict, roads: tuple[str, ...]) -> list[dict]:
  """The closure units of the edges whose road is in `roads`: id, edge_ids and length_m, in id order."""
  corridor = [e for e in graph["edges"] if e["road"] in roads]
  if not corridor:
    raise ClosureUnitsError(f"No edge of graph.json matches closure.roads {list(roads)}")
  in_corridor = {e["id"] for e in corridor}
  touching: dict[str, list[dict]] = {}
  for e in graph["edges"]:
    touching.setdefault(e["from"], []).append(e)
    touching.setdefault(e["to"], []).append(e)

  chains = _Groups(in_corridor)  # corridor edges joined at plain nodes: the stretches between two junctions
  for node, here in touching.items():
    corridor_here = [e["id"] for e in here if e["id"] in in_corridor]
    if len(corridor_here) == 2 and len(here) == 2:  # not a junction: no other road, not an end
      chains.union(*corridor_here)
  units = _Groups(in_corridor)
  units.parent = dict(chains.parent)
  _pair_edges(corridor, units)

  by_edge = {e["id"]: e for e in corridor}
  members: dict[str, list[str]] = {}
  for edge_id in in_corridor:
    members.setdefault(units.find(edge_id), []).append(edge_id)

  def key(edge_ids: list[str]) -> tuple[float, float, int]:
    points = [p for i in edge_ids for p in by_edge[i]["geometry"]]
    lons, lats = [p[0] for p in points], [p[1] for p in points]
    return (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2, min(_number(i) for i in edge_ids)

  result = []
  for number, edge_ids in enumerate(sorted(members.values(), key=key), start=1):
    chain_lengths: dict[str, int] = {}
    for i in edge_ids:
      chain_lengths[chains.find(i)] = chain_lengths.get(chains.find(i), 0) + by_edge[i]["length_m"]
    result.append({"id": f"T-{number:02d}", "edge_ids": sorted(edge_ids, key=_number), "length_m": max(chain_lengths.values())})
  return result


def _dump(content, indent: int | None = None) -> bytes:
  separators = None if indent else (",", ":")
  return (json.dumps(content, indent=indent, separators=separators, ensure_ascii=False) + "\n").encode("utf-8")


def _write_atomic(path: Path, data: bytes) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  part = path.with_name(path.name + ".part")
  part.write_bytes(data)
  os.replace(part, path)


def run(zone: Zone, work_dir: Path) -> Path:
  """Writes the unit ids into the zone's graph.json and closure_units.json; writes nothing unless every check passed."""
  graph_path = zone.output_dir / "graph.json"
  try:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
  except (OSError, ValueError) as exc:
    raise ClosureUnitsError(f"{graph_path}: cannot be read ({exc})") from None
  errors = _schema_errors("graph.json", graph, "graph.schema.json")
  if not errors:
    errors = _check_graph(graph)
  if errors:
    raise ClosureUnitsError("graph.json failed its checks, nothing written: " + "; ".join(errors))
  units = build_units(graph, zone.closure_roads)
  owner = {edge_id: unit["id"] for unit in units for edge_id in unit["edge_ids"]}
  for edge in graph["edges"]:
    edge["candidate_id"] = owner.get(edge["id"])
  errors = _schema_errors("graph.json", graph, "graph.schema.json")
  if errors:
    raise ClosureUnitsError("graph.json failed its checks, nothing written: " + "; ".join(errors))
  # shortcut: if the second write fails the two files disagree; the stage is rerunnable, so a rerun repairs it.
  _write_atomic(work_dir / "closure_units.json", _dump(units, indent=2))
  _write_atomic(graph_path, _dump(graph))
  return graph_path


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="closure-units", description="Cut a zone's studied road into closure units.")
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  args = parser.parse_args(argv)
  logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
  try:
    zone = load_zone(args.area)
    path = run(zone, WORK_DIR / zone.id)
  except (ConfigError, ClosureUnitsError) as exc:
    raise SystemExit(f"closure-units: {exc}") from None
  print(f"{zone.id}: wrote {path}")
