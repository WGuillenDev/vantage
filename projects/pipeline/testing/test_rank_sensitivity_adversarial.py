import copy
import random

import pytest

from pipeline.rank_sensitivity import SensitivityError, build_report, rank_correlation, top_overlap
from test_rank_sensitivity import BASE_ORDER, HOSPITALS, UNITS, Stub, make_graph, scenarios_of, stub_for_speeds


def permutation(n: int, seed: int) -> list[str]:
  order = [f"T-{i:03d}" for i in range(1, n + 1)]
  random.Random(seed).shuffle(order)
  return order


@pytest.mark.parametrize("seed", range(20))
def test_inv_08_rank_correlation_matches_the_classic_formula_for_untied_ranks(seed: int):
  n = 30
  base_order = [f"T-{i:03d}" for i in range(1, n + 1)]
  run_order = permutation(n, seed)
  run_rank = {uid: rank for rank, uid in enumerate(run_order, start=1)}
  d2 = sum((rank - run_rank[uid]) ** 2 for rank, uid in enumerate(base_order, start=1))
  expected = 1 - 6 * d2 / (n * (n * n - 1))
  value, compared = rank_correlation(scenarios_of(base_order), scenarios_of(run_order))
  assert compared == n and value == pytest.approx(expected)
  assert rank_correlation(scenarios_of(run_order), scenarios_of(base_order))[0] == pytest.approx(expected)  # symmetric


@pytest.mark.parametrize("n", range(2, 120))
def test_inv_08_rank_correlation_stays_within_minus_one_and_one(n: int):
  order = [f"T-{i:03d}" for i in range(1, n + 1)]
  for run in (order, order[::-1]):
    value, _ = rank_correlation(scenarios_of(order), scenarios_of(run))
    assert -1.0 <= value <= 1.0


def test_inv_08_two_common_units_are_enough_for_a_correlation():
  base = scenarios_of(["T-01", "T-02"])
  assert rank_correlation(base, scenarios_of(["T-01", "T-02"])) == (pytest.approx(1.0), 2)
  assert rank_correlation(base, scenarios_of(["T-02", "T-01"])) == (pytest.approx(-1.0), 2)


@pytest.mark.parametrize("seed", range(10))
def test_inv_07_top_overlap_is_symmetric_and_never_above_k_or_the_unit_count(seed: int):
  a, b = scenarios_of(permutation(12, seed)), scenarios_of(permutation(12, seed + 100))
  for k in (5, 10, 20):
    overlap = top_overlap(a, b, k)
    assert overlap == top_overlap(b, a, k) and 0 <= overlap <= min(k, 12)
  assert top_overlap(a, b, 12) == 12


def test_inv_11_two_referral_hospitals_still_get_a_removal_run_each():
  graph = make_graph(hospitals=HOSPITALS[:2])
  answers = {(100, ("h1", "h2")): scenarios_of(BASE_ORDER), (100, ("h2",)): scenarios_of(BASE_ORDER), (100, ("h1",)): scenarios_of(BASE_ORDER)}
  scorer = Stub(answers, default=scenarios_of(BASE_ORDER))
  result = build_report(graph, UNITS, scenarios_of(BASE_ORDER), scorer)
  assert [r["value"] for r in result["runs"] if r["kind"] == "hospital"] == ["Hospital 1", "Hospital 2"]
  assert result["skipped"] == []
  last_two = [[h["id"] for h in g["hospitals"]] for g, _ in scorer.calls[-2:]]
  assert last_two == [["h2"], ["h1"]]


def test_inputs_are_never_modified_by_a_report():
  graph, scenarios, units = make_graph(), scenarios_of(BASE_ORDER), copy.deepcopy(UNITS)
  before = copy.deepcopy((graph, scenarios, units))
  build_report(graph, units, scenarios, stub_for_speeds(BASE_ORDER, BASE_ORDER))
  assert (graph, scenarios, units) == before


def test_inv_10_the_report_does_not_depend_on_the_order_of_candidates_in_the_file():
  scenarios = scenarios_of(BASE_ORDER)
  shuffled = copy.deepcopy(scenarios)
  random.Random(3).shuffle(shuffled["candidates"])
  first = build_report(make_graph(), UNITS, scenarios, Stub({}, default=scenarios))
  second = build_report(make_graph(), UNITS, shuffled, Stub({}, default=shuffled))
  assert first["baseline"] == second["baseline"] and first["runs"] == second["runs"]


@pytest.mark.parametrize("change", ["baseline_row", "schema_version"])
def test_inv_02_a_difference_outside_the_candidates_also_breaks_reproducibility(change: str):
  scenarios = scenarios_of(BASE_ORDER)
  scenarios["baseline"] = [{"community_id": "c1", "time_s": 100, "hospital_id": "h1"}]
  scenarios["schema_version"] = "0.3"
  scored = copy.deepcopy(scenarios)
  if change == "baseline_row":
    scored["baseline"][0]["time_s"] = 101
  else:
    scored["schema_version"] = "0.2"
  with pytest.raises(SensitivityError, match="baseline is not reproducible"):
    build_report(make_graph(), UNITS, scenarios, Stub({}, default=scored))
