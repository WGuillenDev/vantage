"""Rain stage (E1): IMERG Late daily cells -> rain.csv and exposure.rain_mm_12d per closure unit in scenarios.json."""

import argparse
import csv
import json
import logging
import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from .area_config import ConfigError, Zone, load_zone
from .road_graph import WORK_DIR
from .validate import _check_graph, _check_scenarios, _schema_errors

log = logging.getLogger(__name__)

WINDOW_DAYS = 12
CELL_DEG = Decimal("0.1")
PRODUCT, VERSION = "GPM_3IMERGDL", "07"
FILL_BELOW = -9000  # IMERG marks a missing cell with -9999.9
AUTH_HELP = (
  "Earthdata credentials are missing or the application is not authorized. Create an account at "
  "https://urs.earthdata.nasa.gov, authorize the application 'NASA GESDISC DATA ARCHIVE' under "
  "Applications > Authorized Apps, and set EARTHDATA_USERNAME and EARTHDATA_PASSWORD (or a ~/.netrc entry)."
)

Cell = tuple[Decimal, Decimal]


class RainContextError(Exception):
  pass


def _read_json(path: Path):
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, ValueError) as exc:
    raise RainContextError(f"{path}: cannot be read ({exc})") from None


def _write_atomic(path: Path, data: bytes) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  part = path.with_name(path.name + ".part")
  part.write_bytes(data)
  os.replace(part, path)


def _decimal(value: float) -> Decimal:
  return Decimal(repr(value))


def _cell_of(lon: float, lat: float) -> Cell:
  """The IMERG cell holding a point: centres sit at x.x5 on a 0.1 degree grid; a cell owns its lower edge, not its upper."""
  col = math.floor((_decimal(lon) + 180) / CELL_DEG)
  row = math.floor((_decimal(lat) + 90) / CELL_DEG)
  return Decimal(col) * CELL_DEG - 180 + CELL_DEG / 2, Decimal(row) * CELL_DEG - 90 + CELL_DEG / 2


def _read_cells(path: Path, period: list[date]) -> dict[tuple[date, Cell], Decimal]:
  """The valid value of every (day, cell) of the period; an absent or unusable one raises, naming the date."""
  try:
    text = path.read_text(encoding="utf-8")
  except OSError as exc:
    raise RainContextError(f"{path}: cannot be read ({exc}); run `make imerg AREA=<zone>`") from None
  reader = csv.DictReader(text.splitlines())
  if reader.fieldnames != ["date", "cell_lon", "cell_lat", "precip_mm"]:
    raise RainContextError(f"{path.name}: header must be 'date,cell_lon,cell_lat,precip_mm', got {reader.fieldnames}")
  raw: dict[tuple[str, Cell], str] = {}
  cells: set[Cell] = set()
  for line, row in enumerate(reader, start=2):
    try:
      cell = (Decimal(row["cell_lon"]), Decimal(row["cell_lat"]))
    except (InvalidOperation, TypeError):
      raise RainContextError(f"{path.name}: line {line}: cell_lon and cell_lat must be numbers") from None
    if not all(part.is_finite() for part in cell):
      raise RainContextError(f"{path.name}: line {line}: cell_lon and cell_lat must be finite numbers")
    key = (row["date"], cell)
    if key in raw:
      raise RainContextError(f"{path.name}: line {line}: repeats {row['date']} for cell {cell[0]}, {cell[1]}")
    raw[key] = row["precip_mm"]
    cells.add(cell)
  values = {}
  for day in period:
    for cell in sorted(cells):
      text_value = raw.get((day.isoformat(), cell))
      try:
        value = Decimal(text_value) if text_value is not None else None
      except InvalidOperation:
        value = None
      if value is None or not value.is_finite() or value < 0:
        raise RainContextError(f"{path.name}: no usable precip_mm for {day.isoformat()} at cell {cell[0]}, {cell[1]}")
      values[(day, cell)] = value
  return values


def _mean(values: list[Decimal], places: str) -> Decimal:
  return (sum(values) / len(values)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _check_units(scenarios: object) -> None:
  """The shape of scenarios.json that this stage reads; the full schema is checked on the output."""
  units = scenarios.get("candidates") if isinstance(scenarios, dict) else None
  if not isinstance(units, list):
    raise RainContextError("scenarios.json: must be an object with a candidates list")
  for number, unit in enumerate(units, start=1):
    if not isinstance(unit, dict) or not isinstance(unit.get("id"), str) or not isinstance(unit.get("edge_ids"), list) or not unit["edge_ids"]:
      raise RainContextError(f"scenarios.json: candidate {number} needs an id and a non-empty edge_ids list")


def _unit_cells(unit: dict, edges: dict[str, dict]) -> set[Cell]:
  """Cells holding a vertex of the unit's edges. shortcut: an edge crossing a cell with no vertex in it misses it; vertices are dense in OSM, upgrade by sampling segments if that shows up."""
  cells = set()
  for edge_id in unit["edge_ids"]:
    if edge_id not in edges:
      raise RainContextError(f"scenarios.json: unit {unit['id']} names unknown edge {edge_id}")
    cells.update(_cell_of(lon, lat) for lon, lat in edges[edge_id]["geometry"])
  return cells


def run(zone: Zone, work_dir: Path) -> Path:
  """Writes rain.csv and the exposure of every unit of scenarios.json; writes nothing unless every check passed."""
  start, end = date.fromisoformat(zone.rain_start), date.fromisoformat(zone.rain_end)
  window_start = end - timedelta(days=WINDOW_DAYS - 1)
  if window_start < start:
    raise RainContextError(f"The {WINDOW_DAYS} days ending at {end} start before the period {start}..{end}; move rain.start earlier")
  period = [start + timedelta(days=n) for n in range((end - start).days + 1)]
  values = _read_cells(work_dir / "imerg" / "cells.csv", period)
  cells = sorted({cell for _, cell in values})
  west, south, east, north = (_decimal(v) for v in zone.bbox)
  inside = [c for c in cells if west <= c[0] <= east and south <= c[1] <= north]
  if not inside:
    raise RainContextError(f"cells.csv holds no cell with its centre inside the bbox {list(zone.bbox)}")
  rain = [(day, _mean([values[(day, c)] for c in inside], "0.001")) for day in period]

  graph = _read_json(zone.output_dir / "graph.json")
  scenarios = _read_json(zone.output_dir / "scenarios.json")
  _check_units(scenarios)
  errors = _schema_errors("graph.json", graph, "graph.schema.json")
  if not errors:
    errors = _check_graph(graph)
  if errors:
    raise RainContextError("graph.json failed its checks, nothing written: " + "; ".join(errors))
  edges = {e["id"]: e for e in graph["edges"]}
  window = [window_start + timedelta(days=n) for n in range(WINDOW_DAYS)]
  for unit in scenarios["candidates"]:
    touched = _unit_cells(unit, edges)
    missing = touched - set(cells)
    if missing:
      lon, lat = min(missing)
      raise RainContextError(f"Unit {unit['id']} touches the cell {lon}, {lat}, which cells.csv does not hold")
    sums = [sum((values[(day, c)] for day in window), Decimal(0)) for c in sorted(touched)]
    unit["exposure"] = {"rain_mm_12d": float(_mean(sums, "0.1"))}
  errors = _schema_errors("scenarios.json", scenarios, "scenarios.schema.json")
  if not errors:
    errors = _check_scenarios(graph, scenarios, set())
  if errors:
    raise RainContextError("scenarios.json failed its checks, nothing written: " + "; ".join(errors))

  lines = ["date,precip_mm"] + [f"{day.isoformat()},{format(mm, 'f')}" for day, mm in rain]
  rain_path, path = zone.output_dir / "rain.csv", zone.output_dir / "scenarios.json"
  old_rain = rain_path.read_bytes() if rain_path.is_file() else None
  _write_atomic(rain_path, ("\n".join(lines) + "\n").encode("utf-8"))
  try:
    _write_atomic(path, (json.dumps(scenarios, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8"))
  except BaseException:
    # shortcut: if this restore fails too, the two files disagree; fine for a rerunnable offline stage.
    if old_rain is None:
      rain_path.unlink(missing_ok=True)
    else:
      rain_path.write_bytes(old_rain)
    raise
  return path


def _load_earthaccess():
  import earthaccess  # imported here so the stage and its tests work without the network libraries loaded

  return earthaccess


def _login(earthaccess) -> None:
  for strategy in ("environment", "netrc"):
    try:
      if getattr(earthaccess.login(strategy=strategy), "authenticated", False):
        return
    except Exception:  # noqa: BLE001 - earthaccess raises several types when a strategy has no credentials
      continue
  raise RainContextError(AUTH_HELP)


def _read_granule(item) -> tuple[str, list[tuple[str, str, str]]]:
  import h5py
  import numpy as np

  granule, handle, bbox = item
  day = granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]
  west, south, east, north = bbox
  with h5py.File(handle) as h5:
    lon, lat = np.round(h5["lon"][:], 2), np.round(h5["lat"][:], 2)
    cols = np.where((lon + 0.05 > west) & (lon - 0.05 < east))[0]  # cells whose extent intersects the bbox
    rows = np.where((lat + 0.05 > south) & (lat - 0.05 < north))[0]
    block = h5["precipitation"][0, cols[0] : cols[-1] + 1, rows[0] : rows[-1] + 1]
  out = []
  for i, col in enumerate(cols):
    for j, row in enumerate(rows):
      value = block[i, j]  # the float32 as stored: str() gives its short form (0.35), float() would add noise digits
      out.append((f"{lon[col]:.2f}", f"{lat[row]:.2f}", "" if float(value) < FILL_BELOW else str(value)))
  return day, out


def download(zone: Zone, imerg_dir: Path, earthaccess=None) -> None:
  """Fetches IMERG Late daily cells for the zone's period; writes nothing unless the whole download worked."""
  earthaccess = earthaccess or _load_earthaccess()
  _login(earthaccess)
  try:
    granules = earthaccess.search_data(short_name=PRODUCT, version=VERSION, temporal=(zone.rain_start, zone.rain_end), count=1000)
    if not granules:
      raise RainContextError(f"No {PRODUCT} granules found for {zone.rain_start}..{zone.rain_end}")
    handles = earthaccess.open(granules)
    with ThreadPoolExecutor(8) as pool:
      days = sorted(pool.map(_read_granule, ((g, h, zone.bbox) for g, h in zip(granules, handles, strict=True))))
  except RainContextError:
    raise
  except Exception as exc:  # noqa: BLE001 - a 401 or 403 means the application is not authorized
    if isinstance(exc, PermissionError) or any(code in str(exc) for code in ("401", "403", "Unauthorized", "Forbidden")):
      raise RainContextError(f"{AUTH_HELP} (error received: {type(exc).__name__}: {exc})") from None
    raise RainContextError(f"IMERG download failed: {type(exc).__name__}: {exc}") from None
  lines = ["date,cell_lon,cell_lat,precip_mm"] + [f"{day},{lon},{lat},{value}" for day, rows in days for lon, lat, value in rows]
  _write_atomic(imerg_dir / "cells.csv", ("\n".join(lines) + "\n").encode("utf-8"))
  source = {"product": PRODUCT, "version": VERSION, "start": zone.rain_start, "end": zone.rain_end}
  _write_atomic(imerg_dir / "source.json", (json.dumps(source, indent=2) + "\n").encode("utf-8"))


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="rain-context", description="Write a zone's rain.csv and per-unit recent-rain context from IMERG.")
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  parser.add_argument("--download", action="store_true", help="only fetch the IMERG cells (needs Earthdata credentials)")
  args = parser.parse_args(argv)
  logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
  try:
    zone = load_zone(args.area)
    work_dir = WORK_DIR / zone.id
    if args.download:
      download(zone, work_dir / "imerg")
      print(f"{zone.id}: saved the IMERG cells in {work_dir / 'imerg'}")
    else:
      print(f"{zone.id}: wrote {run(zone, work_dir)}")
  except (ConfigError, RainContextError) as exc:
    raise SystemExit(f"rain-context: {exc}") from None
