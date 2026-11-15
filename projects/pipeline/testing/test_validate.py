import json
import shutil
from pathlib import Path

import pytest

from pipeline.validate import main, validate_dir, validate_storage

CONTRACT = Path(__file__).resolve().parents[2] / "contract"


@pytest.fixture
def data(tmp_path: Path) -> Path:
  shutil.copytree(CONTRACT / "examples" / "mock-validated", tmp_path, dirs_exist_ok=True)
  return tmp_path


@pytest.fixture
def storage(tmp_path: Path) -> Path:
  shutil.copytree(CONTRACT / "examples", tmp_path, dirs_exist_ok=True)
  return tmp_path


def edit(folder: Path, name: str, change) -> None:
  path = folder / name
  obj = json.loads(path.read_text(encoding="utf-8"))
  change(obj)
  path.write_text(json.dumps(obj), encoding="utf-8")


def test_examples_are_valid(data: Path):
  assert validate_dir(data) == []


def test_variant_without_before_after_is_valid(data: Path):
  shutil.copy(CONTRACT / "shared" / "no-toggle" / "meta.json", data / "meta.json")
  (data / "overlay_before.png").unlink()
  (data / "overlay_after.png").unlink()
  assert validate_dir(data) == []


def test_missing_file_is_reported(data: Path):
  (data / "graph.json").unlink()
  assert "graph.json: file is missing" in validate_dir(data)


def test_unknown_field_is_rejected(data: Path):
  edit(data, "graph.json", lambda g: g.update(extra=1))
  assert any("graph.json" in e and "extra" in e for e in validate_dir(data))


def test_passes_must_share_track(data: Path):
  edit(data, "meta.json", lambda m: m["passes"]["after"].update(track=2))
  assert any("track" in e for e in validate_dir(data))


def test_unknown_edge_in_scenario(data: Path):
  edit(data, "scenarios.json", lambda s: s["candidates"][0]["edge_ids"].append("e99"))
  assert any("unknown edge e99" in e for e in validate_dir(data))


def test_isolated_must_be_affected(data: Path):
  edit(data, "scenarios.json", lambda s: s["candidates"][0]["isolated_community_ids"].append("c5"))
  assert any("subset" in e for e in validate_dir(data))


def test_missing_overlay_file(data: Path):
  (data / "overlay_change.png").unlink()
  assert any("overlay_change.png does not exist" in e for e in validate_dir(data))


def test_rain_must_cover_period(data: Path):
  rows = (data / "rain.csv").read_text(encoding="utf-8").splitlines()
  (data / "rain.csv").write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
  assert any("must cover" in e for e in validate_dir(data))


def test_change_layer_is_optional(data: Path):
  def drop(m):
    m.pop("passes")
    m.pop("overlays")

  edit(data, "meta.json", drop)
  edit(data, "change.geojson", lambda c: c.update(features=[]))
  edit(data, "scenarios.json", lambda s: [c.update(zone_ids=[], mean_delta_db=None) for c in s["candidates"]])
  assert validate_dir(data) == []


def test_inv_05_removed_exposure_fields_are_rejected(data: Path):
  for field in ("soil_moisture_pctl", "radar_evidence"):
    edit(data, "scenarios.json", lambda s: s["candidates"][0]["exposure"].update({field: None}))
    assert any(field in e for e in validate_dir(data))
    edit(data, "scenarios.json", lambda s: s["candidates"][0]["exposure"].pop(field))


@pytest.mark.parametrize("name", ["meta.json", "graph.json", "scenarios.json", "change.geojson"])
def test_inv_01_wrong_schema_version_names_the_file(data: Path, name: str):
  edit(data, name, lambda o: o.update(schema_version="0.2"))
  assert any(e.startswith(name) and "schema_version" in e for e in validate_dir(data))


def test_inv_01_areas_wrong_schema_version(storage: Path):
  edit(storage, "areas.json", lambda o: o.update(schema_version="0.2"))
  assert any(e.startswith("areas.json") and "schema_version" in e for e in validate_storage(storage))


@pytest.mark.parametrize("field", ["length_m", "suspect_isolated_community_ids"])
def test_inv_02_candidate_missing_field_is_reported(data: Path, field: str):
  edit(data, "scenarios.json", lambda s: s["candidates"][0].pop(field))
  assert any("scenarios.json" in e and field in e for e in validate_dir(data))


def test_inv_03_suspect_must_be_isolated(data: Path):
  edit(data, "scenarios.json", lambda s: s["candidates"][0]["suspect_isolated_community_ids"].append("c5"))
  errors = validate_dir(data)
  assert any("T-02" in e and "c5" in e and "suspect_isolated_community_ids" in e for e in errors)


def test_inv_10_areas_missing(storage: Path):
  (storage / "areas.json").unlink()
  assert "areas.json: file is missing" in validate_storage(storage)


def test_inv_10_areas_empty(storage: Path):
  edit(storage, "areas.json", lambda o: o.update(areas=[]))
  assert any(e.startswith("areas.json") for e in validate_storage(storage))


def test_inv_10_duplicate_area_id(storage: Path):
  edit(storage, "areas.json", lambda o: o["areas"][1].update(id="mock-validated"))
  assert any("areas.json" in e and "mock-validated" in e and "twice" in e for e in validate_storage(storage))


def test_inv_10_area_without_folder(storage: Path):
  shutil.rmtree(storage / "mock-unvalidated")
  assert any("mock-unvalidated" in e and "folder" in e for e in validate_storage(storage))


def test_inv_12_every_listed_zone_is_validated(storage: Path):
  (storage / "mock-unvalidated" / "graph.json").unlink()
  assert any("mock-unvalidated" in e and "graph.json: file is missing" in e for e in validate_storage(storage))


def test_inv_12_exit_code_is_non_zero_when_a_zone_fails(storage: Path, monkeypatch):
  (storage / "mock-unvalidated" / "graph.json").unlink()
  monkeypatch.setattr("sys.argv", ["validate", str(storage)])
  with pytest.raises(SystemExit) as exc:
    main()
  assert exc.value.code not in (0, None)


def test_acc_03_mock_has_suspect_candidate_and_marked_area():
  scen = json.loads((CONTRACT / "examples" / "mock-validated" / "scenarios.json").read_text(encoding="utf-8"))
  meta = json.loads((CONTRACT / "examples" / "mock-validated" / "meta.json").read_text(encoding="utf-8"))
  assert any(c["suspect_isolated_community_ids"] for c in scen["candidates"])
  assert "MOCK" in meta["area"]["name"]


def test_acc_04_two_zones_validate(storage: Path):
  areas = json.loads((storage / "areas.json").read_text(encoding="utf-8"))["areas"]
  assert sorted(a["validated"] for a in areas) == [False, True]
  assert validate_storage(storage) == []


def test_oversized_overlay_is_rejected(data: Path):
  (data / "overlay_change.png").write_bytes(b"0" * (2 * 1024 * 1024 + 1))
  assert any("is larger than" in e for e in validate_dir(data))


def test_change_geojson_is_optional(data: Path):
  (data / "change.geojson").unlink()
  edit(data, "scenarios.json", lambda s: [c.update(zone_ids=[], mean_delta_db=None) for c in s["candidates"]])
  assert validate_dir(data) == []
