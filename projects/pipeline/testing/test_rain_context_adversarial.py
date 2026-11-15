import json
from datetime import date

import h5py
import numpy as np
import pytest
from test_rain_context import EDGES, START, days, make_zone, rain_rows, setup, units

from pipeline import rain_context
from pipeline.rain_context import RainContextError


def run_expecting_clean_error(zone, work_dir):
  """The stage must fail with its own error type: any other exception is a traceback at the trust boundary."""
  with pytest.raises(RainContextError):
    rain_context.run(zone, work_dir)
  assert not (zone.output_dir / "rain.csv").exists()


@pytest.mark.parametrize("bad", ["inf", "-inf"])
def test_inv_04_a_non_finite_cell_coordinate_is_a_clean_error(tmp_path, bad):
  zone, work_dir = setup(tmp_path, EDGES)
  path = work_dir / "imerg" / "cells.csv"
  path.write_text(path.read_text(encoding="utf-8").replace("0.15,0.15", f"{bad},0.15", 1), encoding="utf-8")
  run_expecting_clean_error(zone, work_dir)


def test_inv_04_a_cells_file_with_short_rows_is_a_clean_error(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  path = work_dir / "imerg" / "cells.csv"
  path.write_text(path.read_text(encoding="utf-8") + "2026-01-05,0.05\n", encoding="utf-8")
  run_expecting_clean_error(zone, work_dir)


def test_inv_04_the_same_cell_spelled_two_ways_is_a_duplicate(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  path = work_dir / "imerg" / "cells.csv"
  path.write_text(path.read_text(encoding="utf-8") + "2026-01-05,0.050,0.05,9\n", encoding="utf-8")
  run_expecting_clean_error(zone, work_dir)


def test_inv_04_a_missing_cells_file_is_a_clean_error(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  (work_dir / "imerg" / "cells.csv").unlink()
  run_expecting_clean_error(zone, work_dir)


def test_inv_01_running_twice_gives_the_same_files(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  rain_context.run(zone, work_dir)
  first = [(zone.output_dir / name).read_bytes() for name in ("rain.csv", "scenarios.json")]
  rain_context.run(zone, work_dir)
  assert [(zone.output_dir / name).read_bytes() for name in ("rain.csv", "scenarios.json")] == first


def test_inv_01_an_old_exposure_is_replaced_not_kept(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  path = zone.output_dir / "scenarios.json"
  data = json.loads(path.read_text(encoding="utf-8"))
  data["candidates"][0]["exposure"] = {"rain_mm_12d": 999.0}
  path.write_text(json.dumps(data), encoding="utf-8")
  rain_context.run(zone, work_dir)
  assert units(zone)["T-01"]["exposure"] == {"rain_mm_12d": 102.0}


# --- download against real HDF5 files (the part the spec tests cannot reach) ---

LON = np.array([-0.05, 0.05, 0.15, 0.25], dtype="float32")
LAT = np.array([0.05, 0.15, 0.25], dtype="float32")


class FakeGesDisc:
  """An earthaccess stand-in that serves one real HDF5 file per day, laid out like GPM_3IMERGDL: precipitation[time, lon, lat]."""

  def __init__(self, tmp_path, value):
    self.paths, self.granules = [], []
    for day in days():
      path = tmp_path / f"{day.isoformat()}.HDF5"
      with h5py.File(path, "w") as h5:
        h5["lon"], h5["lat"] = LON, LAT
        grid = np.array([[value(day, float(lo), float(la)) for la in LAT] for lo in LON], dtype="float32")
        h5["precipitation"] = grid[None, :, :]
      self.paths.append(str(path))
      self.granules.append({"umm": {"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": f"{day.isoformat()}T00:00:00.000Z"}}}})

  def login(self, strategy):
    return type("Auth", (), {"authenticated": True})()

  def search_data(self, **kwargs):
    return self.granules

  def open(self, granules):
    return self.paths


def asymmetric(day, lon, lat):
  """A value that tells lon from lat and day from day: any swapped axis shows."""
  return round((day - START).days + 1 + lon * 100 + lat * 1000, 2)


def test_inv_14_download_writes_the_cells_of_the_bbox_with_values_in_the_right_axis(tmp_path):
  zone = make_zone(tmp_path)  # bbox (0, 0, 0.1, 0.2): lon centre 0.05; lat centres 0.05 and 0.15
  rain_context.download(zone, tmp_path / "work" / "imerg", FakeGesDisc(tmp_path, asymmetric))
  rows = [line.split(",") for line in (tmp_path / "work" / "imerg" / "cells.csv").read_text(encoding="utf-8").splitlines()[1:]]
  assert {(r[1], r[2]) for r in rows} == {("0.05", "0.05"), ("0.05", "0.15")}
  first = {(r[1], r[2]): float(r[3]) for r in rows if r[0] == "2026-01-01"}
  assert first[("0.05", "0.05")] == pytest.approx(1 + 5 + 50, abs=1e-3)
  assert first[("0.05", "0.15")] == pytest.approx(1 + 5 + 150, abs=1e-3)
  source = json.loads((tmp_path / "work" / "imerg" / "source.json").read_text(encoding="utf-8"))
  assert source == {"product": "GPM_3IMERGDL", "version": "07", "start": "2026-01-01", "end": "2026-01-14"}


def test_inv_04_the_fill_value_becomes_a_blank_that_run_rejects_naming_the_day(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  bad = date(2026, 1, 6)
  fake = FakeGesDisc(tmp_path, lambda d, lo, la: -9999.9 if d == bad else 1.0)
  (work_dir / "imerg" / "cells.csv").unlink()
  rain_context.download(zone, work_dir / "imerg", fake)
  assert ",," not in (work_dir / "imerg" / "cells.csv").read_text(encoding="utf-8").splitlines()[0]
  with pytest.raises(RainContextError, match="2026-01-06"):
    rain_context.run(zone, work_dir)


def test_inv_14_download_then_run_round_trips(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  (work_dir / "imerg" / "cells.csv").unlink()
  rain_context.download(zone, work_dir / "imerg", FakeGesDisc(tmp_path, lambda d, lo, la: 2.0))
  rain_context.run(zone, work_dir)
  assert {r["precip_mm"] for r in rain_rows(zone)} == {"2.000"}
  assert units(zone)["T-01"]["exposure"] == {"rain_mm_12d": 24.0}


def test_inv_14_a_download_that_finds_no_granules_writes_nothing(tmp_path):
  zone = make_zone(tmp_path)
  fake = FakeGesDisc(tmp_path, asymmetric)
  fake.granules = []
  with pytest.raises(RainContextError):
    rain_context.download(zone, tmp_path / "work" / "imerg", fake)
  assert not (tmp_path / "work").exists()


def test_inv_14_a_bbox_outside_the_granule_is_a_clean_error_and_writes_nothing(tmp_path):
  zone = make_zone(tmp_path, bbox=(50.0, 50.0, 50.1, 50.1))
  with pytest.raises(RainContextError):
    rain_context.download(zone, tmp_path / "work" / "imerg", FakeGesDisc(tmp_path, asymmetric))
  assert not (tmp_path / "work").exists()


@pytest.mark.parametrize("error", [RuntimeError("HTTP 403 Forbidden"), RuntimeError("401 Client Error: Unauthorized"), RuntimeError("Forbidden")])
def test_inv_14_any_rejection_by_the_archive_says_how_to_authorize(tmp_path, error):
  zone = make_zone(tmp_path)
  fake = FakeGesDisc(tmp_path, asymmetric)
  fake.open = lambda granules: (_ for _ in ()).throw(error)
  with pytest.raises(RainContextError, match="NASA GESDISC DATA ARCHIVE"):
    rain_context.download(zone, tmp_path / "work" / "imerg", fake)
  assert not (tmp_path / "work").exists()
