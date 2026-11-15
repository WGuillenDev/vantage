import argparse
import math
import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parents[2]
CONFIGS_DIR = PIPELINE_DIR / "configs"
ZONE_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class ConfigError(Exception):
  pass


@dataclass(frozen=True)
class Zone:
  id: str
  name: str
  validated: bool
  bbox: tuple[float, float, float, float]
  referral_hospitals: tuple[str, ...]
  speed_model_kmh: dict[str, float]
  closure_roads: tuple[str, ...]
  closure_alternates: tuple[tuple[str, str], ...]
  population_raster: str
  population_url: str
  rain_start: str
  rain_end: str
  detection_limits: dict | None
  output_dir: Path


def _fail(file: str, key: str, problem: str) -> ConfigError:
  return ConfigError(f"{file}: {key}: {problem}")


def _get(table: dict, key: str, path: str, file: str):
  if key not in table:
    raise _fail(file, path, "missing required key")
  return table[key]


def _check_keys(table: dict, allowed: set[str], path: str, file: str) -> None:
  for key in table:
    if key not in allowed:
      raise _fail(file, f"{path}.{key}" if path else key, "unknown key")


def _table(parent: dict, key: str, allowed: set[str] | None, file: str) -> dict:
  value = _get(parent, key, key, file)
  if not isinstance(value, dict):
    raise _fail(file, key, "must be a table")
  if allowed is not None:
    _check_keys(value, allowed, key, file)
  return value


def _string(value: object, path: str, file: str) -> str:
  if not isinstance(value, str) or not value.strip():
    raise _fail(file, path, "must be a non-empty string")
  return value


def _string_list(value: object, path: str, file: str) -> tuple[str, ...]:
  if not isinstance(value, list) or not value:
    raise _fail(file, path, "must be a non-empty list")
  items = tuple(_string(v, path, file) for v in value)
  _no_repeats(items, path, file)
  return items


def _no_repeats(items: tuple[str, ...], path: str, file: str) -> None:
  if len(set(items)) != len(items):
    raise _fail(file, path, "has a repeated value")


def _number(value: object, path: str, file: str) -> float:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    raise _fail(file, path, "must be a number")
  return value


def _positive(value: object, path: str, file: str) -> float:
  if not (math.isfinite(_number(value, path, file)) and value > 0):
    raise _fail(file, path, "must be a finite number greater than 0")
  return value


def _iso_date(value: object, path: str, file: str) -> date:
  if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
    raise _fail(file, path, "must be a YYYY-MM-DD string")
  try:
    return date.fromisoformat(value)
  except ValueError:
    raise _fail(file, path, "is not a real date") from None


def _bbox(value: object, file: str) -> tuple[float, float, float, float]:
  if not isinstance(value, list) or len(value) != 4:
    raise _fail(file, "bbox", "must be four numbers [w, s, e, n]")
  w, s, e, n = (_number(v, "bbox", file) for v in value)
  # Written as "not in range" so that NaN fails too.
  if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s <= 90 and -90 <= n <= 90):
    raise _fail(file, "bbox", "longitude must be in [-180, 180] and latitude in [-90, 90]")
  if not (w < e and s < n):
    raise _fail(file, "bbox", "needs w < e and s < n")
  return (w, s, e, n)


def _alternates(value: object, file: str) -> tuple[tuple[str, str], ...]:
  if not isinstance(value, list):
    raise _fail(file, "closure.alternates", "must be a list")
  out = []
  for entry in value:
    if not isinstance(entry, dict):
      raise _fail(file, "closure.alternates", "each entry must be a table")
    _check_keys(entry, {"name", "vehicles"}, "closure.alternates", file)
    name = _string(_get(entry, "name", "closure.alternates.name", file), "closure.alternates.name", file)
    vehicles = _get(entry, "vehicles", "closure.alternates.vehicles", file)
    if vehicles not in ("light", "freight"):
      raise _fail(file, "closure.alternates.vehicles", "must be 'light' or 'freight'")
    out.append((name, vehicles))
  _no_repeats(tuple(name for name, _ in out), "closure.alternates", file)
  return tuple(out)


def _detection_limits(table: dict, file: str) -> dict | None:
  if "detection_limits" not in table:
    return None
  limits = _table(table, "detection_limits", {"min_detectable_area_ha", "min_delta_db", "note"}, file)
  for key in ("min_detectable_area_ha", "min_delta_db"):
    _positive(_get(limits, key, f"detection_limits.{key}", file), f"detection_limits.{key}", file)
  _string(_get(limits, "note", "detection_limits.note", file), "detection_limits.note", file)
  return dict(limits)


def available_ids(configs_dir: Path) -> list[str]:
  return sorted(p.stem for p in configs_dir.glob("*.toml") if p.is_file() and ZONE_ID.fullmatch(p.stem))


def load_zone(zone_id: str, configs_dir: Path = CONFIGS_DIR) -> Zone:
  if not ZONE_ID.fullmatch(zone_id):
    raise ConfigError(f"zone id {zone_id!r}: must be lowercase letters and digits joined by single hyphens")
  path = configs_dir / f"{zone_id}.toml"
  file = path.name
  # Matching against the listing, not is_file(), so a file spelled RUTA-32.toml is not found on a case-insensitive disk.
  ids = available_ids(configs_dir)
  if zone_id not in ids:
    raise ConfigError(f"{file}: no such config; available zones: {', '.join(ids) or 'none'}")
  try:
    # utf-8-sig drops the byte-order mark that some Windows editors add.
    data = tomllib.loads(path.read_bytes().decode("utf-8-sig"))
  except OSError as exc:
    raise ConfigError(f"{file}: cannot be read ({exc.strerror or exc})") from None
  except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
    raise ConfigError(f"{file}: invalid TOML ({exc})") from None
  _check_keys(
    data,
    {"name", "validated", "bbox", "hospitals", "speed_model_kmh", "closure", "detection_limits", "population", "rain"},
    "",
    file,
  )
  validated = _get(data, "validated", "validated", file)
  if not isinstance(validated, bool):
    raise _fail(file, "validated", "must be true or false")
  hospitals = _table(data, "hospitals", {"referral"}, file)
  speeds = _table(data, "speed_model_kmh", None, file)
  if "" in speeds:
    raise _fail(file, "speed_model_kmh", "road class name must not be empty")
  if not speeds:
    raise _fail(file, "speed_model_kmh", "needs at least one road class")
  closure = _table(data, "closure", {"roads", "alternates"}, file)
  population = _table(data, "population", {"raster", "url"}, file)
  rain = _table(data, "rain", {"start", "end"}, file)
  start = _iso_date(_get(rain, "start", "rain.start", file), "rain.start", file)
  end = _iso_date(_get(rain, "end", "rain.end", file), "rain.end", file)
  if start > end:
    raise _fail(file, "rain", "start is after end")
  return Zone(
    id=zone_id,
    name=_string(_get(data, "name", "name", file), "name", file),
    validated=validated,
    bbox=_bbox(_get(data, "bbox", "bbox", file), file),
    referral_hospitals=_string_list(_get(hospitals, "referral", "hospitals.referral", file), "hospitals.referral", file),
    speed_model_kmh={k: _positive(v, f"speed_model_kmh.{k}", file) for k, v in speeds.items()},
    closure_roads=_string_list(_get(closure, "roads", "closure.roads", file), "closure.roads", file),
    closure_alternates=_alternates(_get(closure, "alternates", "closure.alternates", file), file),
    population_raster=_string(_get(population, "raster", "population.raster", file), "population.raster", file),
    population_url=_string(_get(population, "url", "population.url", file), "population.url", file),
    rain_start=rain["start"],
    rain_end=rain["end"],
    detection_limits=_detection_limits(data, file),
    output_dir=configs_dir.parent / "output" / zone_id,
  )


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="area-config", description="Load and validate one zone config.")
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  args = parser.parse_args(argv)
  try:
    zone = load_zone(args.area, CONFIGS_DIR)
  except ConfigError as exc:
    raise SystemExit(str(exc)) from None
  print(f"{zone.id}: OK, output folder {zone.output_dir}")
