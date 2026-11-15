import csv
import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from pipeline import rain_context
from pipeline.area_config import Zone
from pipeline.rain_context import RainContextError
from pipeline.validate import _check_graph, _check_rain, _check_scenarios, _schema_errors

# Cell centres sit on a 0.1 degree grid at x.x5, as IMERG's do. Lon centres 0.05 and 0.15, lat centres 0.05 and 0.15.
START, END = date(2026, 1, 1), date(2026, 1, 14)  # 14 days; the 12-day window is 3 Jan .. 14 Jan
CELLS = [("0.05", "0.05"), ("0.05", "0.15"), ("0.15", "0.05"), ("0.15", "0.15")]
BONUS = {("0.05", "0.05"): 0, ("0.05", "0.15"): 1, ("0.15", "0.05"): 10, ("0.15", "0.15"): 11}
BBOX = (0.0, 0.0, 0.1, 0.2)  # holds the centres of the two lon 0.05 cells only


def days(start: date = START, end: date = END):
  return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def default_value(day: date, cell: tuple[str, str]) -> str:
  return str((day - START).days + 1 + BONUS[cell])


def make_zone(tmp_path: Path, **changes) -> Zone:
  zone = Zone(
    id="fixture", name="Fixture", validated=False, bbox=BBOX, referral_hospitals=("way/1",),
    speed_model_kmh={"trunk": 60}, closure_roads=("Ruta 901",), closure_alternates=(),
    population_raster=str(tmp_path / "raster.tif"), population_url="https://example.invalid/raster.tif",
    rain_start=START.isoformat(), rain_end=END.isoformat(), detection_limits=None,
    output_dir=tmp_path / "output" / "fixture",
  )
  return replace(zone, **changes)


def write_cells(work_dir: Path, value=default_value, skip=(), cells=CELLS, period=(START, END)) -> None:
  folder = work_dir / "imerg"
  folder.mkdir(parents=True, exist_ok=True)
  with (folder / "cells.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["date", "cell_lon", "cell_lat", "precip_mm"])
    for day in days(*period):
      for lon, lat in cells:
        if (day.isoformat(), lon, lat) not in skip:
          writer.writerow([day.isoformat(), lon, lat, value(day, (lon, lat))])


def candidate(unit_id: str, edge_ids: list[str]) -> dict:
  return {
    "id": unit_id, "rank": 1, "source": "network_consequence", "length_m": 100, "edge_ids": edge_ids, "zone_ids": [],
    "mean_delta_db": None, "criticality": 0, "extra_time_s": None, "population_dependent": None,
    "affected_community_ids": [], "isolated_community_ids": [], "suspect_isolated_community_ids": [],
    "per_community": [], "alternates": [],
  }


def setup(tmp_path: Path, edges: dict[str, list[list[float]]], zone_changes=None) -> tuple[Zone, Path]:
  """A zone whose graph has one unit per entry of `edges` (edge id -> [lon, lat] vertices)."""
  zone = make_zone(tmp_path, **(zone_changes or {}))
  work_dir = tmp_path / "work"
  graph = {
    "schema_version": "0.3",
    "nodes": [{"id": "n1", "lon": 0.0, "lat": 0.0}, {"id": "n2", "lon": 0.1, "lat": 0.1}],
    "edges": [
      {"id": edge_id, "from": "n1", "to": "n2", "length_m": 100, "time_s": 10, "road": "Ruta 901", "oneway": False, "candidate_id": f"T-{n:02d}", "geometry": geometry}
      for n, (edge_id, geometry) in enumerate(edges.items(), start=1)
    ],
    "hospitals": [{"id": "h1", "name": "Hospital", "node": "n1"}],
    "communities": [{"id": "c1", "name": "Place", "node": "n2", "population": None}],
  }
  scenarios = {
    "schema_version": "0.3",
    "baseline": [{"community_id": "c1", "time_s": 10, "hospital_id": "h1"}],
    "candidates": [candidate(f"T-{n:02d}", [edge_id]) for n, edge_id in enumerate(edges, start=1)],
  }
  zone.output_dir.mkdir(parents=True)
  (zone.output_dir / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
  (zone.output_dir / "scenarios.json").write_text(json.dumps(scenarios, indent=2), encoding="utf-8")
  write_cells(work_dir)
  return zone, work_dir


# One unit inside the cell (0.05, 0.05), one crossing it and the cell (0.05, 0.15).
EDGES = {"e1": [[0.02, 0.02], [0.08, 0.08]], "e2": [[0.02, 0.02], [0.08, 0.18]]}


def rain_rows(zone: Zone) -> list[dict]:
  with (zone.output_dir / "rain.csv").open(newline="", encoding="utf-8") as f:
    return list(csv.DictReader(f))


def units(zone: Zone) -> dict[str, dict]:
  data = json.loads((zone.output_dir / "scenarios.json").read_text(encoding="utf-8"))
  return {c["id"]: c for c in data["candidates"]}


def test_inv_01_outputs_validate_and_scenarios_differ_only_in_exposure(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  before = json.loads((zone.output_dir / "scenarios.json").read_text(encoding="utf-8"))
  rain_context.run(zone, work_dir)
  after = json.loads((zone.output_dir / "scenarios.json").read_text(encoding="utf-8"))
  graph = json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))
  assert _schema_errors("scenarios.json", after, "scenarios.schema.json") == []
  assert _check_graph(graph) == [] and _check_scenarios(graph, after, set()) == []
  rows = rain_rows(zone)
  assert [_schema_errors("rain.csv", {"date": r["date"], "precip_mm": float(r["precip_mm"])}, "rain.schema.json") for r in rows] == [[]] * len(rows)
  assert _check_rain([{"date": r["date"]} for r in rows], {"start": START.isoformat(), "end": END.isoformat()}) == []
  for candidate_after in after["candidates"]:
    assert "exposure" in candidate_after
    del candidate_after["exposure"]
  assert after == before


def test_inv_02_one_row_per_day_ascending_without_gaps(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  write_cells(work_dir, period=(date(2025, 12, 20), date(2026, 1, 20)))  # the file may cover more days than the period
  rain_context.run(zone, work_dir)
  assert [r["date"] for r in rain_rows(zone)] == [d.isoformat() for d in days()]
  assert list(rain_rows(zone)[0]) == ["date", "precip_mm"]


def test_inv_03_daily_value_is_the_mean_of_cells_with_centre_inside_bbox(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  rain_context.run(zone, work_dir)
  # Day 1: the two lon 0.05 cells hold 1 and 2; the lon 0.15 cells (11 and 12) are outside the bbox.
  assert [float(r["precip_mm"]) for r in rain_rows(zone)[:2]] == [1.5, 2.5]


def test_inv_03_daily_value_rounds_half_up_to_three_decimals(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES, {"bbox": (0.0, 0.0, 0.1, 0.1)})  # one cell inside
  write_cells(work_dir, value=lambda d, c: "0.0005" if d == START else "0.0015")
  rain_context.run(zone, work_dir)
  assert [r["precip_mm"] for r in rain_rows(zone)[:2]] == ["0.001", "0.002"]


def test_inv_03_a_centre_on_the_bbox_edge_counts_as_inside(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES, {"bbox": (0.05, 0.05, 0.15, 0.15)})  # four centres, two of them on edges
  rain_context.run(zone, work_dir)
  assert float(rain_rows(zone)[0]["precip_mm"]) == 1 + sum(BONUS.values()) / 4


@pytest.mark.parametrize("problem", ["missing_cell", "empty_value", "not_a_number", "negative"])
def test_inv_04_a_bad_or_missing_day_fails_and_writes_nothing(tmp_path, problem):
  zone, work_dir = setup(tmp_path, EDGES)
  bad = date(2026, 1, 6)
  if problem == "missing_cell":
    write_cells(work_dir, skip={(bad.isoformat(), "0.15", "0.15")})
  else:
    bad_value = {"empty_value": "", "not_a_number": "n/a", "negative": "-9999.9"}[problem]
    write_cells(work_dir, value=lambda d, c: bad_value if (d == bad and c == ("0.15", "0.15")) else default_value(d, c))
  before = (zone.output_dir / "scenarios.json").read_bytes()
  with pytest.raises(RainContextError, match="2026-01-06"):
    rain_context.run(zone, work_dir)
  assert not (zone.output_dir / "rain.csv").exists()
  assert (zone.output_dir / "scenarios.json").read_bytes() == before


def test_inv_04_a_missing_day_of_the_whole_file_fails_naming_the_date(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  write_cells(work_dir, skip={("2026-01-14", lon, lat) for lon, lat in CELLS})
  with pytest.raises(RainContextError, match="2026-01-14"):
    rain_context.run(zone, work_dir)
  assert not (zone.output_dir / "rain.csv").exists()


def test_inv_04_a_period_shorter_than_the_window_fails_naming_the_period(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES, {"rain_start": "2026-01-05"})  # 5..14 is 10 days
  with pytest.raises(RainContextError, match="2026-01-05"):
    rain_context.run(zone, work_dir)
  assert not (zone.output_dir / "rain.csv").exists()


def test_inv_04_main_exits_non_zero_with_an_english_error(tmp_path, monkeypatch):
  zone, work_dir = setup(tmp_path, EDGES)
  write_cells(work_dir, skip={("2026-01-02", "0.05", "0.05")})
  monkeypatch.setattr(rain_context, "load_zone", lambda _id: zone)
  root = tmp_path / "work_root"
  root.mkdir()
  work_dir.rename(root / zone.id)  # main reads WORK_DIR / zone.id
  monkeypatch.setattr(rain_context, "WORK_DIR", root)
  with pytest.raises(SystemExit) as exit_info:
    rain_context.main(["--area", zone.id])
  assert "2026-01-02" in str(exit_info.value) and str(exit_info.value) != "0"


def test_inv_05_unit_value_is_the_mean_of_the_cells_touched_over_the_window(tmp_path):
  zone, work_dir = setup(tmp_path, EDGES)
  rain_context.run(zone, work_dir)
  # Window 3..14 Jan: the sum of day numbers is 102; the cell (0.05, 0.15) holds 1 more each day: 114.
  assert units(zone)["T-01"]["exposure"] == {"rain_mm_12d": 102.0}
  assert units(zone)["T-02"]["exposure"] == {"rain_mm_12d": 108.0}  # mean of 102 and 114


def test_inv_05_a_cell_counts_once_however_many_vertices_it_holds(tmp_path):
  zone, work_dir = setup(tmp_path, {"e1": [[0.01, 0.01], [0.02, 0.02], [0.03, 0.03], [0.04, 0.12]]})
  rain_context.run(zone, work_dir)
  assert units(zone)["T-01"]["exposure"] == {"rain_mm_12d": 108.0}


def test_inv_05_the_cell_boundary_is_inclusive_on_the_lower_edge_only(tmp_path):
  zone, work_dir = setup(tmp_path, {"e1": [[0.1, 0.05], [0.1, 0.05]]})  # lon 0.1 belongs to the cell centred 0.15
  rain_context.run(zone, work_dir)
  assert units(zone)["T-01"]["exposure"] == {"rain_mm_12d": 102.0 + 12 * 10}


def test_inv_05_unit_value_rounds_half_up_to_one_decimal(tmp_path):
  zone, work_dir = setup(tmp_path, {"e1": [[0.02, 0.02], [0.03, 0.03]]})
  write_cells(work_dir, value=lambda d, c: "0.25" if d == END else "0")
  rain_context.run(zone, work_dir)
  assert units(zone)["T-01"]["exposure"] == {"rain_mm_12d": 0.3}


def test_inv_05_only_the_last_12_days_count(tmp_path):
  zone, work_dir = setup(tmp_path, {"e1": [[0.02, 0.02], [0.03, 0.03]]})
  write_cells(work_dir, value=lambda d, c: "100" if d <= date(2026, 1, 2) else "1")
  rain_context.run(zone, work_dir)
  assert units(zone)["T-01"]["exposure"] == {"rain_mm_12d": 12.0}


def test_inv_05_a_unit_in_a_cell_without_data_fails_instead_of_a_partial_value(tmp_path):
  zone, work_dir = setup(tmp_path, {"e1": [[0.02, 0.02], [0.33, 0.33]]})  # the second vertex is in a cell the file lacks
  with pytest.raises(RainContextError, match="T-01"):
    rain_context.run(zone, work_dir)
  assert not (zone.output_dir / "rain.csv").exists()


class FakeEarthaccess:
  """Stands in for the earthaccess module; `outcome` decides where the download fails."""

  def __init__(self, authenticated: bool, search_error: Exception | None = None):
    self.authenticated, self.search_error = authenticated, search_error

  def login(self, strategy: str):
    if not self.authenticated:
      raise RuntimeError("no credentials")
    return type("Auth", (), {"authenticated": True})()

  def search_data(self, **kwargs):
    if self.search_error:
      raise self.search_error
    return []

  def open(self, granules):
    return []


@pytest.mark.parametrize("fake", [
  FakeEarthaccess(authenticated=False),
  FakeEarthaccess(authenticated=True, search_error=PermissionError("401 Unauthorized")),
], ids=["no_credentials", "application_not_authorized"])
def test_inv_14_download_without_authorization_fails_telling_how_and_writes_nothing(tmp_path, fake):
  zone = make_zone(tmp_path)
  work_dir = tmp_path / "work"
  with pytest.raises(RainContextError, match="NASA GESDISC DATA ARCHIVE") as error:
    rain_context.download(zone, work_dir / "imerg", fake)
  assert "urs.earthdata.nasa.gov" in str(error.value)
  assert not work_dir.exists()


def test_inv_14_main_exits_non_zero_when_download_is_not_authorized(tmp_path, monkeypatch):
  zone = make_zone(tmp_path)
  monkeypatch.setattr(rain_context, "load_zone", lambda _id: zone)
  monkeypatch.setattr(rain_context, "WORK_DIR", tmp_path / "work")
  monkeypatch.setattr(rain_context, "_load_earthaccess", lambda: FakeEarthaccess(authenticated=False))
  with pytest.raises(SystemExit) as exit_info:
    rain_context.main(["--area", zone.id, "--download"])
  assert "GESDISC" in str(exit_info.value)
  assert not (tmp_path / "work").exists()
