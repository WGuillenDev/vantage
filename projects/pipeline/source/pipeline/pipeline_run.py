import argparse
import importlib
import json
import shutil
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from pipeline.area_config import CONFIGS_DIR, ConfigError, Zone, available_ids, load_zone
from pipeline.validate import validate_dir

PIPELINE_DIR = Path(__file__).resolve().parents[2]
WORK_DIR = PIPELINE_DIR / "work"
STAGE_NAMES = ("road-graph", "population-data", "closure-units", "impact-scoring", "rain-context")
Stage = tuple[str, Callable[[Zone, Path], object]]


class PipelineRunError(Exception):
  pass


def default_stages() -> list[Stage]:
  """The five stages in their fixed order; each is the `run(zone, work_dir)` of its own module."""
  stages: list[Stage] = []
  for name in STAGE_NAMES:
    module = "pipeline." + name.replace("-", "_")
    try:
      stages.append((name, importlib.import_module(module).run))
    except ModuleNotFoundError as exc:
      if exc.name != module:
        raise
      raise PipelineRunError(f"stage {name} is not implemented yet ({module} not found)") from None
  return stages


def _write_json(path: Path, data: object) -> None:
  path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read(path: Path, hint: str) -> str:
  if not path.is_file():
    raise PipelineRunError(f"{path} not found; {hint}")
  return path.read_text(encoding="utf-8").strip()


def _population_filled(staging: Path) -> bool:
  graph = json.loads((staging / "graph.json").read_text(encoding="utf-8"))
  return any(c.get("population") is not None for c in graph["communities"])


def build_meta(zone: Zone, work_dir: Path, population_filled: bool) -> dict:
  source = json.loads(_read(work_dir / "imerg" / "source.json", f"run `make imerg AREA={zone.id}`"))
  extract_date = _read(work_dir / "osm" / "extract_date.txt", f"run `make osm AREA={zone.id}`")
  attributions = [f"© OpenStreetMap contributors (ODbL), extract {extract_date}", "IMERG Late (NASA GPM)"]
  if population_filled:
    attributions.append("WorldPop (modelled population estimate)")
  meta = {
    "schema_version": "0.3",
    "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "files": {"rain_csv_schema": "0.1"},
    "area": {"name": zone.name, "bbox": list(zone.bbox)},
    "rain": {"product": source["product"], "version": source["version"], "start": zone.rain_start, "end": zone.rain_end, "aggregation": "area_mean"},
    "speed_model_kmh": dict(zone.speed_model_kmh),
  }
  if zone.detection_limits is not None:
    meta["detection_limits"] = zone.detection_limits
  meta["attributions"] = attributions
  return meta


def run_zone(zone: Zone, work_dir: Path, stages: list[Stage] | None = None) -> Path:
  """Runs the stages into a staging folder and swaps it into `zone.output_dir` only if the validator passes."""
  stages = default_stages() if stages is None else stages
  final = zone.output_dir
  staging, old = final.with_name(f".{final.name}.new"), final.with_name(f".{final.name}.old")
  shutil.rmtree(staging, ignore_errors=True)
  staging.mkdir(parents=True)
  try:
    for name, stage in stages:
      try:
        stage(replace(zone, output_dir=staging), work_dir)
      except Exception as exc:
        raise PipelineRunError(f"stage {name} failed: {exc}") from None
    _write_json(staging / "meta.json", build_meta(zone, work_dir, _population_filled(staging)))
    if errors := validate_dir(staging):
      raise PipelineRunError("validator failed: " + "; ".join(errors))
  except BaseException:
    shutil.rmtree(staging, ignore_errors=True)
    raise
  shutil.rmtree(old, ignore_errors=True)
  if final.exists():
    final.rename(old)
  staging.rename(final)
  shutil.rmtree(old, ignore_errors=True)
  return final


def write_areas(output_root: Path, configs_dir: Path = CONFIGS_DIR) -> Path:
  """Lists every zone folder of `output_root`, by id, with its config's name, bbox and validated flag."""
  zones = [load_zone(p.name, configs_dir) for p in sorted(output_root.iterdir()) if p.is_dir() and not p.name.startswith(".")]
  areas = [{"id": z.id, "name": z.name, "bbox": list(z.bbox), "validated": z.validated} for z in zones]
  path = output_root / "areas.json"
  tmp = output_root / ".areas.json.new"
  _write_json(tmp, {"schema_version": "0.3", "areas": areas})
  tmp.replace(path)
  return path


def main(argv: list[str] | None = None) -> None:
  parser = argparse.ArgumentParser(prog="pipeline-run", description="Run every stage for a zone and publish it into output/.")
  parser.add_argument("--area", help="zone id; every zone in configs/ when omitted")
  args = parser.parse_args(argv)
  try:
    ids = [args.area] if args.area else available_ids(CONFIGS_DIR)
    for zone_id in ids:
      zone = load_zone(zone_id)
      print(f"{zone.id}: wrote {run_zone(zone, WORK_DIR / zone.id)}")
    if ids:
      write_areas(CONFIGS_DIR.parent / "output")
  except (ConfigError, PipelineRunError) as exc:
    raise SystemExit(f"pipeline-run: {exc}") from None
