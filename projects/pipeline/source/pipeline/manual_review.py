import argparse
import json
import math
import re
from collections import deque
from pathlib import Path

from .area_config import PIPELINE_DIR, ConfigError, load_zone

REPORTS_DIR = PIPELINE_DIR / "reports"
WORK_DIR = PIPELINE_DIR / "work"
SHEET_NAME = "manual_review.json"
CLASSES = ("real", "snapping_artifact", "oneway_artifact", "outside_network")
MAX_COMMUNITIES = 20
PASS_SHARE = 0.8
EARTH_RADIUS_M = 6371008.8


class ReviewError(Exception):
  pass


def _id_number(identifier: str) -> int:
  match = re.search(r"\d+", identifier)
  return int(match.group()) if match else 0


def choose_units(scenarios: dict) -> list[dict]:
  """Units A (rank 1), B (middle of the units with impact) and C (longest), each at most once."""
  by_rank = sorted(scenarios["candidates"], key=lambda u: u["rank"])
  with_impact = [u for u in by_rank if u["affected_community_ids"]]
  middle = (len(with_impact) + 1) // 2 - 1  # position ceil(n/2), zero-based
  # shortcut: when the middle unit is taken, look forward and then backward; the spec does not say which way "next" goes.
  middle_order = with_impact[middle:] + with_impact[:middle][::-1]
  longest_order = sorted(by_rank, key=lambda u: (-u["length_m"], _id_number(u["id"])))
  chosen: list[dict] = []
  for why, order in (("highest_criticality", by_rank), ("median_criticality", middle_order), ("longest", longest_order)):
    taken = {u["id"] for u in chosen}
    pick = next((u for u in order if u["id"] not in taken), None)
    if pick is not None:
      chosen.append({**pick, "why": why})
  return chosen


def _distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
  p1, p2 = math.radians(lat1), math.radians(lat2)
  a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
  return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _reaches_hospital(graph: dict, closed: set[str], start: str) -> bool:
  """True when `start` still touches a hospital node with the closed edges removed and direction ignored."""
  neighbours: dict[str, list[str]] = {}
  for e in graph["edges"]:
    if e["id"] not in closed:
      neighbours.setdefault(e["from"], []).append(e["to"])
      neighbours.setdefault(e["to"], []).append(e["from"])
  targets = {h["node"] for h in graph["hospitals"]}
  seen, queue = {start}, deque([start])
  while queue:
    current = queue.popleft()
    if current in targets:
      return True
    for other in neighbours.get(current, ()):
      if other not in seen:
        seen.add(other)
        queue.append(other)
  return False


def _community_row(community: dict, original: dict, node: dict, closed: set[str], graph: dict, endpoints: set[str]) -> dict:
  joined = _reaches_hospital(graph, closed, community["node"])
  is_endpoint = community["node"] in endpoints
  suggestion = "oneway_artifact" if joined else "snapping_artifact" if is_endpoint else None
  return {
    "community_id": community["id"],
    "name": community["name"],
    "population": community["population"],
    "distance_to_node_m": round(_distance_m(original["lon"], original["lat"], node["lon"], node["lat"]), 1),
    "node_is_closed_endpoint": is_endpoint,
    "joined_ignoring_direction": joined,
    "suggested_class": suggestion,
    "class": "",
    "note": "",
  }


def build_sheet(graph: dict, scenarios: dict, units: list[dict], originals: list[dict]) -> dict:
  edges = {e["id"]: e for e in graph["edges"]}
  nodes = {n["id"]: n for n in graph["nodes"]}
  communities = {c["id"]: c for c in graph["communities"]}
  original_by_id = {o["id"]: o for o in originals}
  unit_edges = {u["id"]: u["edge_ids"] for u in units}
  sheet_units = []
  for chosen in choose_units(scenarios):
    if chosen["id"] not in unit_edges:
      raise ReviewError(f"closure_units.json: unit {chosen['id']} is missing")
    closed = set(unit_edges[chosen["id"]])
    endpoints = {end for edge_id in closed for end in (edges[edge_id]["from"], edges[edge_id]["to"])}
    isolated = [communities[cid] for cid in chosen["isolated_community_ids"]]
    isolated.sort(key=lambda c: (c["population"] is None, -(c["population"] or 0), _id_number(c["id"])))
    rows = []
    for community in isolated[:MAX_COMMUNITIES]:
      original = original_by_id.get(community["id"])
      if original is None:
        raise ReviewError(f"communities.json: no coordinates for {community['id']}")
      rows.append(_community_row(community, original, nodes[community["node"]], closed, graph, endpoints))
    sheet_units.append({"id": chosen["id"], "why": chosen["why"], "communities": rows})
  return {"reviewer": "", "reviewed_on": "", "units": sheet_units}


def _read_json(path: Path):
  if not path.exists():
    raise ReviewError(f"{path.name} not found in {path.parent}")
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, ValueError) as exc:
    raise ReviewError(f"{path.name}: cannot be read ({exc})") from None


def _write_json(path: Path, data: dict) -> None:
  path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def execute_prepare(output_dir: Path, work_dir: Path, reports_dir: Path) -> Path:
  path = reports_dir / SHEET_NAME
  if path.exists():
    raise ReviewError(f"{path} already exists; move it away before preparing a new sheet")
  sheet = build_sheet(
    _read_json(output_dir / "graph.json"),
    _read_json(output_dir / "scenarios.json"),
    _read_json(work_dir / "closure_units.json"),
    _read_json(work_dir / "communities.json"),
  )
  reports_dir.mkdir(parents=True, exist_ok=True)
  _write_json(path, sheet)
  return path


def _blank(value: object) -> bool:
  return not isinstance(value, str) or not value.strip()


def execute_summarize(reports_dir: Path) -> Path:
  path = reports_dir / SHEET_NAME
  sheet = _read_json(path)
  for field in ("reviewer", "reviewed_on"):
    if _blank(sheet.get(field)):
      raise ReviewError(f"{path.name}: {field} is empty")
  listed = [c for u in sheet["units"] for c in u["communities"]]
  for community in listed:
    value = community.get("class")
    if not _blank(value) and value not in CLASSES:
      raise ReviewError(f"{path.name}: community {community['community_id']} has an unknown class {value!r}")
  counts = {name: sum(1 for c in listed if c.get("class") == name) for name in CLASSES}
  unclassified = sum(1 for c in listed if _blank(c.get("class")))
  complete = bool(listed) and unclassified == 0
  share = counts["real"] / len(listed) if complete else None
  sheet["summary"] = {"counts": counts, "unclassified": unclassified, "share_real": share}
  sheet["verdict"] = "incomplete" if not complete else "pass" if share >= PASS_SHARE else "fail"
  _write_json(path, sheet)
  return path


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="manual-review", description="Prepare and summarize the hand review of isolated communities.")
  parser.add_argument("command", choices=("prepare", "summarize"))
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  args = parser.parse_args(argv)
  try:
    zone = load_zone(args.area)
    reports_dir = REPORTS_DIR / zone.id
    if args.command == "prepare":
      path = execute_prepare(zone.output_dir, WORK_DIR / zone.id, reports_dir)
    else:
      path = execute_summarize(reports_dir)
  except (ConfigError, ReviewError) as exc:
    raise SystemExit(str(exc)) from None
  print(f"{zone.id}: {args.command} done, sheet at {path}")
