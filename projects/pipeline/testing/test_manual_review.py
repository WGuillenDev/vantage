import json
import math

import pytest

from pipeline import manual_review
from pipeline.manual_review import (
  ReviewError,
  build_sheet,
  choose_units,
  execute_prepare,
  execute_summarize,
  main,
)


def unit(uid: str, rank: int, length: float = 100.0, affected: list[str] | None = None, isolated: list[str] | None = None):
  return {
    "id": uid,
    "rank": rank,
    "length_m": length,
    "affected_community_ids": affected if affected is not None else ["c1"],
    "isolated_community_ids": isolated or [],
  }


def ids(candidates: list[dict]) -> list[str]:
  return [u["id"] for u in choose_units({"candidates": candidates})]


# INV-01


def test_inv_01_picks_rank_one_median_of_impact_units_and_longest():
  units = [unit("T-01", 1, 10), unit("T-02", 2, 20), unit("T-03", 3, 30), unit("T-04", 4, 40), unit("T-05", 5, 50), unit("T-06", 6, 999)]
  # n=6 -> position ceil(6/2)=3 -> T-03; longest T-06
  assert ids(units) == ["T-01", "T-03", "T-06"]


def test_inv_01_median_ignores_units_without_affected_communities():
  units = [unit("T-01", 1, 10), unit("T-02", 2, 20, affected=[]), unit("T-03", 3, 30), unit("T-04", 4, 40), unit("T-05", 5, 50)]
  # impact units: T-01, T-03, T-04, T-05 -> n=4 -> position 2 -> T-03; longest T-05
  assert ids(units) == ["T-01", "T-03", "T-05"]


def test_inv_01_longest_ties_go_to_the_lower_id_number():
  # The tied units have no impact, so only the "longest" rule can pick them; T-9 beats T-10 by number, not by text.
  units = [unit("T-01", 1, 5), unit("T-10", 2, 90, affected=[]), unit("T-9", 3, 90, affected=[])]
  assert ids(units) == ["T-01", "T-9"]


def test_inv_01_a_unit_already_chosen_is_not_chosen_again():
  units = [unit("T-01", 1, 500), unit("T-02", 2, 10), unit("T-03", 3, 20)]
  # A = T-01, B = position 2 of 3 = T-02, C longest = T-01 already taken -> next longest T-03
  assert ids(units) == ["T-01", "T-02", "T-03"]


def test_inv_01_with_fewer_than_three_units_takes_as_many_as_exist():
  assert ids([unit("T-01", 1)]) == ["T-01"]
  assert ids([unit("T-01", 1), unit("T-02", 2, 5)]) == ["T-01", "T-02"]
  assert ids([]) == []


def test_inv_01_records_why_each_unit_was_chosen():
  chosen = choose_units({"candidates": [unit("T-01", 1, 10), unit("T-02", 2, 20), unit("T-03", 3, 30)]})
  assert [u["why"] for u in chosen] == ["highest_criticality", "median_criticality", "longest"]


# World for INV-03 / INV-05


def node(nid: str, lon: float) -> dict:
  return {"id": nid, "lon": lon, "lat": 10.0}


def edge(eid: str, a: str, b: str, oneway: bool = False) -> dict:
  return {"id": eid, "from": a, "to": b, "length_m": 1, "time_s": 1, "road": "r", "oneway": oneway, "candidate_id": None}


def world():
  """Unit T-01 closes e1 (n1 -> n2). The hospital is at nh.

  c1: node n3, linked to the hospital only by a one-way edge that points away from the hospital.
  c2: node n2, endpoint of the closed edge, otherwise cut off.
  c3: node n7, no edges at all.
  """
  graph = {
    "nodes": [node(n, -84.0 + 0.001 * i) for i, n in enumerate(["n1", "n2", "n3", "nh", "n7"])],
    "edges": [
      edge("e1", "n1", "n2"),
      edge("e2", "nh", "n3", oneway=True),
      edge("e3", "n1", "nh"),
    ],
    "hospitals": [{"id": "h1", "name": "H", "node": "nh"}],
    "communities": [
      {"id": "c1", "name": "One", "node": "n3", "population": 50},
      {"id": "c2", "name": "Snap", "node": "n2", "population": 100},
      {"id": "c3", "name": "Null", "node": "n7", "population": None},
    ],
  }
  scenarios = {
    "baseline": [],
    "candidates": [
      {
        "id": "T-01",
        "rank": 1,
        "length_m": 10.0,
        "edge_ids": ["e1"],
        "affected_community_ids": ["c1", "c2", "c3"],
        "isolated_community_ids": ["c1", "c2", "c3"],
      }
    ],
  }
  units = [{"id": "T-01", "edge_ids": ["e1"], "length_m": 10.0}]
  originals = [
    {"id": "c1", "osm_id": "node/1", "lon": -84.0 + 0.002, "lat": 10.0},
    {"id": "c2", "osm_id": "node/2", "lon": -84.0 + 0.001, "lat": 10.001},
    {"id": "c3", "osm_id": "node/3", "lon": -84.0 + 0.004, "lat": 10.0},
  ]
  return graph, scenarios, units, originals


def communities_of(sheet: dict) -> dict:
  return {c["community_id"]: c for u in sheet["units"] for c in u["communities"]}


# INV-03


def many_isolated(populations: list):
  graph, scenarios, units, originals = world()
  graph["communities"] = [{"id": f"c{i}", "name": f"C{i}", "node": "n7", "population": p} for i, p in enumerate(populations, start=1)]
  originals = [{"id": c["id"], "osm_id": "x", "lon": -84.0, "lat": 10.0} for c in graph["communities"]]
  scenarios["candidates"][0]["isolated_community_ids"] = [c["id"] for c in graph["communities"]]
  return graph, scenarios, units, originals


def test_inv_03_lists_exactly_the_isolated_communities():
  graph, scenarios, units, originals = world()
  scenarios["candidates"][0]["isolated_community_ids"] = ["c1"]
  assert list(communities_of(build_sheet(graph, scenarios, units, originals))) == ["c1"]


def test_inv_03_orders_by_population_desc_null_last_then_id_number():
  sheet = build_sheet(*many_isolated([10, None, 50, 10, None]))
  assert [c["community_id"] for c in sheet["units"][0]["communities"]] == ["c3", "c1", "c4", "c2", "c5"]


def test_inv_03_id_number_not_text_breaks_ties():
  sheet = build_sheet(*many_isolated([5] * 12))
  assert [c["community_id"] for c in sheet["units"][0]["communities"]] == [f"c{i}" for i in range(1, 13)]


def test_inv_03_caps_the_list_at_20():
  listed = build_sheet(*many_isolated(list(range(100, 75, -1))))["units"][0]["communities"]
  assert len(listed) == 20 and listed[0]["community_id"] == "c1" and listed[-1]["community_id"] == "c20"


# INV-05


def haversine(lon1, lat1, lon2, lat2):
  p1, p2 = math.radians(lat1), math.radians(lat2)
  a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
  return 2 * 6371008.8 * math.asin(math.sqrt(a))


def test_inv_05_distance_is_from_original_coordinates_to_the_snapped_node():
  graph, scenarios, units, originals = world()
  c2 = communities_of(build_sheet(graph, scenarios, units, originals))["c2"]
  n2 = next(n for n in graph["nodes"] if n["id"] == "n2")
  assert c2["distance_to_node_m"] == pytest.approx(haversine(-84.0 + 0.001, 10.001, n2["lon"], n2["lat"]), abs=0.1)
  assert c2["distance_to_node_m"] > 100  # the latitude offset alone is about 111 m


def test_inv_05_joined_ignoring_direction_suggests_oneway_artifact():
  c1 = communities_of(build_sheet(*world()))["c1"]
  assert c1["joined_ignoring_direction"] is True
  assert c1["node_is_closed_endpoint"] is False
  assert c1["suggested_class"] == "oneway_artifact"


def test_inv_05_closed_endpoint_not_joined_suggests_snapping_artifact():
  # n2 only reaches the hospital through the closed edge e1, which must not count as a link.
  c2 = communities_of(build_sheet(*world()))["c2"]
  assert c2["node_is_closed_endpoint"] is True
  assert c2["joined_ignoring_direction"] is False
  assert c2["suggested_class"] == "snapping_artifact"


def test_inv_05_neither_cause_suggests_null():
  assert communities_of(build_sheet(*world()))["c3"]["suggested_class"] is None


def test_inv_05_oneway_wins_over_snapping_when_both_hold():
  graph, scenarios, units, originals = world()
  graph["communities"][0]["node"] = "n1"  # endpoint of the closed edge, still linked to the hospital by e3
  c1 = communities_of(build_sheet(graph, scenarios, units, originals))["c1"]
  assert c1["node_is_closed_endpoint"] is True and c1["joined_ignoring_direction"] is True
  assert c1["suggested_class"] == "oneway_artifact"


def test_inv_05_missing_original_coordinates_is_an_english_error():
  graph, scenarios, units, originals = world()
  with pytest.raises(ReviewError, match=r"communities\.json.*c2"):
    build_sheet(graph, scenarios, units, originals[:1])


# INV-06 / INV-07


def write_inputs(tmp_path):
  graph, scenarios, units, originals = world()
  output, work, reports = tmp_path / "output", tmp_path / "work", tmp_path / "reports"
  output.mkdir()
  work.mkdir()
  (output / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
  (output / "scenarios.json").write_text(json.dumps(scenarios), encoding="utf-8")
  (work / "closure_units.json").write_text(json.dumps(units), encoding="utf-8")
  (work / "communities.json").write_text(json.dumps(originals), encoding="utf-8")
  return output, work, reports


def test_inv_06_prepare_leaves_every_person_field_empty_and_has_no_verdict(tmp_path):
  output, work, reports = write_inputs(tmp_path)
  sheet = json.loads(execute_prepare(output, work, reports).read_text(encoding="utf-8"))
  assert sheet["reviewer"] == "" and sheet["reviewed_on"] == ""
  assert "verdict" not in sheet and "summary" not in sheet
  listed = [c for u in sheet["units"] for c in u["communities"]]
  assert listed and all(c["class"] == "" and c["note"] == "" for c in listed)


def test_inv_07_prepare_refuses_to_overwrite_an_existing_sheet(tmp_path):
  output, work, reports = write_inputs(tmp_path)
  reports.mkdir()
  existing = reports / "manual_review.json"
  existing.write_text('{"keep": "me"}', encoding="utf-8")
  with pytest.raises(ReviewError, match="already exists"):
    execute_prepare(output, work, reports)
  assert existing.read_text(encoding="utf-8") == '{"keep": "me"}'


def test_inv_07_main_exits_with_the_english_message(tmp_path, monkeypatch):
  output, work, reports = write_inputs(tmp_path)
  monkeypatch.setattr(manual_review, "load_zone", lambda zone_id: type("Zone", (), {"id": "z", "output_dir": output})())
  monkeypatch.setattr(manual_review, "WORK_DIR", tmp_path / "work_root")
  monkeypatch.setattr(manual_review, "REPORTS_DIR", tmp_path / "reports_root")
  (tmp_path / "reports_root" / "z").mkdir(parents=True)
  (tmp_path / "reports_root" / "z" / "manual_review.json").write_text("{}", encoding="utf-8")
  with pytest.raises(SystemExit) as exc:
    main(["prepare", "--area", "z"])
  assert "already exists" in str(exc.value)


# summarize


def filled(tmp_path, classes: list[str], reviewer="Ana", reviewed_on="2026-11-15"):
  sheet = {
    "reviewer": reviewer,
    "reviewed_on": reviewed_on,
    "units": [
      {
        "id": "T-01",
        "why": "highest_criticality",
        "communities": [{"community_id": f"c{i}", "class": cls, "note": ""} for i, cls in enumerate(classes, start=1)],
      }
    ],
  }
  path = tmp_path / "manual_review.json"
  path.write_text(json.dumps(sheet), encoding="utf-8")
  return path


def read_back(tmp_path) -> dict:
  return json.loads((tmp_path / "manual_review.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("field", ["reviewer", "reviewed_on"])
def test_inv_09_missing_reviewer_or_date_fails_and_leaves_the_sheet(tmp_path, field):
  path = filled(tmp_path, ["real"], **{field: "  "})
  before = path.read_text(encoding="utf-8")
  with pytest.raises(ReviewError, match=field):
    execute_summarize(tmp_path)
  assert path.read_text(encoding="utf-8") == before


def test_inv_10_an_unknown_class_names_the_community_and_leaves_the_sheet(tmp_path):
  path = filled(tmp_path, ["real", "maybe"])
  before = path.read_text(encoding="utf-8")
  with pytest.raises(ReviewError, match="c2"):
    execute_summarize(tmp_path)
  assert path.read_text(encoding="utf-8") == before


def test_inv_11_any_unclassified_community_makes_the_verdict_incomplete(tmp_path):
  filled(tmp_path, ["real", "real", ""])
  execute_summarize(tmp_path)
  sheet = read_back(tmp_path)
  assert sheet["verdict"] == "incomplete"
  assert sheet["summary"]["unclassified"] == 1


def test_inv_11_a_sheet_with_no_listed_communities_is_incomplete(tmp_path):
  filled(tmp_path, [])
  execute_summarize(tmp_path)
  assert read_back(tmp_path)["verdict"] == "incomplete"


def test_inv_12_exactly_80_percent_real_passes(tmp_path):
  filled(tmp_path, ["real"] * 4 + ["snapping_artifact"])
  execute_summarize(tmp_path)
  sheet = read_back(tmp_path)
  assert sheet["verdict"] == "pass"
  assert sheet["summary"]["share_real"] == pytest.approx(0.8)
  assert sheet["summary"]["counts"] == {"real": 4, "snapping_artifact": 1, "oneway_artifact": 0, "outside_network": 0}


def test_inv_12_below_80_percent_real_fails(tmp_path):
  filled(tmp_path, ["real"] * 3 + ["oneway_artifact", "outside_network"])
  execute_summarize(tmp_path)
  assert read_back(tmp_path)["verdict"] == "fail"


def test_inv_12_rerunning_summarize_replaces_the_old_verdict(tmp_path):
  filled(tmp_path, ["real", ""])
  execute_summarize(tmp_path)
  assert read_back(tmp_path)["verdict"] == "incomplete"
  filled(tmp_path, ["real", "real"])
  execute_summarize(tmp_path)
  assert read_back(tmp_path)["verdict"] == "pass"
