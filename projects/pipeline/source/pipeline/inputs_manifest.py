"""Input manifest: SHA-256 of what a zone's run reads and of what it publishes, so an output can be traced to its inputs."""

import argparse
import hashlib
import json
from pathlib import Path

from .area_config import PIPELINE_DIR, ConfigError, Zone, load_zone

REPORTS_DIR = PIPELINE_DIR / "reports"
TEXT_SUFFIXES = {".toml", ".json", ".csv", ".txt"}
OUTPUT_FILES = ("graph.json", "scenarios.json", "rain.csv")  # meta.json is left out: it holds the time of the run


class InputsError(Exception):
  pass


def _digest(path: Path) -> dict:
  if not path.is_file():
    raise InputsError(f"{path.name}: not found in {path.parent}; run the pipeline first")
  data = path.read_bytes()
  if path.suffix in TEXT_SUFFIXES:
    data = data.replace(b"\r\n", b"\n")  # one hash on Windows and Linux
  return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def manifest(zone: Zone, base: Path) -> dict:
  """The digest of every input the stages read and of the files they publish; paths are relative to `base`."""
  work = f"work/{zone.id}"
  inputs = [
    f"configs/{zone.id}.toml",
    f"{work}/osm/roads.osm",
    f"{work}/osm/features.osm",
    f"{work}/osm/extract_date.txt",
    f"{work}/imerg/cells.csv",
    f"{work}/imerg/source.json",
    zone.population_raster,
  ]
  outputs = [f"output/{zone.id}/{name}" for name in OUTPUT_FILES]
  return {
    "zone": zone.id,
    "inputs": {name: _digest(base / name) for name in inputs},
    "outputs": {name: _digest(base / name) for name in outputs},
  }


def run(zone: Zone, base: Path, reports_dir: Path, check: bool = False) -> str:
  actual = manifest(zone, base)
  path = reports_dir / zone.id / "inputs.json"
  if not check:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8", newline="\n")
    return f"{zone.id}: wrote {path}"
  if not path.is_file():
    raise InputsError(f"{path.name} not found in {path.parent}; run `make inputs` first")
  expected = json.loads(path.read_text(encoding="utf-8"))
  different = [
    f"{section}/{name}"
    for section in ("inputs", "outputs")
    for name in actual[section]
    if expected.get(section, {}).get(name) != actual[section][name]
  ]
  if different:
    raise InputsError("differs from inputs.json: " + ", ".join(different))
  return f"{zone.id}: inputs and outputs match inputs.json"


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="inputs-manifest", description="Write or check the SHA-256 manifest of a zone's inputs and outputs.")
  parser.add_argument("--area", required=True, help="zone id, the name of a file in configs/ without .toml")
  parser.add_argument("--check", action="store_true", help="compare with reports/<zone>/inputs.json instead of writing it")
  args = parser.parse_args(argv)
  try:
    print(run(load_zone(args.area), PIPELINE_DIR, REPORTS_DIR, args.check))
  except (ConfigError, InputsError) as exc:
    raise SystemExit(f"inputs-manifest: {exc}") from None
