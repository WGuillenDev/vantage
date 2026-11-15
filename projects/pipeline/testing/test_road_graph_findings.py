import json
import urllib.error
from pathlib import Path

import pytest

from pipeline import road_graph
from pipeline.road_graph import RoadGraphError
from test_road_graph import FIXTURE, FakeResponse, extract, make_zone

EMPTY = '<?xml version="1.0" encoding="UTF-8"?><osm version="0.6"/>'


def put(tmp_path: Path, roads: str | None = None, features: str | None = None) -> Path:
  """The fixture extract, with one of the two files replaced by the given text."""
  work = extract(tmp_path)
  if roads is not None:
    (work / "osm" / "roads.osm").write_text(roads, encoding="utf-8")
  if features is not None:
    (work / "osm" / "features.osm").write_text(features, encoding="utf-8")
  return work


def stops_cleanly(tmp_path: Path, work: Path, *expected: str) -> None:
  zone = make_zone(tmp_path)
  with pytest.raises(RoadGraphError) as error:
    road_graph.run(zone, work)
  for text in expected:
    assert text in str(error.value)
  assert not (zone.output_dir / "graph.json").exists()
  assert not (work / "communities.json").exists()


# --- INV-07: a hospital that is not in the extract must stop the run, whatever the extract looks like ---


def test_inv07_zero_byte_features_file_stops_cleanly(tmp_path):
  stops_cleanly(tmp_path, put(tmp_path, features=""))


def test_inv07_truncated_features_file_stops_cleanly(tmp_path):
  features = (FIXTURE / "features.osm").read_text(encoding="utf-8")
  stops_cleanly(tmp_path, put(tmp_path, features=features[: len(features) // 2]))


# --- INV-20 and the trust boundary: an unusable roads file is an English error, not a traceback ---


def test_roads_file_with_no_ways_stops_cleanly(tmp_path):
  stops_cleanly(tmp_path, put(tmp_path, roads=EMPTY))


def test_zero_byte_roads_file_stops_cleanly(tmp_path):
  stops_cleanly(tmp_path, put(tmp_path, roads=""))


def test_truncated_roads_file_stops_cleanly(tmp_path):
  roads = (FIXTURE / "roads.osm").read_text(encoding="utf-8")
  stops_cleanly(tmp_path, put(tmp_path, roads=roads[: len(roads) // 2]))


# --- INV-06: one hospital per id; two spellings of the same id are one hospital ---


def test_inv06_same_osm_id_with_a_leading_zero_is_not_a_second_hospital(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("way/301", "way/0301"))
  road_graph.run(zone, extract(tmp_path))
  hospitals = json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))["hospitals"]
  assert len(hospitals) == 1


# --- INV-21 and INV-22: a failed download must not leave a mixed extract behind ---


def test_inv21_failed_second_request_leaves_the_previous_extract_whole(tmp_path, monkeypatch):
  osm = tmp_path / "work" / "fixture" / "osm"
  osm.mkdir(parents=True)
  (osm / "roads.osm").write_text("OLD ROADS", encoding="utf-8")
  (osm / "features.osm").write_text("OLD FEATURES", encoding="utf-8")
  (osm / "extract_date.txt").write_text("2026-01-01\n", encoding="utf-8")

  def fake_urlopen(request, **_):
    if b"amenity" in request.data:
      raise urllib.error.URLError("connection reset")
    return FakeResponse((FIXTURE / "roads.osm").read_bytes())

  monkeypatch.setattr(road_graph.urllib.request, "urlopen", fake_urlopen)
  monkeypatch.setattr(road_graph, "WORK_DIR", tmp_path / "work")
  monkeypatch.setattr(road_graph, "load_zone", lambda _id: make_zone(tmp_path))
  with pytest.raises((SystemExit, urllib.error.URLError)):
    road_graph.main(["--area", "fixture", "--download"])
  assert (osm / "roads.osm").read_text(encoding="utf-8") == "OLD ROADS"
  assert (osm / "extract_date.txt").read_text(encoding="utf-8") == "2026-01-01\n"


def test_inv21_a_download_that_fails_is_an_english_exit_not_a_traceback(tmp_path, monkeypatch):
  def fake_urlopen(request, **_):
    raise urllib.error.URLError("no route to host")

  monkeypatch.setattr(road_graph.urllib.request, "urlopen", fake_urlopen)
  monkeypatch.setattr(road_graph, "WORK_DIR", tmp_path / "work")
  monkeypatch.setattr(road_graph, "load_zone", lambda _id: make_zone(tmp_path))
  with pytest.raises(SystemExit) as exit_info:
    road_graph.main(["--area", "fixture", "--download"])
  assert "road-graph" in str(exit_info.value.code)
  assert not (tmp_path / "work" / "fixture" / "osm" / "extract_date.txt").exists()
