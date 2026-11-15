import json
import logging
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from pipeline import population_data
from pipeline.area_config import Zone
from pipeline.population_data import PopulationError
from pipeline.validate import _check_graph, _schema_errors

# Power-of-two pixel size: pixel centers and offsets below are exact binary fractions, so the
# distance ties in these tests are exact. The raster covers lon 0..0.25, lat 0..0.25 (~27 km).
RES = 2**-7
SIZE = 32
NODATA = -99999.0
BBOX = (0.0, 0.0, 0.25, 0.25)  # [w, s, e, n]


def center(row: int, col: int) -> tuple[float, float]:
  """(lon, lat) of the center of pixel (row, col)."""
  return ((col + 0.5) * RES, 0.25 - (row + 0.5) * RES)


def blank() -> np.ndarray:
  return np.full((SIZE, SIZE), NODATA, dtype="float32")


def write_raster(path: Path, data: np.ndarray, *, crs: str = "EPSG:4326", west: float = 0.0, north: float = 0.25) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with rasterio.open(
    path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=1, dtype="float32",
    crs=crs, transform=from_origin(west, north, RES, RES), nodata=NODATA,
  ) as dst:
    dst.write(data, 1)


def make_zone(tmp_path: Path, **changes) -> Zone:
  zone = Zone(
    id="fixture",
    name="Fixture",
    validated=False,
    bbox=BBOX,
    referral_hospitals=("way/1",),
    speed_model_kmh={"trunk": 60},
    closure_roads=("Ruta 901",),
    closure_alternates=(),
    population_raster=str(tmp_path / "raster.tif"),
    population_url="https://example.invalid/raster.tif",
    rain_start="2026-01-01",
    rain_end="2026-01-02",
    detection_limits=None,
    output_dir=tmp_path / "output" / "fixture",
  )
  return replace(zone, **changes)


def setup(tmp_path: Path, data: np.ndarray | None, places: dict[str, tuple[float, float]], *, reverse_originals: bool = False, **raster) -> tuple[Zone, Path]:
  """A zone whose graph.json holds one community per place, plus its work folder with communities.json."""
  zone = make_zone(tmp_path)
  work_dir = tmp_path / "work"
  nodes = [{"id": f"n{i}", "lon": lon, "lat": lat} for i, (lon, lat) in enumerate(places.values(), start=1)]
  communities = [{"id": cid, "name": f"Place {cid}", "node": f"n{i}", "population": None} for i, cid in enumerate(places, start=1)]
  graph = {"schema_version": "0.3", "nodes": nodes, "edges": [], "hospitals": [{"id": "h1", "name": "Hospital", "node": "n1"}], "communities": communities}
  originals = [{"id": cid, "osm_id": f"node/{i}", "lon": lon, "lat": lat} for i, (cid, (lon, lat)) in enumerate(places.items(), start=1)]
  if reverse_originals:
    originals.reverse()
  zone.output_dir.mkdir(parents=True)
  work_dir.mkdir()
  (zone.output_dir / "graph.json").write_text(json.dumps(graph, separators=(",", ":")), encoding="utf-8")
  (work_dir / "communities.json").write_text(json.dumps(originals), encoding="utf-8")
  if data is not None:
    write_raster(Path(zone.population_raster), data, **raster)
  return zone, work_dir


def graph_of(zone: Zone) -> dict:
  return json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))


def report_of(work_dir: Path) -> dict:
  return json.loads((work_dir / "population_report.json").read_text(encoding="utf-8"))


def populations(zone: Zone) -> dict[str, int | None]:
  return {c["id"]: c["population"] for c in graph_of(zone)["communities"]}


def test_inv01_only_population_changes_and_graph_stays_valid(tmp_path):
  data = np.ones((SIZE, SIZE), dtype="float32")
  zone, work_dir = setup(tmp_path, data, {"c1": center(5, 5), "c2": center(25, 25)})
  before = graph_of(zone)
  population_data.run(zone, work_dir)
  after = graph_of(zone)
  for graph in (before, after):
    for community in graph["communities"]:
      community.pop("population")
  assert after == before
  graph = graph_of(zone)
  assert _schema_errors("graph.json", graph, "graph.schema.json") == []
  assert _check_graph(graph) == []


def test_inv02_population_is_an_integer_rounded_half_up(tmp_path):
  data = blank()
  data[5, 5] = 0.25
  data[5, 6] = 0.25  # c1 sums 0.5 -> 1
  data[25, 25] = 2.4  # c2 -> 2
  zone, work_dir = setup(tmp_path, data, {"c1": center(5, 5), "c2": center(25, 25)})
  population_data.run(zone, work_dir)
  values = populations(zone)
  assert values == {"c1": 1, "c2": 2}
  assert all(type(v) is int and v >= 0 for v in values.values())


def test_inv03_community_without_people_gets_null_never_zero(tmp_path):
  data = blank()
  data[5, 5] = 0.3  # valid pixel for c1 but under half a person: rounds to 0
  data[25, 25] = 0.0  # valid pixel with zero people for c3
  zone, work_dir = setup(tmp_path, data, {"c1": center(5, 5), "c2": center(15, 15), "c3": center(25, 25)})
  population_data.run(zone, work_dir)
  # c2 has no valid pixel in reach; c1 and c3 would round to 0, which the graph schema forbids (minimum 1).
  assert populations(zone) == {"c1": None, "c2": None, "c3": None}
  assert _schema_errors("graph.json", graph_of(zone), "graph.schema.json") == []


def test_inv04_each_pixel_counts_for_one_community(tmp_path):
  data = np.ones((SIZE, SIZE), dtype="float32")
  zone, work_dir = setup(tmp_path, data, {"c1": center(8, 8), "c2": center(8, 24), "c3": center(24, 16)})
  population_data.run(zone, work_dir)
  report = report_of(work_dir)
  assert sum(populations(zone).values()) + report["unassigned"] == SIZE * SIZE
  assert report["assigned"] + report["unassigned"] == SIZE * SIZE


def test_inv04_tie_goes_to_the_lowest_id_whatever_the_file_order(tmp_path):
  data = blank()
  data[16, 16] = 10.0
  lon, lat = center(16, 16)
  places = {"c1": (lon - RES, lat), "c2": (lon + RES, lat)}
  zone, work_dir = setup(tmp_path, data, places, reverse_originals=True)
  population_data.run(zone, work_dir)
  assert populations(zone) == {"c1": 10, "c2": None}


def test_inv05_pixel_beyond_the_cutoff_stays_unassigned(tmp_path):
  data = blank()
  data[5, 5] = 5.0
  data[31, 31] = 7.0  # ~26 km from the only community
  zone, work_dir = setup(tmp_path, data, {"c1": center(5, 5)})
  population_data.run(zone, work_dir)
  report = report_of(work_dir)
  assert populations(zone) == {"c1": 5}
  assert report["assigned"] == pytest.approx(5.0)
  assert report["unassigned"] == pytest.approx(7.0)


def test_inv05_cutoff_is_the_road_graph_limit():
  from pipeline import road_graph

  assert population_data.MAX_SNAP_M == road_graph.MAX_SNAP_M == 3000


def test_inv06_nodata_is_in_no_total(tmp_path):
  data = blank()
  data[5, 5] = 4.0
  data[5, 6] = 2.0
  zone, work_dir = setup(tmp_path, data, {"c1": center(5, 5)})
  population_data.run(zone, work_dir)
  report = report_of(work_dir)
  assert report["raster_total"] == pytest.approx(6.0)
  assert report["assigned"] + report["unassigned"] == pytest.approx(6.0)
  assert populations(zone) == {"c1": 6}


def test_inv07_assigned_plus_unassigned_equals_raster_total_inside_bbox(tmp_path):
  rng = np.random.default_rng(7)
  data = rng.uniform(0, 3, (SIZE, SIZE)).astype("float32")
  data[rng.random((SIZE, SIZE)) < 0.2] = NODATA
  data[20, 20] = 1000.0  # lies outside the bbox below: must not be read
  bbox = (0.0, 0.125, 0.125, 0.25)  # the top-left quarter, 16 x 16 pixels
  zone, work_dir = setup(tmp_path, data, {"c1": center(3, 3), "c2": center(12, 10)})
  zone = replace(zone, bbox=bbox)
  population_data.run(zone, work_dir)
  report = report_of(work_dir)
  inside = data[:16, :16]
  expected = float(inside[inside != NODATA].astype("float64").sum())
  assert report["raster_total"] == pytest.approx(expected)
  assert report["assigned"] + report["unassigned"] == pytest.approx(report["raster_total"])


def test_inv08_report_states_totals_and_community_counts(tmp_path):
  data = blank()
  data[5, 5] = 5.0
  data[31, 31] = 7.0
  zone, work_dir = setup(tmp_path, data, {"c1": center(5, 5), "c2": center(15, 15), "c3": center(25, 25), "c4": center(26, 5)})
  population_data.run(zone, work_dir)
  report = report_of(work_dir)
  assert set(report) == {"raster_total", "assigned", "unassigned", "communities_with_value", "communities_without_value", "share_with_value"}
  assert report["communities_with_value"] == 1
  assert report["communities_without_value"] == 3
  assert report["share_with_value"] == pytest.approx(0.25)
  assert report["raster_total"] == pytest.approx(12.0)


def test_inv09_missing_raster_stops_the_run_and_names_the_fix(tmp_path):
  zone, work_dir = setup(tmp_path, None, {"c1": center(5, 5)})
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(PopulationError) as exc:
    population_data.run(zone, work_dir)
  assert zone.population_raster in str(exc.value)
  assert "make worldpop" in str(exc.value)
  assert (zone.output_dir / "graph.json").read_bytes() == original


def test_inv09_main_exits_non_zero(tmp_path, monkeypatch):
  zone, work_dir = setup(tmp_path, None, {"c1": center(5, 5)})
  monkeypatch.setattr(population_data, "load_zone", lambda area: zone)
  monkeypatch.setattr(population_data, "WORK_DIR", tmp_path)
  work_dir.rename(tmp_path / zone.id)
  with pytest.raises(SystemExit) as exc:
    population_data.main(["--area", zone.id])
  assert "make worldpop" in str(exc.value.code)


def test_inv10_no_population_writes_null_everywhere_and_logs_it(tmp_path, caplog):
  zone, work_dir = setup(tmp_path, None, {"c1": center(5, 5), "c2": center(25, 25)})
  graph = graph_of(zone)
  for community in graph["communities"]:
    community["population"] = 7  # left over from an earlier run
  (zone.output_dir / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
  with caplog.at_level(logging.INFO):
    population_data.run(zone, work_dir, skip=True)
  assert populations(zone) == {"c1": None, "c2": None}
  assert any("skipped" in record.getMessage().lower() for record in caplog.records)


def test_inv11_community_ids_must_match_graph(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5), "c2": center(25, 25)})
  originals = json.loads((work_dir / "communities.json").read_text(encoding="utf-8"))
  originals[1]["id"] = "c3"
  (work_dir / "communities.json").write_text(json.dumps(originals), encoding="utf-8")
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(PopulationError, match="c2"):
    population_data.run(zone, work_dir)
  assert (zone.output_dir / "graph.json").read_bytes() == original


def test_inv14_raster_in_another_crs_stops_the_run(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5)}, crs="EPSG:3857")
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(PopulationError) as exc:
    population_data.run(zone, work_dir)
  assert "raster.tif" in str(exc.value)
  assert "EPSG:4326" in str(exc.value)
  assert (zone.output_dir / "graph.json").read_bytes() == original


def test_inv14_raster_outside_the_bbox_stops_the_run(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5)}, west=50.0)
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(PopulationError) as exc:
    population_data.run(zone, work_dir)
  assert "raster.tif" in str(exc.value)
  assert "bbox" in str(exc.value)
  assert (zone.output_dir / "graph.json").read_bytes() == original


@pytest.mark.parametrize("bad", [-5.0, float("inf"), float("-inf")])
def test_inv15_negative_or_non_finite_pixel_stops_the_run(tmp_path, bad):
  data = blank()
  data[5, 5] = bad  # not the declared nodata, so it is a value the raster claims to hold
  data[5, 6] = 2.6
  zone, work_dir = setup(tmp_path, data, {"c1": center(5, 5)})
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(PopulationError, match="raster.tif"):
    population_data.run(zone, work_dir)
  assert (zone.output_dir / "graph.json").read_bytes() == original
  assert not (work_dir / "population_report.json").exists()


def test_inv16_graph_without_communities_stops_the_run(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {})
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(PopulationError, match="no communities"):
    population_data.run(zone, work_dir)
  assert (zone.output_dir / "graph.json").read_bytes() == original
  population_data.run(zone, work_dir, skip=True)  # nothing to fill is fine when the raster is skipped
  assert graph_of(zone)["communities"] == []


def test_inv17_no_population_deletes_the_report_of_an_earlier_run(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5)})
  population_data.run(zone, work_dir)
  assert (work_dir / "population_report.json").is_file()
  population_data.run(zone, work_dir, skip=True)
  assert populations(zone) == {"c1": None}
  assert not (work_dir / "population_report.json").exists()


def test_inv18_repeated_community_id_stops_the_run(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5), "c2": center(25, 25)})
  originals = json.loads((work_dir / "communities.json").read_text(encoding="utf-8"))
  (work_dir / "communities.json").write_text(json.dumps([*originals, {**originals[0], "lon": center(25, 5)[0]}]), encoding="utf-8")
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(PopulationError, match="c1"):
    population_data.run(zone, work_dir)
  assert (zone.output_dir / "graph.json").read_bytes() == original


@pytest.mark.parametrize("change", [{"lon": None}, {"lon": "10.0"}, {"lat": True}, {"lat": float("nan")}, "drop-lon"])
def test_inv19_community_without_numeric_coordinates_stops_the_run(tmp_path, change):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5), "c2": center(25, 25)})
  originals = json.loads((work_dir / "communities.json").read_text(encoding="utf-8"))
  if change == "drop-lon":
    del originals[1]["lon"]
  else:
    originals[1].update(change)
  (work_dir / "communities.json").write_text(json.dumps(originals), encoding="utf-8")
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(PopulationError, match="c2"):
    population_data.run(zone, work_dir)
  assert (zone.output_dir / "graph.json").read_bytes() == original


def test_inv20_second_run_writes_the_same_graph(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5), "c2": center(25, 25)})
  population_data.run(zone, work_dir)
  first = (zone.output_dir / "graph.json").read_bytes()
  population_data.run(zone, work_dir)
  assert (zone.output_dir / "graph.json").read_bytes() == first
