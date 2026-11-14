import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMAS = Path(__file__).resolve().parents[3] / "contract" / "schemas"
JSON_FILES = {
    "meta.json": "meta.schema.json",
    "change.geojson": "change.schema.json",
    "graph.json": "graph.schema.json",
    "scenarios.json": "scenarios.schema.json",
}


def _schema_errors(name: str, data: object, schema_file: str) -> list[str]:
    schema = json.loads((SCHEMAS / schema_file).read_text(encoding="utf-8"))
    errors = Draft202012Validator(schema).iter_errors(data)
    return [
        f"{name}: {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(errors, key=lambda e: list(map(str, e.absolute_path)))
    ]


def _load(folder: Path, name: str, errors: list[str]) -> object | None:
    path = folder / name
    if not path.is_file():
        errors.append(f"{name}: file is missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{name}: invalid JSON ({exc})")
        return None


def _load_rain(folder: Path, errors: list[str]) -> list[dict] | None:
    path = folder / "rain.csv"
    if not path.is_file():
        errors.append("rain.csv: file is missing")
        return None
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
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
            rows.append(row)
    return rows


def _check_meta(folder: Path, meta: dict) -> list[str]:
    errors = []
    before, after = meta["passes"]["before"], meta["passes"]["after"]
    for key in ("track", "direction", "crid"):
        if before[key] != after[key]:
            errors.append(f"meta.json: passes.before.{key} and passes.after.{key} must be identical")
    for o in meta["overlays"]:
        w, s, e, n = o["bounds"]
        if not (w < e and s < n):
            errors.append(f"meta.json: overlays/{o['id']}/bounds: needs west < east and south < north")
        if not (folder / o["file"]).is_file():
            errors.append(f"meta.json: overlays/{o['id']}/file: {o['file']} does not exist")
    return errors


def _check_graph(graph: dict) -> list[str]:
    errors = []
    nodes = {n["id"] for n in graph["nodes"]}
    for e in graph["edges"]:
        for end in ("from", "to"):
            if e[end] not in nodes:
                errors.append(f"graph.json: edges/{e['id']}/{end}: unknown node {e[end]}")
    for kind in ("hospitals", "communities"):
        for item in graph[kind]:
            if item["node"] not in nodes:
                errors.append(f"graph.json: {kind}/{item['id']}/node: unknown node {item['node']}")
    return errors


def _check_scenarios(graph: dict, scenarios: dict, zone_ids: set[str]) -> list[str]:
    errors = []
    edges = {e["id"]: e for e in graph["edges"]}
    communities = {c["id"] for c in graph["communities"]}
    hospitals = {h["id"] for h in graph["hospitals"]}
    candidates = {c["id"]: c for c in scenarios["candidates"]}
    for e in graph["edges"]:
        if e["candidate_id"] is not None and e["candidate_id"] not in candidates:
            errors.append(f"graph.json: edges/{e['id']}/candidate_id: {e['candidate_id']} is not in scenarios.json")
    for b in scenarios["baseline"]:
        errors += _refs("baseline", b["community_id"], b["hospital_id"], communities, hospitals)
    for c in scenarios["candidates"]:
        where = f"scenarios.json: candidates/{c['id']}"
        for edge_id in c["edge_ids"]:
            if edge_id not in edges:
                errors.append(f"{where}/edge_ids: unknown edge {edge_id}")
            elif edges[edge_id]["candidate_id"] != c["id"]:
                errors.append(f"{where}/edge_ids: edge {edge_id} has candidate_id {edges[edge_id]['candidate_id']}")
        for zone_id in c["zone_ids"]:
            if zone_id not in zone_ids:
                errors.append(f"{where}/zone_ids: unknown zone {zone_id}")
        for cid in c["affected_community_ids"] + c["isolated_community_ids"]:
            if cid not in communities:
                errors.append(f"{where}: unknown community {cid}")
        if not set(c["isolated_community_ids"]) <= set(c["affected_community_ids"]):
            errors.append(f"{where}/isolated_community_ids: must be a subset of affected_community_ids")
        for p in c["per_community"]:
            errors += _refs(f"{where}/per_community", p["community_id"], p["hospital_id"], communities, hospitals)
            isolated = p["community_id"] in c["isolated_community_ids"]
            if isolated != (p["time_s"] is None and p["extra_s"] is None):
                errors.append(f"{where}/per_community/{p['community_id']}: time_s and extra_s must be null exactly when isolated")
    return errors


def _refs(where: str, community_id: str, hospital_id: str | None, communities: set, hospitals: set) -> list[str]:
    errors = []
    if community_id not in communities:
        errors.append(f"scenarios.json: {where}: unknown community {community_id}")
    if hospital_id is not None and hospital_id not in hospitals:
        errors.append(f"scenarios.json: {where}: unknown hospital {hospital_id}")
    return errors


def _check_rain(rows: list[dict], period: dict) -> list[str]:
    errors = []
    days = [date.fromisoformat(r["date"]) for r in rows]
    if any(b - a != timedelta(days=1) for a, b in zip(days, days[1:])):
        errors.append("rain.csv: date: rows must be ascending with one row per day and no gaps")
    start, end = date.fromisoformat(period["start"]), date.fromisoformat(period["end"])
    if not days or days[0] > start or days[-1] < end:
        errors.append(f"rain.csv: date: must cover meta.json rain period {period['start']}..{period['end']}")
    return errors


def validate_dir(folder: Path) -> list[str]:
    errors: list[str] = []
    data = {name: _load(folder, name, errors) for name in JSON_FILES}
    rows = _load_rain(folder, errors)
    ok = {}
    for name, schema_file in JSON_FILES.items():
        if data[name] is not None:
            found = _schema_errors(name, data[name], schema_file)
            errors += found
            if not found:
                ok[name] = data[name]
    if rows is not None:
        schema = json.loads((SCHEMAS / "rain.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for n, row in enumerate(rows, start=2):
            errors += [f"rain.csv: line {n}: {e.message}" for e in validator.iter_errors(row)]
    if "meta.json" in ok:
        errors += _check_meta(folder, ok["meta.json"])
        if rows is not None:
            errors += _check_rain(rows, ok["meta.json"]["rain"]) if _rows_ok(rows) else []
    if "graph.json" in ok:
        errors += _check_graph(ok["graph.json"])
        if "scenarios.json" in ok and "change.geojson" in ok:
            zones = {f["properties"]["id"] for f in ok["change.geojson"]["features"]}
            errors += _check_scenarios(ok["graph.json"], ok["scenarios.json"], zones)
    return errors


def _rows_ok(rows: list[dict]) -> bool:
    try:
        for r in rows:
            date.fromisoformat(r["date"])
    except (KeyError, ValueError):
        return False
    return True


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: validate <data-folder>")
    folder = Path(sys.argv[1])
    errors = validate_dir(folder)
    for line in errors:
        print(line, file=sys.stderr)
    if errors:
        sys.exit(f"{len(errors)} problem(s) found in {folder}")
    print(f"{folder}: OK")
