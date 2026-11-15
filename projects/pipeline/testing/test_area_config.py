import shutil
from pathlib import Path

import pytest

from pipeline import area_config
from pipeline.area_config import ConfigError, load_zone, main

PIPELINE = Path(__file__).resolve().parents[1]

VALID = """\
name = "Test Zone"
validated = false
bbox = [-84.30, 9.80, -82.95, 10.45]

[hospitals]
referral = ["way/1"]

[speed_model_kmh]
trunk = 60
primary = 50

[closure]
roads = ["Ruta X"]
alternates = [
  { name = "Ruta Y", vehicles = "light" },
]

[population]
raster = "work/r.tif"
url = "https://example.org/r.tif"

[rain]
start = "2026-01-01"
end = "2026-02-01"
"""

DETECTION = """
[detection_limits]
min_detectable_area_ha = 1
min_delta_db = 5
note = "GCOV 10 m"
"""


def make(tmp_path: Path, text: str = VALID, zone_id: str = "test-zone") -> Path:
  configs = tmp_path / "configs"
  configs.mkdir(exist_ok=True)
  (configs / f"{zone_id}.toml").write_text(text, encoding="utf-8")
  return configs


def test_inv_01_zone_carries_the_file_values(tmp_path: Path):
  zone = load_zone("test-zone", make(tmp_path, VALID + DETECTION))
  assert zone.id == "test-zone"
  assert zone.name == "Test Zone"
  assert zone.validated is False
  assert zone.bbox == (-84.30, 9.80, -82.95, 10.45)
  assert zone.referral_hospitals == ("way/1",)
  assert zone.speed_model_kmh == {"trunk": 60, "primary": 50}
  assert zone.population_raster == "work/r.tif"
  assert zone.rain_start == "2026-01-01" and zone.rain_end == "2026-02-01"
  assert zone.closure_roads == ("Ruta X",)
  assert zone.closure_alternates == (("Ruta Y", "light"),)
  assert zone.detection_limits == {"min_detectable_area_ha": 1, "min_delta_db": 5, "note": "GCOV 10 m"}


def test_inv_01_detection_limits_are_optional(tmp_path: Path):
  assert load_zone("test-zone", make(tmp_path)).detection_limits is None


def test_inv_10_output_folder_is_output_id_and_nothing_is_written(tmp_path: Path):
  zone = load_zone("test-zone", make(tmp_path))
  assert zone.output_dir == tmp_path / "output" / "test-zone"
  assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
  ("old", "new", "key"),
  [
    ('name = "Test Zone"\n', "", "name"),
    ('name = "Test Zone"', 'name = ""', "name"),
    ("validated = false\n", "", "validated"),
    ("bbox = [-84.30, 9.80, -82.95, 10.45]\n", "", "bbox"),
    ('[hospitals]\nreferral = ["way/1"]\n', "", "hospitals"),
    ('referral = ["way/1"]', "referral = []", "hospitals.referral"),
    ('referral = ["way/1"]\n', "", "hospitals.referral"),
    ("trunk = 60\nprimary = 50\n", "", "speed_model_kmh"),
    ('[closure]\nroads = ["Ruta X"]\n', "[closure]\n", "closure.roads"),
    ('roads = ["Ruta X"]', "roads = []", "closure.roads"),
    ('alternates = [\n  { name = "Ruta Y", vehicles = "light" },\n]\n', "", "closure.alternates"),
    ('raster = "work/r.tif"\n', "", "population.raster"),
    ('url = "https://example.org/r.tif"\n', "", "population.url"),
    ('start = "2026-01-01"\n', "", "rain.start"),
    ('end = "2026-02-01"\n', "", "rain.end"),
    ('{ name = "Ruta Y", vehicles = "light" }', '{ vehicles = "light" }', "closure.alternates"),
  ],
)
def test_inv_02_missing_or_empty_key_names_file_and_key(tmp_path: Path, old: str, new: str, key: str):
  assert old in VALID
  configs = make(tmp_path, VALID.replace(old, new))
  with pytest.raises(ConfigError) as err:
    load_zone("test-zone", configs)
  assert "test-zone.toml" in str(err.value) and key in str(err.value)
  assert not (tmp_path / "output").exists()


def test_inv_02_empty_alternates_list_is_allowed(tmp_path: Path):
  text = VALID.replace('  { name = "Ruta Y", vehicles = "light" },\n', "")
  assert load_zone("test-zone", make(tmp_path, text)).closure_alternates == ()


@pytest.mark.parametrize(
  ("text", "key"),
  [
    ('extra = 1\n' + VALID, "extra"),
    (VALID.replace("[rain]", "[rain]\nunit = 1"), "rain.unit"),
    (VALID.replace('{ name = "Ruta Y"', '{ colour = "red", name = "Ruta Y"'), "closure.alternates"),
    (VALID + DETECTION + 'extra = 1\n', "detection_limits.extra"),
  ],
)
def test_inv_03_unknown_key_is_rejected(tmp_path: Path, text: str, key: str):
  with pytest.raises(ConfigError) as err:
    load_zone("test-zone", make(tmp_path, text))
  assert key in str(err.value) and "test-zone.toml" in str(err.value)


@pytest.mark.parametrize(
  ("old", "new", "key"),
  [
    ("[-84.30, 9.80, -82.95, 10.45]", "[-84.30, 9.80, -82.95]", "bbox"),
    ("[-84.30, 9.80, -82.95, 10.45]", '[-84.30, 9.80, -82.95, "n"]', "bbox"),
    ("[-84.30, 9.80, -82.95, 10.45]", "[-82.95, 9.80, -84.30, 10.45]", "bbox"),
    ("[-84.30, 9.80, -82.95, 10.45]", "[-84.30, 10.45, -82.95, 9.80]", "bbox"),
    ("[-84.30, 9.80, -82.95, 10.45]", "[-84.30, 9.80, 190, 10.45]", "bbox"),
    ("[-84.30, 9.80, -82.95, 10.45]", "[-84.30, -95, -82.95, 10.45]", "bbox"),
    ("[-84.30, 9.80, -82.95, 10.45]", "[nan, 9.80, -82.95, 10.45]", "bbox"),
    ("[-84.30, 9.80, -82.95, 10.45]", "[true, 9.80, -82.95, 10.45]", "bbox"),
    ('start = "2026-01-01"', 'start = "01/01/2026"', "rain.start"),
    ('start = "2026-01-01"', 'start = "20260101"', "rain.start"),
    ('start = "2026-01-01"', "start = 2026-01-01", "rain.start"),
    ('end = "2026-02-01"', 'end = "2026-02-30"', "rain.end"),
    ('start = "2026-01-01"', 'start = "2026-03-01"', "rain"),
    ("trunk = 60", "trunk = 0", "speed_model_kmh.trunk"),
    ("trunk = 60", "trunk = -5", "speed_model_kmh.trunk"),
    ("trunk = 60", 'trunk = "fast"', "speed_model_kmh.trunk"),
    ("validated = false", 'validated = "no"', "validated"),
    ('vehicles = "light"', 'vehicles = "bus"', "closure.alternates"),
  ],
)
def test_inv_04_invalid_value_names_the_key(tmp_path: Path, old: str, new: str, key: str):
  assert old in VALID
  with pytest.raises(ConfigError) as err:
    load_zone("test-zone", make(tmp_path, VALID.replace(old, new)))
  assert key in str(err.value) and "test-zone.toml" in str(err.value)


@pytest.mark.parametrize("bad", ["Bad", "bad_id", "-bad", "bad-", "bad--id", "ba d", "bad.id", "ñu", ""])
def test_inv_04_invalid_zone_id(tmp_path: Path, bad: str):
  configs = make(tmp_path)
  with pytest.raises(ConfigError) as err:
    load_zone(bad, configs)
  assert "zone id" in str(err.value)


@pytest.mark.parametrize(
  "block",
  [
    "[detection_limits]\nmin_detectable_area_ha = 0\nmin_delta_db = 5\nnote = 'x'\n",
    "[detection_limits]\nmin_detectable_area_ha = 1\nmin_delta_db = -1\nnote = 'x'\n",
    "[detection_limits]\nmin_detectable_area_ha = 1\nmin_delta_db = 5\nnote = ''\n",
    "[detection_limits]\nmin_detectable_area_ha = 1\nmin_delta_db = 5\n",
  ],
)
def test_inv_04_detection_limits_are_validated_when_present(tmp_path: Path, block: str):
  with pytest.raises(ConfigError, match="detection_limits"):
    load_zone("test-zone", make(tmp_path, VALID + "\n" + block))


def test_inv_04_malformed_toml_names_the_file(tmp_path: Path):
  with pytest.raises(ConfigError, match="test-zone.toml"):
    load_zone("test-zone", make(tmp_path, "name = "))


def test_inv_07_unknown_area_lists_available_ids(tmp_path: Path):
  configs = make(tmp_path)
  make(tmp_path, VALID, "other-zone")
  with pytest.raises(ConfigError) as err:
    load_zone("missing", configs)
  assert "missing" in str(err.value) and "other-zone, test-zone" in str(err.value)


def test_inv_07_main_exits_non_zero_with_the_message(capsys):
  with pytest.raises(SystemExit) as err:
    main(["--area", "no-such-zone"])
  assert err.value.code not in (0, None)
  assert "no-such-zone" in str(err.value.code) and "ruta-32" in str(err.value.code)


def test_inv_02_main_requires_area():
  with pytest.raises(SystemExit) as err:
    main([])
  assert err.value.code != 0


def test_inv_02_main_exits_non_zero_on_invalid_config(tmp_path: Path, monkeypatch):
  monkeypatch.setattr(area_config, "CONFIGS_DIR", make(tmp_path, VALID.replace('name = "Test Zone"\n', "")))
  with pytest.raises(SystemExit) as err:
    main(["--area", "test-zone"])
  assert "name" in str(err.value.code)


def test_acc_01_ruta_32_zone():
  zone = load_zone("ruta-32", PIPELINE / "configs")
  assert zone.id == "ruta-32"
  assert zone.validated is False
  assert zone.output_dir == PIPELINE / "output" / "ruta-32"


def test_acc_01_main_runs_for_ruta_32(capsys):
  main(["--area", "ruta-32"])
  assert "ruta-32" in capsys.readouterr().out


def test_acc_02_another_zone_carries_its_own_values(tmp_path: Path):
  configs = tmp_path / "configs"
  configs.mkdir()
  source = PIPELINE / "configs" / "ruta-32.toml"
  before = source.read_bytes()
  swaps = {"name = ": 'name = "Other"', "bbox = ": "bbox = [-80.0, 8.0, -79.0, 9.0]"}
  lines = [next((v for k, v in swaps.items() if l.startswith(k)), l) for l in source.read_text(encoding="utf-8").splitlines()]
  (configs / "other-zone.toml").write_text("\n".join(lines), encoding="utf-8")
  zone = load_zone("other-zone", configs)
  assert (zone.id, zone.name, zone.bbox) == ("other-zone", "Other", (-80.0, 8.0, -79.0, 9.0))
  assert source.read_bytes() == before
  shutil.rmtree(configs)


@pytest.mark.parametrize("speed", ["inf", "-inf", "nan"])
def test_inv_04_speed_must_be_finite(tmp_path: Path, speed: str):
  with pytest.raises(ConfigError, match="speed_model_kmh.trunk"):
    load_zone("test-zone", make(tmp_path, VALID.replace("trunk = 60", f"trunk = {speed}")))


def test_inv_04_road_class_name_must_not_be_empty(tmp_path: Path):
  with pytest.raises(ConfigError, match="speed_model_kmh"):
    load_zone("test-zone", make(tmp_path, VALID.replace("trunk = 60", '"" = 60')))


def test_inv_04_detection_limits_must_be_finite(tmp_path: Path):
  block = "\n[detection_limits]\nmin_detectable_area_ha = inf\nmin_delta_db = 5\nnote = 'x'\n"
  with pytest.raises(ConfigError, match="detection_limits.min_detectable_area_ha"):
    load_zone("test-zone", make(tmp_path, VALID + block))


def test_inv_07_only_loadable_ids_are_listed(tmp_path: Path):
  configs = make(tmp_path)
  for bad in ("Bad_Name", "worse name", "-x"):
    make(tmp_path, VALID, bad)
  (configs / "dir-zone.toml").mkdir()
  with pytest.raises(ConfigError) as err:
    load_zone("missing", configs)
  assert str(err.value).endswith("available zones: test-zone")


def test_inv_07_a_file_that_differs_only_by_case_does_not_match(tmp_path: Path):
  configs = make(tmp_path, VALID, "RUTA-32")
  with pytest.raises(ConfigError, match="available zones: none"):
    load_zone("ruta-32", configs)


def test_inv_07_a_folder_named_like_a_config_does_not_match(tmp_path: Path):
  configs = make(tmp_path)
  (configs / "dir-zone.toml").mkdir()
  with pytest.raises(ConfigError, match="dir-zone.toml"):
    load_zone("dir-zone", configs)


@pytest.mark.parametrize(
  ("old", "new", "key"),
  [
    ('["way/1"]', '["way/1", "way/1"]', "hospitals.referral"),
    ('["Ruta X"]', '["Ruta X", "Ruta X"]', "closure.roads"),
    ('  { name = "Ruta Y", vehicles = "light" },\n', '  { name = "Ruta Y", vehicles = "light" },\n  { name = "Ruta Y", vehicles = "freight" },\n', "closure.alternates"),
  ],
)
def test_inv_11_repeated_values_are_rejected(tmp_path: Path, old: str, new: str, key: str):
  assert old in VALID
  with pytest.raises(ConfigError) as err:
    load_zone("test-zone", make(tmp_path, VALID.replace(old, new)))
  assert key in str(err.value) and "test-zone.toml" in str(err.value)


def test_inv_12_byte_order_mark_and_crlf_are_accepted(tmp_path: Path):
  configs = tmp_path / "configs"
  configs.mkdir()
  (configs / "test-zone.toml").write_bytes(b"\xef\xbb\xbf" + VALID.replace("\n", "\r\n").encode("utf-8"))
  assert load_zone("test-zone", configs).name == "Test Zone"


def test_inv_13_invalid_utf8_names_the_file(tmp_path: Path):
  configs = tmp_path / "configs"
  configs.mkdir()
  (configs / "test-zone.toml").write_bytes(b'name = "\xff\xfe"\n')
  with pytest.raises(ConfigError, match="test-zone.toml"):
    load_zone("test-zone", configs)


def test_inv_13_unreadable_file_names_the_file(tmp_path: Path, monkeypatch):
  configs = make(tmp_path)

  def deny(self, *args, **kwargs):
    raise PermissionError("denied")

  monkeypatch.setattr(Path, "read_bytes", deny)
  with pytest.raises(ConfigError, match="test-zone.toml"):
    load_zone("test-zone", configs)
