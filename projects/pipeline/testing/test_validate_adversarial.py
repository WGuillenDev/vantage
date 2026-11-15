import json
import shutil
from pathlib import Path

import pytest

from pipeline.validate import main, validate_dir, validate_storage

CONTRACT = Path(__file__).resolve().parents[2] / "contract"


@pytest.fixture
def storage(tmp_path: Path) -> Path:
  shutil.copytree(CONTRACT / "examples", tmp_path, dirs_exist_ok=True)
  return tmp_path


def edit(folder: Path, name: str, change) -> None:
  path = folder / name
  obj = json.loads(path.read_text(encoding="utf-8"))
  change(obj)
  path.write_text(json.dumps(obj), encoding="utf-8")


@pytest.mark.parametrize("bad", [0, -5])
def test_adversarial_length_must_be_positive(storage: Path, bad: int):
  edit(storage / "mock-validated", "scenarios.json", lambda s: s["candidates"][0].update(length_m=bad))
  assert any("length_m" in e for e in validate_storage(storage))


def test_adversarial_area_id_cannot_escape_storage(storage: Path):
  edit(storage, "areas.json", lambda o: o["areas"][0].update(id="../contract"))
  assert any(e.startswith("areas.json") for e in validate_storage(storage))


@pytest.mark.parametrize("content", [b"[]", b"{not json", b""])
def test_adversarial_malformed_areas_is_an_error_not_a_crash(storage: Path, content: bytes):
  (storage / "areas.json").write_bytes(content)
  assert validate_storage(storage)


def test_adversarial_rain_row_with_extra_column_is_an_error_not_a_crash(storage: Path):
  path = storage / "mock-validated" / "rain.csv"
  lines = path.read_text(encoding="utf-8").splitlines()
  lines[1] += ",9,9"
  path.write_text("\n".join(lines) + "\n", encoding="utf-8")
  assert any("rain.csv" in e for e in validate_dir(storage / "mock-validated"))


def test_adversarial_missing_storage_folder_exits_non_zero(tmp_path: Path, monkeypatch):
  monkeypatch.setattr("sys.argv", ["validate", str(tmp_path / "nope")])
  with pytest.raises(SystemExit) as exc:
    main()
  assert exc.value.code not in (0, None)


@pytest.mark.parametrize("name", ["graph.json", "scenarios.json", "meta.json"])
def test_adversarial_non_utf8_zone_file_is_an_error_not_a_crash(storage: Path, name: str):
  (storage / "mock-validated" / name).write_bytes(b"\xff\xfe\x00")
  assert any(name in e for e in validate_dir(storage / "mock-validated"))


def test_adversarial_non_utf8_areas_is_an_error_not_a_crash(storage: Path):
  (storage / "areas.json").write_bytes(b"\xff\xfe\x00bad")
  assert validate_storage(storage)


def test_adversarial_non_utf8_rain_is_an_error_not_a_crash(storage: Path):
  (storage / "mock-validated" / "rain.csv").write_bytes(b"date,precip_mm\n\xff\xfe,1\n")
  assert any("rain.csv" in e for e in validate_dir(storage / "mock-validated"))


@pytest.mark.parametrize("field", ["isolated_community_ids", "suspect_isolated_community_ids"])
def test_adversarial_duplicate_community_ids_are_rejected(storage: Path, field: str):
  def dup(s):
    c = s["candidates"][2]
    c[field] = c[field] + c[field]

  edit(storage / "mock-validated", "scenarios.json", dup)
  assert any("scenarios.json" in e and field in e for e in validate_dir(storage / "mock-validated"))


def test_adversarial_rain_date_that_is_not_a_calendar_day_is_an_error(storage: Path):
  path = storage / "mock-validated" / "rain.csv"
  lines = path.read_text(encoding="utf-8").splitlines()
  lines[1] = "2026-13-45," + lines[1].split(",")[1]
  path.write_text("\n".join(lines) + "\n", encoding="utf-8")
  assert any("valid ISO dates" in e for e in validate_dir(storage / "mock-validated"))


def test_adversarial_folder_not_listed_in_areas_is_ignored(storage: Path):
  shutil.copytree(storage / "mock-validated", storage / "stray-zone")
  (storage / "stray-zone" / "graph.json").unlink()
  assert validate_storage(storage) == []
