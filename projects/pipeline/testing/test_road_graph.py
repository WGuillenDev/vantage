import io
import json
import math
import shutil
import urllib.error
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx
import osmnx as ox
import pytest

from pipeline import road_graph
from pipeline.area_config import Zone
from pipeline.validate import _check_graph, _schema_errors

FIXTURE = Path(__file__).parent / "fixtures" / "road_graph"
SPEEDS = {"trunk": 60, "primary": 40, "secondary": 40, "tertiary": 40}
PLACES = {"Fixture Village": (0.0052, 10.0102), "Fixture Town": (0.0003, 10.0195)}


def make_zone(tmp_path: Path, **changes) -> Zone:
  zone = Zone(
    id="fixture",
    name="Fixture",
    validated=False,
    bbox=(9.995, -0.005, 10.05, 0.02),
    referral_hospitals=("way/301", "node/30"),
    speed_model_kmh=dict(SPEEDS),
    closure_roads=("Ruta 901",),
    closure_alternates=(),
    population_raster="work/none.tif",
    population_url="https://example.invalid/none.tif",
    rain_start="2026-01-01",
    rain_end="2026-01-02",
    detection_limits=None,
    output_dir=tmp_path / "output" / "fixture",
  )
  return replace(zone, **changes)


def extract(tmp_path: Path, roads: str = "roads.osm", features: str = "features.osm") -> Path:
  """The zone's work folder with the fixture extract in work/osm/."""
  osm = tmp_path / "work" / "osm"
  osm.mkdir(parents=True, exist_ok=True)
  shutil.copy(FIXTURE / roads, osm / "roads.osm")
  shutil.copy(FIXTURE / features, osm / "features.osm")
  return tmp_path / "work"


def run(tmp_path: Path, zone: Zone | None = None, **files) -> dict:
  zone = zone or make_zone(tmp_path)
  road_graph.run(zone, extract(tmp_path, **files))
  return json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))


def fails_without_graph(tmp_path: Path, zone: Zone, *expected: str, **files) -> None:
  with pytest.raises(road_graph.RoadGraphError) as error:
    road_graph.run(zone, extract(tmp_path, **files))
  for text in expected:
    assert text in str(error.value)
  assert not (zone.output_dir / "graph.json").exists()
  assert not (tmp_path / "work" / "communities.json").exists()


def edge_class(edge: dict) -> str:
  # The fixture's roads tell their class apart by name and direction.
  if edge["road"] in ("Ruta 901", "Ruta 903"):
    return "trunk"
  if edge["road"] == "Fixture Primary":
    return "primary"
  return "secondary" if edge["oneway"] else "tertiary"


def test_inv01_output_passes_schema_and_node_refs(tmp_path):
  graph = run(tmp_path)
  assert graph["schema_version"] == "0.3"
  assert _schema_errors("graph.json", graph, "graph.schema.json") == []
  assert _check_graph(graph) == []


def test_inv02_geometry_ends_on_its_nodes(tmp_path):
  graph = run(tmp_path)
  nodes = {n["id"]: [n["lon"], n["lat"]] for n in graph["nodes"]}
  for e in graph["edges"]:
    assert e["geometry"][0] == nodes[e["from"]]
    assert e["geometry"][-1] == nodes[e["to"]]


def test_inv03_integer_costs_rounded_half_up(tmp_path):
  graph = run(tmp_path)
  for e in graph["edges"]:
    assert isinstance(e["length_m"], int) and isinstance(e["time_s"], int)
    assert e["time_s"] == math.floor(e["length_m"] / (SPEEDS[edge_class(e)] / 3.6) + 0.5)
  assert road_graph.round_half_up(2.5) == 3
  assert road_graph.round_half_up(3.5) == 4


def test_inv04_long_edges_are_split(tmp_path):
  graph = run(tmp_path)
  assert max(e["length_m"] for e in graph["edges"]) <= 1000
  assert len(graph["nodes"]) > 6  # split nodes were added to the 6 kept OSM nodes


def test_inv05_no_candidate_ids(tmp_path):
  assert all(e["candidate_id"] is None for e in run(tmp_path)["edges"])


def test_inv06_hospitals_are_the_zones_referral_ids(tmp_path):
  graph = run(tmp_path)
  # Numbered by ascending OSM id, whatever the order of the config list (way/301 comes first there).
  assert [h["name"] for h in graph["hospitals"]] == ["Fixture Hospital North", "Fixture Hospital East"]
  assert [h["id"] for h in graph["hospitals"]] == ["h1", "h2"]


def test_inv06_other_hospitals_in_the_extract_are_left_out(tmp_path):
  graph = run(tmp_path, make_zone(tmp_path, referral_hospitals=("node/30",)))
  assert [h["name"] for h in graph["hospitals"]] == ["Fixture Hospital North"]


def test_inv07_unknown_referral_id_stops_the_run(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("way/301", "way/999"))
  fails_without_graph(tmp_path, zone, "way/999")


def test_inv07_extract_with_no_features_stops_with_the_hospital_id(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("way/301",))
  fails_without_graph(tmp_path, zone, "way/301", features="features_empty.osm")


def test_inv08_communities_are_named_places_near_their_node(tmp_path):
  graph = run(tmp_path)
  nodes = {n["id"]: n for n in graph["nodes"]}
  assert [c["name"] for c in graph["communities"]] == ["Fixture Village", "Fixture Town"]
  for c in graph["communities"]:
    lat, lon = PLACES[c["name"]]
    node = nodes[c["node"]]
    assert ox.distance.great_circle(lat, lon, node["lat"], node["lon"]) <= 3000


def test_inv09_far_community_is_dropped_and_logged(tmp_path, caplog):
  graph = run(tmp_path)
  assert "Fixture Far Hamlet" not in [c["name"] for c in graph["communities"]]
  logged = [r.getMessage() for r in caplog.records if "Fixture Far Hamlet" in r.getMessage()]
  assert logged and " m " in logged[0]


def test_inv10_population_is_null(tmp_path):
  assert all(c["population"] is None for c in run(tmp_path)["communities"])


def test_inv11_time_uses_only_the_zones_speed_table(tmp_path):
  zone = make_zone(tmp_path, speed_model_kmh={**SPEEDS, "trunk": 30})
  edges = run(tmp_path, zone)["edges"]
  # Ruta 903 is tagged maxspeed 90 in the fixture; the zone's 30 must win.
  ruta_903 = next(e for e in edges if e["road"] == "Ruta 903")
  assert ruta_903["time_s"] == math.floor(ruta_903["length_m"] / (30 / 3.6) + 0.5)
  for e in edges:
    assert e["time_s"] == math.floor(e["length_m"] / (zone.speed_model_kmh[edge_class(e)] / 3.6) + 0.5)


def test_inv12_same_input_gives_same_bytes(tmp_path):
  zone = make_zone(tmp_path)
  run(tmp_path, zone)
  first = (zone.output_dir / "graph.json").read_bytes()
  run(tmp_path, zone)
  assert (zone.output_dir / "graph.json").read_bytes() == first


def test_inv13_file_is_at_most_3_mb(tmp_path):
  zone = make_zone(tmp_path)
  run(tmp_path, zone)
  assert (zone.output_dir / "graph.json").stat().st_size <= 3 * 1024 * 1024


def test_inv14_graph_is_weakly_connected(tmp_path):
  graph = run(tmp_path)
  g = nx.Graph()
  g.add_nodes_from(n["id"] for n in graph["nodes"])
  g.add_edges_from((e["from"], e["to"]) for e in graph["edges"])
  assert nx.is_connected(g)


def test_inv15_no_self_loops(tmp_path):
  assert all(e["from"] != e["to"] for e in run(tmp_path)["edges"])


def test_inv16_unnamed_hospital_stops_the_run(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("node/30", "node/36"))
  fails_without_graph(tmp_path, zone, "node/36")


def test_inv17_class_without_speed_stops_the_run(tmp_path):
  zone = make_zone(tmp_path, speed_model_kmh={k: v for k, v in SPEEDS.items() if k != "tertiary"})
  fails_without_graph(tmp_path, zone, "tertiary")


def test_inv18_oversized_graph_stops_the_run(tmp_path, monkeypatch):
  monkeypatch.setattr(road_graph, "MAX_GRAPH_BYTES", 100)
  fails_without_graph(tmp_path, make_zone(tmp_path), "bytes")


def test_inv19_parallel_edges_ordered_by_way_id(tmp_path):
  roads = [e["road"] for e in run(tmp_path, roads="roads_parallel.osm")["edges"]]
  # (1, 2) is the lowest pair of OSM end ids, so its two parallel edges come first.
  assert roads[:2] == ["Fixture Smaller Way Id", "Fixture Larger Way Id"]


def test_inv20_missing_extract_says_how_to_get_it(tmp_path, monkeypatch, capsys):
  zone = make_zone(tmp_path)
  monkeypatch.setattr(road_graph, "load_zone", lambda _id: zone)
  monkeypatch.setattr(road_graph, "WORK_DIR", tmp_path / "work")
  with pytest.raises(SystemExit) as exit_info:
    road_graph.main(["--area", "fixture"])
  assert exit_info.value.code not in (0, None)
  assert "make osm" in str(exit_info.value.code)
  assert not (zone.output_dir / "graph.json").exists()


class FakeResponse(io.BytesIO):
  def __enter__(self):
    return self

  def __exit__(self, *_):
    return False


def download_with(monkeypatch, tmp_path: Path) -> Path:
  def fake_urlopen(request, **_):
    name = "features.osm" if b"amenity" in request.data else "roads.osm"
    return FakeResponse((FIXTURE / name).read_bytes())

  monkeypatch.setattr(road_graph.urllib.request, "urlopen", fake_urlopen)
  monkeypatch.setattr(road_graph, "WORK_DIR", tmp_path / "work")
  zone = make_zone(tmp_path)
  monkeypatch.setattr(road_graph, "load_zone", lambda _id: zone)
  road_graph.main(["--area", "fixture", "--download"])
  return tmp_path / "work" / "fixture" / "osm"


def test_inv21_download_records_utc_extract_date(tmp_path, monkeypatch):
  osm = download_with(monkeypatch, tmp_path)
  assert (osm / "extract_date.txt").read_text(encoding="utf-8").strip() == datetime.now(UTC).date().isoformat()


def test_inv22_download_only_downloads(tmp_path, monkeypatch):
  # The fixture extract is served, so a build after downloading would succeed and leave a graph.json behind.
  osm = download_with(monkeypatch, tmp_path)
  assert sorted(p.name for p in osm.iterdir()) == ["extract_date.txt", "features.osm", "roads.osm"]
  assert not (tmp_path / "output").exists()


def test_inv23_hospitals_and_communities_sit_in_the_largest_strong_component(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("node/50",), bbox=(9.995, -0.005, 10.05, 0.02))
  graph = run(tmp_path, zone, roads="roads_spur.osm", features="features_spur.osm")
  g = nx.DiGraph()
  g.add_nodes_from(n["id"] for n in graph["nodes"])
  for e in graph["edges"]:
    g.add_edge(e["from"], e["to"])
    if not e["oneway"]:
      g.add_edge(e["to"], e["from"])
  largest = max(nx.strongly_connected_components(g), key=len)
  sink = next(n["id"] for n in graph["nodes"] if n["lat"] == 0.006)
  assert sink not in largest  # the nearest node to both is the sink, so a plain nearest-node snap would pick it
  assert graph["hospitals"][0]["node"] in largest
  assert [c["node"] in largest for c in graph["communities"]] == [True]


def test_inv24_distant_referral_hospital_stops_the_run(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("node/30", "node/37"))
  fails_without_graph(tmp_path, zone, "node/37", "Fixture Far Hospital", " m")


def test_inv26_communities_json_has_one_entry_per_community(tmp_path):
  zone = make_zone(tmp_path)
  graph = run(tmp_path, zone)
  entries = json.loads((tmp_path / "work" / "communities.json").read_text(encoding="utf-8"))
  assert [e["id"] for e in entries] == [c["id"] for c in graph["communities"]]
  by_name = dict(zip((c["id"] for c in graph["communities"]), (c["name"] for c in graph["communities"])))
  for e in entries:
    lat, lon = PLACES[by_name[e["id"]]]
    assert e["osm_id"].startswith("node/")
    assert (e["lat"], e["lon"]) == (lat, lon)


EMPTY_OSM = '<?xml version="1.0" encoding="UTF-8"?><osm version="0.6"/>'
# A timed-out query still returns the elements it found, so the remark is the only sign of the failure.
REMARK = '<osm version="0.6"><node id="1" lat="0" lon="10"/><remark>runtime error: Query timed out</remark></osm>'


def extract_with(tmp_path: Path, roads: str | None = None, features: str | None = None) -> Path:
  """The fixture extract with one of its two files replaced by the given text."""
  work = extract(tmp_path)
  if roads is not None:
    (work / "osm" / "roads.osm").write_text(roads, encoding="utf-8")
  if features is not None:
    (work / "osm" / "features.osm").write_text(features, encoding="utf-8")
  return work


def half(name: str) -> str:
  text = (FIXTURE / name).read_text(encoding="utf-8")
  return text[: len(text) // 2]


UNREADABLE = [
  pytest.param("roads.osm", "", id="roads-zero-bytes"),
  pytest.param("roads.osm", EMPTY_OSM, id="roads-without-ways"),
  pytest.param("roads.osm", half("roads.osm"), id="roads-truncated"),
  pytest.param("features.osm", "", id="features-zero-bytes"),
  pytest.param("features.osm", half("features.osm"), id="features-truncated"),
]


@pytest.mark.parametrize(("name", "content"), UNREADABLE)
def test_inv27_unusable_extract_file_stops_naming_it(tmp_path, name, content):
  zone = make_zone(tmp_path)
  work = extract_with(tmp_path, **{name.removesuffix(".osm"): content})
  with pytest.raises(road_graph.RoadGraphError) as error:
    road_graph.run(zone, work)
  assert name in str(error.value)
  assert not (zone.output_dir / "graph.json").exists()
  assert not (work / "communities.json").exists()


def previous_extract(tmp_path: Path) -> Path:
  osm = tmp_path / "work" / "fixture" / "osm"
  osm.mkdir(parents=True)
  (osm / "roads.osm").write_text("OLD ROADS", encoding="utf-8")
  (osm / "features.osm").write_text("OLD FEATURES", encoding="utf-8")
  (osm / "extract_date.txt").write_text("2026-01-01\n", encoding="utf-8")
  return osm


def failed_download(monkeypatch, tmp_path: Path, answer) -> str:
  """Runs `--download` with Overpass answering through `answer(name)` and returns the exit message."""
  def fake_urlopen(request, **_):
    return answer("features.osm" if b"amenity" in request.data else "roads.osm")

  monkeypatch.setattr(road_graph.urllib.request, "urlopen", fake_urlopen)
  monkeypatch.setattr(road_graph, "WORK_DIR", tmp_path / "work")
  monkeypatch.setattr(road_graph, "load_zone", lambda _id: make_zone(tmp_path))
  with pytest.raises(SystemExit) as exit_info:
    road_graph.main(["--area", "fixture", "--download"])
  return str(exit_info.value.code)


def assert_previous_extract_intact(osm: Path) -> None:
  assert (osm / "roads.osm").read_text(encoding="utf-8") == "OLD ROADS"
  assert (osm / "features.osm").read_text(encoding="utf-8") == "OLD FEATURES"
  assert (osm / "extract_date.txt").read_text(encoding="utf-8") == "2026-01-01\n"


FAILURES = [
  pytest.param(lambda: urllib.error.URLError("no route to host"), id="network"),
  pytest.param(lambda: TimeoutError("timed out"), id="timeout"),
  pytest.param(lambda: urllib.error.HTTPError("https://example.invalid", 504, "Gateway Timeout", {}, None), id="http-status"),
]


@pytest.mark.parametrize("failure", FAILURES)
@pytest.mark.parametrize("failing", ["roads.osm", "features.osm"])
def test_inv28_failed_request_leaves_the_previous_extract_whole(tmp_path, monkeypatch, failure, failing):
  osm = previous_extract(tmp_path)

  def answer(name):
    if name == failing:
      raise failure()
    return FakeResponse((FIXTURE / name).read_bytes())

  message = failed_download(monkeypatch, tmp_path, answer)
  assert message.startswith("road-graph:") and failing in message
  assert_previous_extract_intact(osm)


UNUSABLE_ANSWERS = [
  pytest.param(b"<osm version=", id="not-xml"),
  pytest.param(EMPTY_OSM.encode(), id="no-elements"),
  pytest.param(REMARK.encode(), id="remark"),
]


@pytest.mark.parametrize("body", UNUSABLE_ANSWERS)
@pytest.mark.parametrize("bad", ["roads.osm", "features.osm"])
def test_inv29_unusable_answer_leaves_the_previous_extract_whole(tmp_path, monkeypatch, body, bad):
  osm = previous_extract(tmp_path)

  def answer(name):
    return FakeResponse(body if name == bad else (FIXTURE / name).read_bytes())

  message = failed_download(monkeypatch, tmp_path, answer)
  assert message.startswith("road-graph:") and bad in message
  assert_previous_extract_intact(osm)


def test_inv30_same_osm_element_twice_stops_naming_both_ids(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("way/301", "way/0301"))
  fails_without_graph(tmp_path, zone, "way/301", "way/0301")


def test_first_of_a_merged_tag_does_not_depend_on_list_order():
  from pipeline.road_graph import _first

  assert _first(["Calle 1", "Avenida 3"]) == _first(["Avenida 3", "Calle 1"]) == "Avenida 3"
  assert _first(["b;c", "a"]) == "a"


def test_road_class_of_a_merged_way_is_the_highest_one_whatever_the_order():
  assert road_graph._road_class({"highway": ["tertiary", "trunk_link"]}) == "trunk"
  assert road_graph._road_class({"highway": ["trunk", "tertiary"]}) == "trunk"
  assert road_graph._road_class({"highway": "primary_link"}) == "primary"
