import csv
import io
import json
import sys
from datetime import date, timedelta
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

MAX_OVERLAY_BYTES = 2 * 1024 * 1024
SCHEMAS = Path(__file__).resolve().parents[3] / "contract" / "schemas"
JSON_FILES = {
  "meta.json": "meta.schema.json",
  "change.geojson": "change.schema.json",
  "graph.json": "graph.schema.json",
  "scenarios.json": "scenarios.schema.json",
}


@cache
def _validator(schema_file: str) -> Draft202012Validator:
  return Draft202012Validator(json.loads((SCHEMAS / schema_file).read_text(encoding="utf-8")))


def _schema_errors(name: str, data: object, schema_file: str) -> list[str]:
  errors = sorted(_validator(schema_file).iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
  return [f"{name}: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errors]


def _read(folder: Path, name: str, errors: list[str]) -> str | None:
  path = folder / name
  if not path.is_file():
    errors.append(f"{name}: file is missing")
    return None
  try:
    return path.read_text(encoding="utf-8")
  except UnicodeDecodeError as exc:
    errors.append(f"{name}: not valid UTF-8 ({exc})")
    return None


def _load(folder: Path, name: str, errors: list[str]) -> object | None:
  text = _read(folder, name, errors)
  if text is None:
    return None
  try:
    return json.loads(text)
  except json.JSONDecodeError as exc:
    errors.append(f"{name}: invalid JSON ({exc})")
    return None


def _load_rain(folder: Path, errors: list[str]) -> list[dict] | None:
  text = _read(folder, "rain.csv", errors)
  if text is None:
    return None
  reader = csv.DictReader(io.StringIO(text, newline=""))
  if reader.fieldnames != ["date", "precip_mm"]:
    errors.append(f"rain.csv: header must be 'date,precip_mm', got {reader.fieldnames}")
    return None
  rows = []
  for n, row in enumerate(reader, start=2):
    try:
      row["precip_mm"] = float(row["precip_mm"])
    except (TypeError, ValueError):
      errors.append(f"rain.csv: line {n}: precip_mm is not a number")
      continue
    errors += [f"rain.csv: line {n}: {e.message}" for e in _validator("rain.schema.json").iter_errors(row)]
    rows.append(row)
  return rows


def _check_meta(folder: Path, meta: dict) -> list[str]:
  errors = []
  # `passes` is optional since 0.2: the radar change layer may be absent.
  if passes := meta.get("passes"):
    for key in ("track", "direction", "crid"):
      if passes["before"][key] != passes["after"][key]:
        errors.append(f"meta.json: passes.before.{key} and passes.after.{key} must be identical")
  for o in meta.get("overlays", []):
    where = f"meta.json: overlays/{o['id']}"
    w, s, e, n = o["bounds"]
    if not (w < e and s < n):
      errors.append(f"{where}/bounds: needs west < east and south < north")
    path = folder / o["file"]
    if not path.is_file():
      errors.append(f"{where}/file: {o['file']} does not exist")
    elif path.stat().st_size > MAX_OVERLAY_BYTES:
      errors.append(f"{where}/file: {o['file']} is larger than {MAX_OVERLAY_BYTES} bytes")
  return errors


def _check_graph(graph: dict) -> list[str]:
  errors = []
  nodes = {n["id"] for n in graph["nodes"]}
  for e in graph["edges"]:
    errors += [f"graph.json: edges/{e['id']}/{end}: unknown node {e[end]}" for end in ("from", "to") if e[end] not in nodes]
  for kind in ("hospitals", "communities"):
    errors += [f"graph.json: {kind}/{i['id']}/node: unknown node {i['node']}" for i in graph[kind] if i["node"] not in nodes]
  return errors


def _refs(where: str, community_id: str, hospital_id: str | None, communities: set, hospitals: set) -> list[str]:
  errors = []
  if community_id not in communities:
    errors.append(f"scenarios.json: {where}: unknown community {community_id}")
  if hospital_id is not None and hospital_id not in hospitals:
    errors.append(f"scenarios.json: {where}: unknown hospital {hospital_id}")
  return errors


def _check_scenarios(graph: dict, scenarios: dict, zone_ids: set[str]) -> list[str]:
  errors = []
  edges = {e["id"]: e for e in graph["edges"]}
  communities = {c["id"] for c in graph["communities"]}
  hospitals = {h["id"] for h in graph["hospitals"]}
  candidate_ids = {c["id"] for c in scenarios["candidates"]}
  for e in graph["edges"]:
    if e["candidate_id"] is not None and e["candidate_id"] not in candidate_ids:
      errors.append(f"graph.json: edges/{e['id']}/candidate_id: {e['candidate_id']} is not in scenarios.json")
  for b in scenarios["baseline"]:
    errors += _refs("baseline", b["community_id"], b["hospital_id"], communities, hospitals)
  for c in scenarios["candidates"]:
    where = f"scenarios.json: candidates/{c['id']}"
    isolated, affected = set(c["isolated_community_ids"]), set(c["affected_community_ids"])
    for edge_id in c["edge_ids"]:
      if edge_id not in edges:
        errors.append(f"{where}/edge_ids: unknown edge {edge_id}")
      elif edges[edge_id]["candidate_id"] != c["id"]:
        errors.append(f"{where}/edge_ids: edge {edge_id} has candidate_id {edges[edge_id]['candidate_id']}")
    errors += [f"{where}/zone_ids: unknown zone {z}" for z in c["zone_ids"] if z not in zone_ids]
    errors += [f"{where}: unknown community {cid}" for cid in affected | isolated if cid not in communities]
    if not isolated <= affected:
      errors.append(f"{where}/isolated_community_ids: must be a subset of affected_community_ids")
    errors += [
      f"{where}/suspect_isolated_community_ids: {cid} is not in isolated_community_ids"
      for cid in c["suspect_isolated_community_ids"]
      if cid not in isolated
    ]
    for p in c["per_community"]:
      errors += _refs(f"{where}/per_community", p["community_id"], p["hospital_id"], communities, hospitals)
      if (p["community_id"] in isolated) != (p["time_s"] is None and p["extra_s"] is None):
        errors.append(f"{where}/per_community/{p['community_id']}: time_s and extra_s must be null exactly when isolated")
  return errors


def _check_rain(rows: list[dict], period: dict) -> list[str]:
  try:
    days = [date.fromisoformat(r["date"]) for r in rows]
  except ValueError:
    return ["rain.csv: date: must be valid ISO dates (YYYY-MM-DD)"]
  errors = []
  if any(b - a != timedelta(days=1) for a, b in zip(days, days[1:])):
    errors.append("rain.csv: date: rows must be ascending with one row per day and no gaps")
  if not days or days[0] > date.fromisoformat(period["start"]) or days[-1] < date.fromisoformat(period["end"]):
    errors.append(f"rain.csv: date: must cover meta.json rain period {period['start']}..{period['end']}")
  return errors


def validate_dir(folder: Path) -> list[str]:
  errors: list[str] = []
  # change.geojson is the optional radar layer: a zone without it is valid.
  data = {name: _load(folder, name, errors) for name in JSON_FILES if name != "change.geojson" or (folder / name).exists()}
  rows = _load_rain(folder, errors)
  ok = {}
  for name, schema_file in JSON_FILES.items():
    if data.get(name) is not None:
      found = _schema_errors(name, data[name], schema_file)
      errors += found
      if not found:
        ok[name] = data[name]
  if "meta.json" in ok:
    errors += _check_meta(folder, ok["meta.json"])
    if rows is not None:
      errors += _check_rain(rows, ok["meta.json"]["rain"])
  if "graph.json" in ok:
    errors += _check_graph(ok["graph.json"])
    if "scenarios.json" in ok:
      zones = {f["properties"]["id"] for f in ok["change.geojson"]["features"]} if "change.geojson" in ok else set()
      errors += _check_scenarios(ok["graph.json"], ok["scenarios.json"], zones)
  return errors


def validate_storage(root: Path) -> list[str]:
  errors: list[str] = []
  areas = _load(root, "areas.json", errors)
  if areas is None:
    return errors
  if found := _schema_errors("areas.json", areas, "areas.schema.json"):
    return found
  seen: set[str] = set()
  for area in areas["areas"]:
    zone_id = area["id"]
    if zone_id in seen:
      errors.append(f"areas.json: areas/{zone_id}/id: listed twice")
    elif not (root / zone_id).is_dir():
      errors.append(f"areas.json: areas/{zone_id}: folder {zone_id}/ does not exist")
    else:
      errors += [f"{zone_id}/{line}" for line in validate_dir(root / zone_id)]
    seen.add(zone_id)
  return errors


def main() -> None:
  if len(sys.argv) != 2:
    sys.exit("usage: validate <storage-folder>")
  folder = Path(sys.argv[1])
  errors = validate_storage(folder)
  for line in errors:
    print(line, file=sys.stderr)
  if errors:
    sys.exit(f"{len(errors)} problem(s) found in {folder}")
  print(f"{folder}: OK")
