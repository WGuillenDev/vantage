import pytest

from pipeline import manual_review
from pipeline.manual_review import ReviewError, build_sheet, choose_units, execute_prepare, execute_summarize
from test_manual_review import filled, many_isolated, read_back, unit, write_inputs


def test_adv_population_zero_sorts_before_unknown():
  sheet = build_sheet(*many_isolated([None, 0, 7]))
  assert [c["community_id"] for c in sheet["units"][0]["communities"]] == ["c3", "c2", "c1"]


def test_adv_unit_choice_does_not_depend_on_the_order_of_the_input():
  units = [unit("T-01", 1, 10), unit("T-02", 2, 20), unit("T-03", 3, 30), unit("T-04", 4, 40)]
  forward = [u["id"] for u in choose_units({"candidates": units})]
  backward = [u["id"] for u in choose_units({"candidates": list(reversed(units))})]
  assert forward == backward == ["T-01", "T-02", "T-04"]


def test_adv_a_failed_prepare_leaves_no_sheet_so_it_can_be_rerun(tmp_path):
  output, work, reports = write_inputs(tmp_path)
  (work / "communities.json").write_text("[]", encoding="utf-8")
  with pytest.raises(ReviewError):
    execute_prepare(output, work, reports)
  assert not (reports / "manual_review.json").exists()


def test_adv_summarize_twice_gives_the_same_file(tmp_path):
  filled(tmp_path, ["real"] * 4 + ["oneway_artifact"])
  execute_summarize(tmp_path)
  first = (tmp_path / "manual_review.json").read_text(encoding="utf-8")
  execute_summarize(tmp_path)
  assert (tmp_path / "manual_review.json").read_text(encoding="utf-8") == first
  assert read_back(tmp_path)["verdict"] == "pass"


def test_adv_main_summarize_without_a_sheet_exits_with_a_message(tmp_path, monkeypatch):
  monkeypatch.setattr(manual_review, "load_zone", lambda zone_id: type("Zone", (), {"id": "z", "output_dir": tmp_path})())
  monkeypatch.setattr(manual_review, "REPORTS_DIR", tmp_path / "reports_root")
  with pytest.raises(SystemExit) as exc:
    manual_review.main(["summarize", "--area", "z"])
  assert "not found" in str(exc.value)


# Mutation survivors: the pass threshold and the median position for an odd number of units.


def test_adv_share_between_75_and_80_percent_fails(tmp_path):
  filled(tmp_path, ["real"] * 7 + ["snapping_artifact"] * 2)  # 7/9 = 0.78
  execute_summarize(tmp_path)
  assert read_back(tmp_path)["verdict"] == "fail"


def test_adv_median_with_an_odd_number_of_impact_units_is_the_middle_one():
  units = [unit(f"T-0{i}", i, 10 * i) for i in range(1, 6)]
  assert [u["id"] for u in choose_units({"candidates": units})] == ["T-01", "T-03", "T-05"]
