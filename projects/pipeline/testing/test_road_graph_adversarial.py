import json
import math
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from pipeline import road_graph
from test_road_graph import FIXTURE, FakeResponse, extract, make_zone



def put_features(tmp_path: Path, features: str) -> Path:
  work = extract(tmp_path)
  (work / "osm" / "features.osm").write_text(features, encoding="utf-8")
  return work


# --- Real Costa Rican names carry accents: they must survive both files and the 3 MB check ---


ACCENTED = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="30" lat="0.0004" lon="10.0001"><tag k="amenity" v="hospital"/><tag k="name" v="Hospital Dr. Rafael Ángel Calderón Guardia"/></node>
  <node id="40" lat="0.0052" lon="10.0102"><tag k="place" v="village"/><tag k="name" v="Guápiles ñandú"/></node>
</osm>
"""


def test_names_with_accents_round_trip_through_both_files(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("node/30",))
  work = put_features(tmp_path, ACCENTED)
  road_graph.run(zone, work)
  graph = json.loads((zone.output_dir / "graph.json").read_bytes().decode("utf-8"))
  assert graph["hospitals"][0]["name"] == "Hospital Dr. Rafael Ángel Calderón Guardia"
  assert graph["communities"][0]["name"] == "Guápiles ñandú"
  assert json.loads((work / "communities.json").read_bytes().decode("utf-8"))[0]["osm_id"] == "node/40"


# --- INV-03: the half-up rule must be the one applied to each edge, not only the helper that implements it ---


def test_inv03_exact_halves_round_up_on_the_edges(tmp_path):
  # 14.4 km/h is exactly 4 m/s: the 890 m edge costs exactly 222.5 s, where half-to-even gives 222 and half-up 223.
  zone = make_zone(tmp_path, speed_model_kmh={k: 14.4 for k in ("trunk", "primary", "secondary", "tertiary")})
  road_graph.run(zone, extract(tmp_path))
  edges = json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))["edges"]
  ties = [e for e in edges if e["length_m"] % 4 == 2 and (e["length_m"] // 4) % 2 == 0]
  assert ties, "the fixture has no edge where half-up and half-even differ, so the test cannot tell them apart"
  for e in edges:
    assert e["time_s"] == math.floor(e["length_m"] / 4 + 0.5)


# --- INV-15: a one-way loop shorter than one edge is dropped; a long one is only split, which hides the filter ---

SHORT_LOOP = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="0.0000" lon="10.0000"/>
  <node id="2" lat="0.0000" lon="10.0040"/>
  <node id="3" lat="0.0000" lon="10.0080"/>
  <node id="4" lat="0.0020" lon="10.0040"/>
  <node id="5" lat="0.0020" lon="10.0060"/>
  <way id="1"><nd ref="1"/><nd ref="2"/><nd ref="3"/><tag k="highway" v="trunk"/><tag k="ref" v="901"/></way>
  <way id="2"><nd ref="2"/><nd ref="4"/><nd ref="5"/><nd ref="2"/><tag k="highway" v="tertiary"/><tag k="oneway" v="yes"/></way>
</osm>
"""


def test_inv15_short_one_way_loop_hanging_from_a_junction_is_dropped(tmp_path):
  zone = make_zone(tmp_path, referral_hospitals=("node/30",))
  work = extract(tmp_path)
  (work / "osm" / "roads.osm").write_text(SHORT_LOOP, encoding="utf-8")
  road_graph.run(zone, work)
  graph = json.loads((zone.output_dir / "graph.json").read_text(encoding="utf-8"))
  assert all(e["from"] != e["to"] for e in graph["edges"])
  assert {e["road"] for e in graph["edges"]} == {"Ruta 901"}


# --- INV-21: the extract date is the UTC day, also when the local day is another one ---


def test_inv21_date_is_the_utc_day_when_local_time_is_a_day_behind(tmp_path, monkeypatch):
  class FakeDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
      moment = datetime(2026, 11, 16, 2, 0, tzinfo=UTC)  # 20:00 on the 15th in Costa Rica
      return moment if tz is not None else moment.astimezone(timezone(timedelta(hours=-6))).replace(tzinfo=None)

  monkeypatch.setattr(road_graph, "datetime", FakeDatetime)
  monkeypatch.setattr(
    road_graph.urllib.request, "urlopen", lambda request, **_: FakeResponse((FIXTURE / "roads.osm").read_bytes())
  )
  monkeypatch.setattr(road_graph, "WORK_DIR", tmp_path / "work")
  monkeypatch.setattr(road_graph, "load_zone", lambda _id: make_zone(tmp_path))
  road_graph.main(["--area", "fixture", "--download"])
  assert (tmp_path / "work" / "fixture" / "osm" / "extract_date.txt").read_text(encoding="utf-8").strip() == "2026-11-16"
