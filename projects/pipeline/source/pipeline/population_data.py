"""Population stage (E4): the WorldPop raster -> communities[].population in a zone's graph.json."""

import argparse
import json
import logging
import math
import os
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.windows import Window

from .area_config import PIPELINE_DIR, ConfigError, Zone, load_zone
from .road_graph import MAX_SNAP_M, WORK_DIR, round_half_up

log = logging.getLogger(__name__)

EARTH_RADIUS_M = 6371008.8
BLOCK_CELLS = 2_000_000  # pixels x communities per block: bounds the memory of the distance matrix
USER_AGENT = "vantage-pipeline"  # generic on purpose: no name, email or machine data


class PopulationError(Exception):
  pass


def _id_number(community_id: str) -> int:
  return int(community_id.removeprefix("c"))


def _read_json(path: Path):
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, ValueError) as exc:
    raise PopulationError(f"{path}: cannot be read ({exc})") from None


def _check_ids(graph: dict, originals: list[dict]) -> None:
  in_graph = {c["id"] for c in graph["communities"]}
  in_file = {c["id"] for c in originals}
  differing = in_graph ^ in_file
  if differing:
    first = min(differing, key=_id_number)
    raise PopulationError(f"communities.json and graph.json do not list the same communities (first id that differs: {first})")


def _pixel_window(src, bbox: tuple[float, float, float, float]) -> Window:
  """The pixels whose center lies inside bbox, as a window of the raster."""
  west, south, east, north = bbox
  t = src.transform
  cols = (math.ceil((west - t.c) / t.a - 0.5), math.floor((east - t.c) / t.a - 0.5))
  rows = (math.ceil((north - t.f) / t.e - 0.5), math.floor((south - t.f) / t.e - 0.5))  # t.e < 0: north is the first row
  col0, col1 = max(cols[0], 0), min(cols[1], src.width - 1)
  row0, row1 = max(rows[0], 0), min(rows[1], src.height - 1)
  if col0 > col1 or row0 > row1:
    raise PopulationError(f"{Path(src.name).name}: does not intersect the zone bbox")
  return Window(col0, row0, col1 - col0 + 1, row1 - row0 + 1)


def _assign(src, window: Window, places: list[dict]) -> tuple[np.ndarray, np.ndarray, float, float, float]:
  """Per community: people assigned and pixels assigned; then the raster total, assigned and unassigned people."""
  data = src.read(1, window=window).astype("float64")
  valid = ~np.isnan(data)
  if src.nodata is not None:
    valid &= data != src.nodata
  t = src.transform
  col_lon = t.c + (window.col_off + np.arange(window.width) + 0.5) * t.a
  place_lon = np.array([p["lon"] for p in places])
  place_lat = np.array([p["lat"] for p in places])
  place_lat_rad = np.radians(place_lat)
  sums = np.zeros(len(places))
  counts = np.zeros(len(places), dtype=int)
  total = assigned = 0.0
  rows_per_block = max(1, BLOCK_CELLS // (window.width * len(places)))
  for start in range(0, window.height, rows_per_block):
    stop = min(start + rows_per_block, window.height)
    block_valid = valid[start:stop]
    rows, cols = np.nonzero(block_valid)
    if rows.size == 0:
      continue
    people = data[start:stop][rows, cols]
    lat = (t.f + (window.row_off + start + rows + 0.5) * t.e)[:, None]
    lon = col_lon[cols][:, None]
    # Differences are taken in degrees: exact for symmetric places, so ties stay exact ties.
    a = np.sin(np.radians(place_lat - lat) / 2) ** 2 + np.cos(np.radians(lat)) * np.cos(place_lat_rad) * np.sin(np.radians(place_lon - lon) / 2) ** 2
    distance = 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))
    nearest = distance.argmin(axis=1)  # first minimum: places are sorted by id, so ties go to the lowest id
    within = distance[np.arange(rows.size), nearest] <= MAX_SNAP_M
    total += float(people.sum())
    assigned += float(people[within].sum())
    sums += np.bincount(nearest[within], weights=people[within], minlength=len(places))
    counts += np.bincount(nearest[within], minlength=len(places))
  return sums, counts, total, assigned, total - assigned


def _write_atomic(path: Path, data: bytes) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  part = path.with_name(path.name + ".part")
  part.write_bytes(data)
  os.replace(part, path)


def _dump(content) -> bytes:
  return (json.dumps(content, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def run(zone: Zone, work_dir: Path, skip: bool = False) -> Path:
  """Fills the population of the zone's graph.json; writes nothing unless every check passed."""
  graph_path = zone.output_dir / "graph.json"
  graph = _read_json(graph_path)
  if skip:
    values = {c["id"]: None for c in graph["communities"]}
    log.info("Population skipped (--no-population): every community keeps population null")
    report = None
  else:
    originals = _read_json(work_dir / "communities.json")
    _check_ids(graph, originals)
    raster = PIPELINE_DIR / zone.population_raster
    if not raster.is_file():
      raise PopulationError(f"Raster not found: {raster}; run `make worldpop AREA={zone.id}` to download it")
    places = sorted(originals, key=lambda p: _id_number(p["id"]))
    try:
      with rasterio.open(raster) as src:
        if src.crs is None or src.crs.to_epsg() != 4326:
          raise PopulationError(f"{raster.name}: the raster is in {src.crs or 'no CRS'}, not EPSG:4326 (no reprojection)")
        sums, counts, total, assigned, unassigned = _assign(src, _pixel_window(src, zone.bbox), places)
    except RasterioIOError as exc:
      raise PopulationError(f"{raster.name}: cannot be read as a raster ({exc})") from None
    # shortcut: a community whose people round to 0 gets null because graph.schema.json requires population >= 1.
    values = {
      p["id"]: (round_half_up(sums[i]) or None) if counts[i] else None
      for i, p in enumerate(places)
    }
    with_value = sum(v is not None for v in values.values())
    report = {
      "raster_total": total,
      "assigned": assigned,
      "unassigned": unassigned,
      "communities_with_value": with_value,
      "communities_without_value": len(values) - with_value,
      "share_with_value": with_value / len(values) if values else 0.0,
    }
  for community in graph["communities"]:
    community["population"] = values[community["id"]]
  if report is not None:
    _write_atomic(work_dir / "population_report.json", (json.dumps(report, indent=2) + "\n").encode("utf-8"))
  _write_atomic(graph_path, _dump(graph))
  return graph_path


def download(zone: Zone, raster: Path) -> None:
  raster.parent.mkdir(parents=True, exist_ok=True)
  part = raster.with_name(raster.name + ".part")
  log.info("Downloading %s", zone.population_url)
  request = urllib.request.Request(zone.population_url, headers={"User-Agent": USER_AGENT})
  try:
    with urllib.request.urlopen(request, timeout=900) as response, part.open("wb") as out:
      while chunk := response.read(1 << 20):
        out.write(chunk)
    with rasterio.open(part):  # the file is replaced only when it opens as a raster
      pass
  except (OSError, RasterioIOError) as exc:
    part.unlink(missing_ok=True)
    raise PopulationError(f"Download of {zone.population_url} failed: {exc}") from None
  os.replace(part, raster)


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="population-data", description="Fill the population of a zone's communities from WorldPop.")
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  parser.add_argument("--download", action="store_true", help="only fetch the raster named by the zone config")
  parser.add_argument("--no-population", action="store_true", help="skip the raster and leave every population null")
  args = parser.parse_args(argv)
  logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
  try:
    zone = load_zone(args.area)
    if args.download:
      download(zone, PIPELINE_DIR / zone.population_raster)
      log.info("Saved the raster in %s", PIPELINE_DIR / zone.population_raster)
      return
    path = run(zone, WORK_DIR / zone.id, skip=args.no_population)
  except (ConfigError, PopulationError) as exc:
    raise SystemExit(f"population-data: {exc}") from None
  log.info("Wrote %s", path)
