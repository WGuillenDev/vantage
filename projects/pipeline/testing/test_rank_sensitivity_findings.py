"""Adversarial tests from `breaker` for malformed inputs: each must end in a clean SensitivityError or a correct result, never a traceback."""

import copy
import json
from pathlib import Path

import pytest

from pipeline.rank_sensitivity import SensitivityError, build_report, execute
from test_rank_sensitivity import BASE_ORDER, UNITS, Stub, make_files, make_graph, scenarios_of


def test_inv_01_a_scorer_that_returns_tuples_where_the_file_has_lists_still_reproduces_the_baseline():
  scenarios = scenarios_of(BASE_ORDER)
  from_file = json.loads(json.dumps(scenarios))  # what scenarios.json looks like once loaded
  scenarios["candidates"][0]["affected_community_ids"] = ("c1",)  # same content, a tuple in memory
  assert build_report(make_graph(), UNITS, from_file, Stub({}, default=scenarios))["verdict"] == "pass"


@pytest.mark.parametrize(
  "broken",
  [
    lambda s: s.pop("candidates"),
    lambda s: s["candidates"][0].pop("rank"),
    lambda s: s["candidates"][0].pop("affected_community_ids"),
    lambda s: s["candidates"][0].update(rank=None),
  ],
)
def test_inv_02_a_scenarios_file_with_a_missing_field_is_a_clean_error(broken):
  scenarios = scenarios_of(BASE_ORDER)
  broken(scenarios)
  with pytest.raises(SensitivityError):
    build_report(make_graph(), UNITS, scenarios, Stub({}, default=copy.deepcopy(scenarios)))


@pytest.mark.parametrize("missing", ["hospitals", "edges"])
def test_inv_14_a_graph_file_without_hospitals_or_edges_is_a_clean_error(tmp_path: Path, missing: str):
  output, work, reports = make_files(tmp_path, scenarios_of(BASE_ORDER))
  graph = make_graph()
  del graph[missing]
  (output / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
  with pytest.raises(SensitivityError, match=missing):
    execute(output, work, reports, Stub({}, default=scenarios_of(BASE_ORDER)))
  assert not (reports / "sensitivity.json").exists()


@pytest.mark.parametrize("name", ["graph.json", "scenarios.json"])
def test_inv_14_a_json_file_that_is_not_an_object_is_a_clean_error(tmp_path: Path, name: str):
  output, work, reports = make_files(tmp_path, scenarios_of(BASE_ORDER))
  (output / name).write_text("[]", encoding="utf-8")
  with pytest.raises(SensitivityError, match=name):
    execute(output, work, reports, Stub({}, default=scenarios_of(BASE_ORDER)))
  assert not (reports / "sensitivity.json").exists()
