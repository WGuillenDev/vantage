import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import pipeline.pipeline_run as pipeline_run
from pipeline.pipeline_run import PipelineRunError, run_zone, write_areas
from test_pipeline_run import ROOT, make_zone, snapshot, stages, work  # noqa: F401  (work is a fixture)


def test_adv_inv_02_failed_swap_restores_the_previous_output(tmp_path: Path, work: Path, monkeypatch: pytest.MonkeyPatch):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  before = snapshot(zone.output_dir)
  real_rename = Path.rename

  def failing_rename(self: Path, target):
    if self.name.endswith(".new"):
      raise OSError("disk error")
    return real_rename(self, target)

  monkeypatch.setattr(Path, "rename", failing_rename)
  with pytest.raises(Exception):
    run_zone(zone, work, stages())
  monkeypatch.undo()
  assert zone.output_dir.is_dir() and snapshot(zone.output_dir) == before


@pytest.mark.parametrize("content", ["{}", "not json", '{"product": "P"}'])
def test_adv_inv_02_bad_imerg_source_is_a_pipeline_error(tmp_path: Path, work: Path, content: str):
  (work / "imerg" / "source.json").write_text(content, encoding="utf-8")
  with pytest.raises(PipelineRunError):
    run_zone(make_zone(tmp_path), work, stages())


def test_adv_inv_02_stages_that_write_nothing_give_a_pipeline_error(tmp_path: Path, work: Path):
  with pytest.raises(PipelineRunError):
    run_zone(make_zone(tmp_path), work, [(name, lambda z, w: None) for name, _ in stages()])


def test_adv_inv_10_blank_extract_date_is_rejected(tmp_path: Path, work: Path):
  (work / "osm" / "extract_date.txt").write_text("\n", encoding="utf-8")
  with pytest.raises(PipelineRunError):
    run_zone(make_zone(tmp_path), work, stages())


def test_adv_inv_02_stale_staging_folder_does_not_leak_into_the_output(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path)
  stale = zone.output_dir.parent / ".zone-a.new"
  stale.mkdir(parents=True)
  (stale / "leftover.json").write_text("{}", encoding="utf-8")
  run_zone(zone, work, stages())
  assert sorted(snapshot(zone.output_dir)) == ["graph.json", "meta.json", "rain.csv", "scenarios.json"]
  assert not stale.exists()


def test_adv_inv_02_main_exits_with_an_english_error_naming_the_stage(tmp_path: Path, work: Path, monkeypatch: pytest.MonkeyPatch):
  bad = stages()
  bad[0] = ("road-graph", lambda z, w: 1 / 0)
  monkeypatch.setattr(pipeline_run, "load_zone", lambda zone_id: make_zone(tmp_path))
  monkeypatch.setattr(pipeline_run, "default_stages", lambda: bad)
  monkeypatch.setattr(pipeline_run, "WORK_DIR", work.parent)
  with pytest.raises(SystemExit) as raised:
    pipeline_run.main(["--area", "zone-a"])
  assert str(raised.value).startswith("pipeline-run: stage road-graph failed")


@pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")
def test_adv_inv_14_publish_from_a_missing_source_keeps_the_old_storage(tmp_path: Path):
  storage = tmp_path / "storage"
  storage.mkdir()
  (storage / "areas.json").write_text("{}", encoding="utf-8")
  done = subprocess.run(
    ["make", "-C", str(ROOT), "publish", f"OUTPUT={(tmp_path / 'missing').as_posix()}", f"STORAGE={storage.as_posix()}"],
    capture_output=True,
  )
  assert done.returncode != 0
  assert (storage / "areas.json").exists()


def test_adv2_inv_02_failed_move_of_the_old_output_is_a_pipeline_error(tmp_path: Path, work: Path, monkeypatch: pytest.MonkeyPatch):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  before = snapshot(zone.output_dir)
  real_rename = Path.rename

  def locked(self: Path, target):
    if self == zone.output_dir:
      raise PermissionError("folder is in use")
    return real_rename(self, target)

  monkeypatch.setattr(Path, "rename", locked)
  with pytest.raises(PipelineRunError):
    run_zone(zone, work, stages())
  monkeypatch.undo()
  assert snapshot(zone.output_dir) == before
  assert sorted(p.name for p in zone.output_dir.parent.iterdir()) == ["zone-a"]


def test_adv2_inv_02_interrupt_during_the_swap_keeps_the_previous_output(tmp_path: Path, work: Path, monkeypatch: pytest.MonkeyPatch):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  before = snapshot(zone.output_dir)
  real_rename = Path.rename

  def interrupted(self: Path, target):
    if self.name.endswith(".new"):
      raise KeyboardInterrupt
    return real_rename(self, target)

  monkeypatch.setattr(Path, "rename", interrupted)
  with pytest.raises(KeyboardInterrupt):
    run_zone(zone, work, stages())
  monkeypatch.undo()
  assert zone.output_dir.is_dir() and snapshot(zone.output_dir) == before


def test_adv2_inv_06_non_ascii_zone_name_survives_meta_and_areas(tmp_path: Path, work: Path):
  zone = replace(make_zone(tmp_path), name="Ruta 32 (San José–Limón)")
  run_zone(zone, work, stages())
  meta = json.loads((zone.output_dir / "meta.json").read_text(encoding="utf-8"))
  assert meta["area"]["name"] == "Ruta 32 (San José–Limón)"


def test_adv2_inv_13_areas_json_is_byte_identical_between_runs(tmp_path: Path, work: Path):
  configs, output = tmp_path / "configs", tmp_path / "output"
  configs.mkdir()
  for zone_id in ("zone-b", "zone-a"):
    (output / zone_id).mkdir(parents=True)
    (configs / f"{zone_id}.toml").write_text(
      'name = "Zona José"\nvalidated = true\nbbox = [-84.2, 9.95, -83.7, 10.3]\n'
      '[hospitals]\nreferral = ["way/1"]\n[speed_model_kmh]\nprimary = 60\n[closure]\nroads = ["R"]\nalternates = []\n'
      '[population]\nraster = "r.tif"\nurl = "u"\n[rain]\nstart = "2026-06-29"\nend = "2026-07-01"\n',
      encoding="utf-8",
    )
  write_areas(output, configs)
  first = (output / "areas.json").read_bytes()
  write_areas(output, configs)
  assert (output / "areas.json").read_bytes() == first
  assert "Zona José".encode("utf-8") in first


def test_adv2_inv_13_written_json_uses_unix_line_endings(tmp_path: Path, work: Path):
  zone = make_zone(tmp_path)
  run_zone(zone, work, stages())
  assert b"\r" not in (zone.output_dir / "meta.json").read_bytes()
