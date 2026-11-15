import filecmp
import json
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from pipeline.area_config import Zone
from pipeline.pipeline_run import STAGE_NAMES, PipelineRunError, default_stages, run_zone, write_areas
from pipeline.validate import _schema_errors, validate_dir

CONTRACT = Path(__file__).resolve().parents[2] / "contract"
ROOT = Path(__file__).resolve().parents[3]
MOCK = CONTRACT / "examples" / "mock-validated"
LIMITS = {"min_detectable_area_ha": 1, "min_delta_db": 5, "note": "test limits"}


def make_zone(tmp_path: Path, zone_id: str = "zone-a", limits: dict | None = LIMITS) -> Zone:
  return Zone(
    id=zone_id, name="Test zone", validated=True, bbox=(-84.2, 9.95, -83.7, 10.3), referral_hospitals=("way/1",),
    speed_model_kmh={"primary": 60.0}, closure_roads=("R",), closure_alternates=(), population_raster="r.tif", population_url="u",
    rain_start="2026-06-29", rain_end="2026-07-01", detection_limits=limits, output_dir=tmp_path / "output" / zone_id,
  )


@pytest.fixture
def work(tmp_path: Path) -> Path:
  folder = tmp_path / "work" / "zone-a"
  (folder / "imerg").mkdir(parents=True)
  (folder / "osm").mkdir()
  (folder / "imerg" / "source.json").write_text(json.dumps({"product": "GPM_3IMERGDL", "version": "V07"}), encoding="utf-8")
  (folder / "osm" / "extract_date.txt").write_text("2026-11-14\n", encoding="utf-8")
  return folder


def graph_stage(population: int | None = None):
  def stage(zone, work_dir):
    graph = json.loads((MOCK / "graph.json").read_text(encoding="utf-8"))
    for community in graph["communities"]:
      community["population"] = population
    (zone.output_dir / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
  return stage


def scenarios_stage(zone, work_dir):
  scenarios = json.loads((MOCK / "scenarios.json").read_text(encoding="utf-8"))
  for candidate in scenarios["candidates"]:
    candidate.update(zone_ids=[], mean_delta_db=None)
  (zone.output_dir / "scenarios.json").write_text(json.dumps(scenarios), encoding="utf-8")


def rain_stage(zone, work_dir):
  (zone.output_dir / "rain.csv").write_text("date,precip_mm\n2026-06-29,0.0\n2026-06-30,1.2\n2026-07-01,0.0\n", encoding="utf-8")


def stages(calls: list | None = None, population: int | None = None):
  real = {"road-graph": graph_stage(population), "impact-scoring": scenarios_stage, "rain-context": rain_stage}

  def named(name):
    def stage(zone, work_dir):
      if calls is not None:
        calls.append(name)
      real.get(name, lambda z, w: None)(zone, work_dir)
    return stage

  return [(name, named(name)) for name in STAGE_NAMES]


def snapshot(folder: Path) -> dict[str, bytes]:
  return {p.name: p.read_bytes() for p in folder.iterdir()}


def test_inv_04_stages_run_in_the_fixed_order(tmp_path: Path, work: Path):
  calls: list[str] = []
  run_zone(make_zone(tmp_path), work, stages(calls))
  assert calls == ["road-graph", "population-data", "closure-units", "impact-scoring", "rain-context"]


def test_inv_04_default_stages_follow_the_order_or_name_the_missing_one():
  assert STAGE_NAMES == ("road-graph", "population-data", "closure-units", "impact-scoring", "rain-context")
  try:
    names = [name for name, _ in default_stages()]
  except PipelineRunError as exc:
    assert "not implemented yet" in str(exc)
  else:
    assert names == list(STAGE_NAMES)


def test_inv_01_run_leaves_the_four_files_and_the_validator_passes(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  assert sorted(snapshot(zone.output_dir)) == ["graph.json", "meta.json", "rain.csv", "scenarios.json"]
  assert validate_dir(zone.output_dir) == []


def test_inv_02_failing_stage_keeps_the_previous_output(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  before = snapshot(zone.output_dir)
  bad = stages()
  bad[3] = ("impact-scoring", lambda z, w: (_ for _ in ()).throw(ValueError("boom")))
  with pytest.raises(PipelineRunError, match="stage impact-scoring failed: boom"):
    run_zone(zone, work, bad)
  assert snapshot(zone.output_dir) == before
  assert sorted(p.name for p in zone.output_dir.parent.iterdir()) == ["zone-a"]


def test_inv_02_validator_failure_keeps_the_previous_output(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  before = snapshot(zone.output_dir)
  bad = stages()
  bad[4] = ("rain-context", lambda z, w: (z.output_dir / "rain.csv").write_text("date,precip_mm\n", encoding="utf-8"))
  with pytest.raises(PipelineRunError, match="validator failed: .*rain.csv"):
    run_zone(zone, work, bad)
  assert snapshot(zone.output_dir) == before


def test_inv_02_first_run_failure_leaves_no_zone_folder(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path)
  bad = stages()
  bad[0] = ("road-graph", lambda z, w: 1 / 0)
  with pytest.raises(PipelineRunError, match="stage road-graph failed"):
    run_zone(zone, work, bad)
  assert not zone.output_dir.exists()


def test_inv_05_run_makes_no_network_request(tmp_path: Path, work: Path, monkeypatch: pytest.MonkeyPatch):
  def refuse(*args, **kwargs):
    raise AssertionError("network request attempted")

  monkeypatch.setattr(socket.socket, "connect", refuse)
  monkeypatch.setattr(socket, "getaddrinfo", refuse)
  run_zone(make_zone(tmp_path), work, stages())


def test_inv_06_meta_copies_the_zone_and_the_imerg_source(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  meta = json.loads((zone.output_dir / "meta.json").read_text(encoding="utf-8"))
  assert meta["area"] == {"name": "Test zone", "bbox": [-84.2, 9.95, -83.7, 10.3]}
  assert meta["rain"] == {"product": "GPM_3IMERGDL", "version": "V07", "start": "2026-06-29", "end": "2026-07-01", "aggregation": "area_mean"}
  assert meta["speed_model_kmh"] == {"primary": 60.0}
  assert meta["detection_limits"] == LIMITS
  assert meta["schema_version"] == "0.3" and meta["files"] == {"rain_csv_schema": "0.1"}
  assert "passes" not in meta and "overlays" not in meta


def test_inv_06_detection_limits_absent_when_the_zone_has_none(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path, limits=None)
  run_zone(zone, work, stages())
  assert "detection_limits" not in json.loads((zone.output_dir / "meta.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("population, worldpop", [(None, False), (120, True)])
def test_inv_10_attributions(tmp_path: Path, work: Path, population, worldpop):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages(population=population))
  lines = json.loads((zone.output_dir / "meta.json").read_text(encoding="utf-8"))["attributions"]
  assert "© OpenStreetMap contributors (ODbL), extract 2026-11-14" in lines
  assert "IMERG Late (NASA GPM)" in lines
  assert any("WorldPop" in line for line in lines) is worldpop
  assert not any("NISAR" in line for line in lines)


def test_inv_11_areas_lists_every_zone_folder_by_id(tmp_path: Path):
  configs = tmp_path / "configs"
  configs.mkdir()
  output = tmp_path / "output"
  for zone_id, name, validated in (("zone-b", "Beta", "false"), ("zone-a", "Alpha", "true")):
    (output / zone_id).mkdir(parents=True)
    (configs / f"{zone_id}.toml").write_text(
      f'name = "{name}"\nvalidated = {validated}\nbbox = [-84.2, 9.95, -83.7, 10.3]\n'
      '[hospitals]\nreferral = ["way/1"]\n[speed_model_kmh]\nprimary = 60\n[closure]\nroads = ["R"]\nalternates = []\n'
      '[population]\nraster = "r.tif"\nurl = "u"\n[rain]\nstart = "2026-06-29"\nend = "2026-07-01"\n',
      encoding="utf-8",
    )
  (output / ".hidden.new").mkdir()
  write_areas(output, configs)
  areas = json.loads((output / "areas.json").read_text(encoding="utf-8"))
  assert areas["areas"] == [
    {"id": "zone-a", "name": "Alpha", "bbox": [-84.2, 9.95, -83.7, 10.3], "validated": True},
    {"id": "zone-b", "name": "Beta", "bbox": [-84.2, 9.95, -83.7, 10.3], "validated": False},
  ]
  assert _schema_errors("areas.json", areas, "areas.schema.json") == []


def test_inv_13_two_runs_are_identical_except_generated_at(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  first = tmp_path / "first"
  shutil.copytree(zone.output_dir, first)
  run_zone(zone, work, stages())
  for name in ("graph.json", "scenarios.json", "rain.csv"):
    assert filecmp.cmp(first / name, zone.output_dir / name, shallow=False)

  def without_time(folder: Path) -> dict:
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    meta.pop("generated_at")
    return meta

  assert without_time(first) == without_time(zone.output_dir)


@pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")
@pytest.mark.parametrize("target, source_var", [("publish", "OUTPUT"), ("mock", "EXAMPLES")])
def test_inv_14_publish_and_mock_make_storage_an_exact_copy(tmp_path: Path, target: str, source_var: str):
  source, storage = tmp_path / "source", tmp_path / "storage"
  (source / "zone-a").mkdir(parents=True)
  (source / "areas.json").write_text("{}", encoding="utf-8")
  (source / "zone-a" / "meta.json").write_text("{}", encoding="utf-8")
  storage.mkdir()
  (storage / "stale.json").write_text("old", encoding="utf-8")
  subprocess.run(
    ["make", "-C", str(ROOT), target, f"{source_var}={source.as_posix()}", f"STORAGE={storage.as_posix()}"],
    check=True, capture_output=True,
  )

  def listing(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))

  assert listing(storage) == listing(source) == ["areas.json", "zone-a", "zone-a/meta.json"]
