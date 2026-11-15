from pathlib import Path

import pytest

from pipeline.area_config import ConfigError, load_zone
from test_area_config import DETECTION, VALID, make


# Boundaries the builder tests leave open: each pins one comparison in the loader.


def test_inv_04_rain_start_equal_to_end_is_valid(tmp_path: Path):
  text = VALID.replace('end = "2026-02-01"', 'end = "2026-01-01"')
  assert load_zone("test-zone", make(tmp_path, text)).rain_start == "2026-01-01"


@pytest.mark.parametrize("bbox", ["[-180, -90, 180, 90]", "[-84.30, 9.80, -84.30, 10.45]", "[-84.30, 9.80, -82.95, 9.80]"])
def test_inv_04_bbox_edges(tmp_path: Path, bbox: str):
  text = VALID.replace("[-84.30, 9.80, -82.95, 10.45]", bbox)
  if bbox.startswith("[-180"):
    assert load_zone("test-zone", make(tmp_path, text)).bbox == (-180, -90, 180, 90)
  else:
    with pytest.raises(ConfigError, match="bbox"):
      load_zone("test-zone", make(tmp_path, text))


@pytest.mark.parametrize("bbox", ["[-180.01, 9.8, -82.95, 10.45]", "[-84.3, 9.8, 180.01, 10.45]", "[-84.3, -90.01, -82.95, 10.45]", "[-84.3, 9.8, -82.95, 90.01]"])
def test_inv_04_bbox_just_outside_the_range(tmp_path: Path, bbox: str):
  with pytest.raises(ConfigError, match="bbox"):
    load_zone("test-zone", make(tmp_path, VALID.replace("[-84.30, 9.80, -82.95, 10.45]", bbox)))


@pytest.mark.parametrize("value", ["٢٠٢٦-٠١-٠١", "２０２６-０１-０１", "2026-01-01\n", " 2026-01-01"])
def test_inv_04_non_ascii_or_padded_dates_are_rejected(tmp_path: Path, value: str):
  text = VALID.replace('start = "2026-01-01"', f'start = "{value}"'.replace("\n", "\\n"))
  with pytest.raises(ConfigError, match="rain.start"):
    load_zone("test-zone", make(tmp_path, text))


def test_inv_03_unknown_key_in_an_alternate_is_named(tmp_path: Path):
  text = VALID.replace('{ name = "Ruta Y"', '{ colour = "red", name = "Ruta Y"')
  with pytest.raises(ConfigError, match="colour"):
    load_zone("test-zone", make(tmp_path, text))


def test_inv_03_unknown_key_in_detection_limits_is_named(tmp_path: Path):
  with pytest.raises(ConfigError, match="detection_limits.extra"):
    load_zone("test-zone", make(tmp_path, VALID + DETECTION + 'extra = 1\n'))


def test_inv_02_crlf_line_endings_load(tmp_path: Path):
  assert load_zone("test-zone", make(tmp_path, VALID.replace("\n", "\r\n"))).name == "Test Zone"
