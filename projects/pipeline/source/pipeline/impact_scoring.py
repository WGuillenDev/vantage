"""Impact stage (P5): closes one closure unit at a time, measures the loss of access to the referral hospitals and ranks the units."""

import argparse
import heapq
import json
from collections import deque
from pathlib import Path

from .area_config import PIPELINE_DIR, ConfigError, Zone, load_zone
from .validate import _check_graph, _check_scenarios, _schema_errors

WORK_DIR = PIPELINE_DIR / "work"

# A route: (seconds, hospital id), or None when the community cannot reach any referral hospital.
Route = tuple[int, str] | None


class ImpactScoringError(Exception):
  pass


def _num(item_id: str) -> int:
  """Number of an id such as c12, e3 or h10, so that h2 sorts before h10."""
  return int("".join(ch for ch in item_id if ch.isdigit()))


def _nearest_hospitals(graph: dict, closed: set[str]) -> dict[str, tuple[int, str]]:
  """Per node, the route time and hospital id to the nearest hospital; ties go to the lowest hospital number."""
  reverse: dict[str, list[tuple[str, int]]] = {}
  # Routes run community -> hospital, so the search walks the edges backwards from the hospitals.
  for e in graph["edges"]:
    if e["id"] in closed:
      continue
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


def _routes(graph: dict, closed: set[str]) -> dict[str, Route]:
  nearest = _nearest_hospitals(graph, closed)
  return {c["id"]: nearest.get(c["node"]) for c in graph["communities"]}


def _nodes_joined_to_hospitals(graph: dict, closed: set[str]) -> set[str]:
  """Nodes that still touch a hospital node with the closed edges removed and direction ignored, found in one pass."""
  neighbours: dict[str, list[str]] = {}
  for e in graph["edges"]:
    if e["id"] not in closed:
      neighbours.setdefault(e["from"], []).append(e["to"])
      neighbours.setdefault(e["to"], []).append(e["from"])
  seen = {h["node"] for h in graph["hospitals"]}
  queue = deque(seen)
  while queue:
    for other in neighbours.get(queue.popleft(), ()):
      if other not in seen:
        seen.add(other)
        queue.append(other)
  return seen


def _closed_edges(given: dict, edges: dict[str, dict]) -> set[str]:
  for edge_id in given["edge_ids"]:
    # A non-text id (a list, for one) would raise TypeError on the lookup, so it is checked first.
    if not isinstance(edge_id, str) or edge_id not in edges:
      raise ImpactScoringError(f"unit {given['id']} lists edge {edge_id}, which is not in the graph")
  return set(given["edge_ids"])


def score(graph: dict, units: list[dict], alternates: list[dict] | tuple = ()) -> dict:
  """The content of scenarios.json for a graph and its closure units.

  Pure: it reads nothing but its arguments (the hospitals and every time_s come from `graph`), so a caller can pass
  a perturbed copy of the graph. `alternates` is copied to every unit; the caller takes it from the zone config.
  """
  communities = sorted(graph["communities"], key=lambda c: _num(c["id"]))
  population = {c["id"]: c["population"] for c in communities}
  edges = {e["id"]: e for e in graph["edges"]}
  baseline = _routes(graph, set())

  seen_ids: set[str] = set()
  results = []
  for given in units:
    if given["id"] in seen_ids:
      raise ImpactScoringError(f"unit id {given['id']} appears more than once")
    seen_ids.add(given["id"])
    closed = _closed_edges(given, edges)
    after = _routes(graph, closed)
    per_community = []
    for c in communities:
      base, now = baseline[c["id"]], after[c["id"]]
      if base is None:
        continue  # never affected without a baseline route
      if now is None:
        per_community.append({"community_id": c["id"], "time_s": None, "extra_s": None, "hospital_id": None})
      elif now[0] > base[0]:
        per_community.append({"community_id": c["id"], "time_s": now[0], "extra_s": now[0] - base[0], "hospital_id": now[1]})
    results.append((given, closed, per_community))

  # Taken over all the units together: it prices every isolated community, so it decides the ranking.
  penalty = max((p["extra_s"] for _, _, rows in results for p in rows if p["extra_s"] is not None), default=0)
  node_of = {c["id"]: c["node"] for c in communities}
  scored = []
  for given, closed, rows in results:
    affected = [p["community_id"] for p in rows]
    isolated = [p["community_id"] for p in rows if p["time_s"] is None]
    finite = [p["extra_s"] for p in rows if p["extra_s"] is not None]
    known = [population[c] for c in affected if population[c] is not None]
    ends = {end for edge_id in closed for end in (edges[edge_id]["from"], edges[edge_id]["to"])}
    # One pass per unit, and only when something is isolated: the check used to walk the whole graph per community.
    joined = _nodes_joined_to_hospitals(graph, closed) if isolated else set()
    suspect = [c for c in isolated if node_of[c] in ends or node_of[c] in joined]
    scored.append({
      "id": given["id"],
      "source": "network_consequence",
      "length_m": given["length_m"],
      "edge_ids": sorted(given["edge_ids"], key=_num),
      "zone_ids": [],
      "mean_delta_db": None,
      "criticality": sum((population[p["community_id"]] or 0) * (penalty if p["extra_s"] is None else p["extra_s"]) for p in rows),
      "extra_time_s": max(finite) if finite else (None if affected else 0),
      "population_dependent": sum(known) if known else None,
      "affected_community_ids": affected,
      "isolated_community_ids": isolated,
      "suspect_isolated_community_ids": suspect,
      "per_community": rows,
      "alternates": [dict(a) for a in alternates],
    })

  scored.sort(key=lambda c: (
    -c["criticality"],
    -len(c["isolated_community_ids"]),
    c["extra_time_s"] is None,
    -(c["extra_time_s"] or 0),
    min((_num(e) for e in c["edge_ids"]), default=0),
  ))
  for rank, c in enumerate(scored, start=1):
    c["rank"] = rank
  return {
    "schema_version": "0.3",
    "baseline": [_baseline_row(c["id"], baseline[c["id"]]) for c in communities],
    "candidates": scored,
  }


def _baseline_row(community_id: str, route: Route) -> dict:
  time_s, hospital_id = route if route else (None, None)
  return {"community_id": community_id, "time_s": time_s, "hospital_id": hospital_id}


def _load(path: Path):
  if not path.is_file():
    raise ImpactScoringError(f"{path.name} not found in {path.parent}; run the previous stages first")
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, ValueError) as exc:
    raise ImpactScoringError(f"{path.name}: cannot be read ({exc})") from None


def _check_units(units: object) -> list[dict]:
  if not isinstance(units, list):
    raise ImpactScoringError("closure_units.json: must be a list of units")
  for number, given in enumerate(units, start=1):
    if not isinstance(given, dict) or not isinstance(given.get("id"), str) or not isinstance(given.get("edge_ids"), list) or "length_m" not in given:
      raise ImpactScoringError(f"closure_units.json: unit {number} needs an id, edge_ids and length_m")
  return units


def run(zone: Zone, work_dir: Path) -> Path:
  """Scores the zone's units with `score` and writes scenarios.json; writes nothing unless every check passes."""
  graph = _load(zone.output_dir / "graph.json")
  units = _check_units(_load(work_dir / "closure_units.json"))
  errors = _schema_errors("graph.json", graph, "graph.schema.json")
  if not errors:
    errors = _check_graph(graph)
  if errors:
    raise ImpactScoringError("graph.json failed its checks, nothing written: " + "; ".join(errors))
  scenarios = score(graph, units, [{"name": name, "vehicles": vehicles} for name, vehicles in zone.closure_alternates])
  errors = _schema_errors("scenarios.json", scenarios, "scenarios.schema.json")
  if not errors:
    errors = _check_scenarios(graph, scenarios, set())
  if errors:
    raise ImpactScoringError("scenarios.json failed its checks, nothing written: " + "; ".join(errors))
  path = zone.output_dir / "scenarios.json"
  path.write_text(json.dumps(scenarios, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  return path


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="impact-scoring", description="Rank a zone's closure units by their effect on hospital access.")
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  args = parser.parse_args(argv)
  try:
    zone = load_zone(args.area)
    path = run(zone, WORK_DIR / zone.id)
  except (ConfigError, ImpactScoringError) as exc:
    raise SystemExit(f"impact-scoring: {exc}") from None
  print(f"{zone.id}: wrote {path}")
