"""Adversarial attacks on population-data (breaker). Claims are cited by ID."""

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from dataclasses import replace

from test_population_data import RES, SIZE, blank, center, graph_of, populations, report_of, setup, write_raster

from pipeline import population_data


def test_inv05_cutoff_sits_between_2_6_and_3_5_km(tmp_path):
  # One row is ~868 m: 3 rows ~2.6 km are inside the 3000 m cutoff, 4 rows ~3.5 km are outside.
  data = blank()
  data[10, 10] = 1.0
  data[13, 10] = 2.0
  data[14, 10] = 4.0
  lon, lat = center(10, 10)
  zone, work_dir = setup(tmp_path, data, {"c1": (lon, lat)})
  population_data.run(zone, work_dir)
  report = report_of(work_dir)
  assert report["assigned"] == pytest.approx(3.0)
  assert report["unassigned"] == pytest.approx(4.0)


def test_inv04_result_does_not_depend_on_the_block_size(tmp_path, monkeypatch):
  rng = np.random.default_rng(11)
  data = rng.uniform(0, 5, (SIZE, SIZE)).astype("float32")
  places = {"c1": center(4, 4), "c2": center(10, 25), "c3": center(27, 9)}
  zone, work_dir = setup(tmp_path, data, places)
  population_data.run(zone, work_dir)
  whole, whole_report = populations(zone), report_of(work_dir)
  monkeypatch.setattr(population_data, "BLOCK_CELLS", 1)  # one row per block
  zone2, work_dir2 = setup(tmp_path / "again", data, places)
  population_data.run(zone2, work_dir2)
  assert populations(zone2) == whole
  assert report_of(work_dir2) == pytest.approx(whole_report)


def test_inv01_running_twice_gives_the_same_graph(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5), "c2": center(25, 25)})
  population_data.run(zone, work_dir)
  first = (zone.output_dir / "graph.json").read_bytes()
  population_data.run(zone, work_dir)
  assert (zone.output_dir / "graph.json").read_bytes() == first


def test_inv06_nan_pixels_count_even_without_a_declared_nodata(tmp_path):
  zone, work_dir = setup(tmp_path, None, {"c1": center(5, 5)})
  data = np.full((SIZE, SIZE), np.nan, dtype="float32")
  data[5, 5] = 3.0
  with rasterio.open(
    zone.population_raster, "w", driver="GTiff", height=SIZE, width=SIZE, count=1, dtype="float32",
    crs="EPSG:4326", transform=from_origin(0.0, 0.25, RES, RES),
  ) as dst:
    dst.write(data, 1)
  population_data.run(zone, work_dir)
  assert populations(zone) == {"c1": 3}
  assert report_of(work_dir)["raster_total"] == pytest.approx(3.0)


def test_inv09_directory_in_place_of_the_raster_is_an_english_error(tmp_path):
  zone, work_dir = setup(tmp_path, None, {"c1": center(5, 5)})
  Path(zone.population_raster).mkdir()
  with pytest.raises(population_data.PopulationError, match="make worldpop"):
    population_data.run(zone, work_dir)


def test_inv09_corrupt_raster_is_an_english_error_and_leaves_the_graph(tmp_path):
  zone, work_dir = setup(tmp_path, None, {"c1": center(5, 5)})
  Path(zone.population_raster).write_bytes(b"not a tiff")
  original = (zone.output_dir / "graph.json").read_bytes()
  with pytest.raises(population_data.PopulationError, match="raster.tif"):
    population_data.run(zone, work_dir)
  assert (zone.output_dir / "graph.json").read_bytes() == original


def test_inv11_graph_with_extra_community_names_it(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5), "c2": center(25, 25), "c10": center(15, 15)})
  originals = json.loads((work_dir / "communities.json").read_text(encoding="utf-8"))
  (work_dir / "communities.json").write_text(json.dumps([o for o in originals if o["id"] != "c10"]), encoding="utf-8")
  with pytest.raises(population_data.PopulationError, match="c10"):
    population_data.run(zone, work_dir)


def test_inv04_tie_between_c2_and_c10_goes_to_c2(tmp_path):
  # By text "c10" < "c2"; the lowest id is by number.
  data = blank()
  data[16, 16] = 10.0
  lon, lat = center(16, 16)
  zone, work_dir = setup(tmp_path, data, {"c10": (lon - RES, lat), "c2": (lon + RES, lat)}, reverse_originals=True)
  population_data.run(zone, work_dir)
  assert populations(zone) == {"c10": None, "c2": 10}


def test_inv11_first_differing_id_is_ordered_by_number(tmp_path):
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(5, 5), "c2": center(15, 15), "c10": center(25, 25)})
  originals = json.loads((work_dir / "communities.json").read_text(encoding="utf-8"))
  (work_dir / "communities.json").write_text(json.dumps([o for o in originals if o["id"] == "c1"]), encoding="utf-8")
  with pytest.raises(population_data.PopulationError, match="differs: c2[)]"):
    population_data.run(zone, work_dir)


@pytest.mark.parametrize(("extra", "columns"), [(0.25, 16), (0.75, 17)])
def test_inv07_pixel_is_read_when_its_center_is_inside_bbox(tmp_path, extra, columns):
  # Pixel column 16 spans 0.125..0.1328; its center 0.1289 is inside only when east >= 0.1289.
  zone, work_dir = setup(tmp_path, np.ones((SIZE, SIZE), dtype="float32"), {"c1": center(3, 3)})
  zone = replace(zone, bbox=(0.0, 0.125, 0.125 + extra * RES, 0.25))
  population_data.run(zone, work_dir)
  assert report_of(work_dir)["raster_total"] == pytest.approx(16 * columns)


def test_download_replaces_the_raster_only_with_a_file_that_opens(tmp_path):
  source = tmp_path / "source.tif"
  write_raster(source, np.ones((4, 4), dtype="float32"))
  zone, _ = setup(tmp_path / "zone", None, {"c1": center(5, 5)})
  raster = tmp_path / "target" / "raster.tif"
  population_data.download(replace(zone, population_url=source.as_uri()), raster)
  with rasterio.open(raster) as src:
    assert src.count == 1
  good = raster.read_bytes()
  junk = tmp_path / "junk.tif"
  junk.write_bytes(b"not a tiff")
  with pytest.raises(population_data.PopulationError, match="junk.tif"):
    population_data.download(replace(zone, population_url=junk.as_uri()), raster)
  assert raster.read_bytes() == good
  assert [f.name for f in raster.parent.iterdir()] == ["raster.tif"]
