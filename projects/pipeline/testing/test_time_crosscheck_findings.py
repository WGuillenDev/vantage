"""Adversarial tests from `breaker` for malformed inputs: each must end in a clean CrossCheckError, never a traceback."""

import json
from pathlib import Path

import pytest

from pipeline.time_crosscheck import CrossCheckError, build_report, load_references
from test_time_crosscheck import Router, reference, world, write_references

TODAY = "2026-11-15"


def test_baseline_row_for_a_community_missing_from_the_graph_is_a_clean_error():
  graph, scenarios = world([100.0, 200.0])
  scenarios["baseline"].append({"community_id": "c99", "time_s": 50.0, "hospital_id": "h1"})
  with pytest.raises(CrossCheckError, match="c99"):
    build_report(graph, scenarios, [], Router([100.0] * 3), lambda s: None, TODAY)


def test_baseline_row_for_a_hospital_missing_from_the_graph_is_a_clean_error():
  graph, scenarios = world([100.0])
  scenarios["baseline"][0]["hospital_id"] = "h99"
  with pytest.raises(CrossCheckError, match="h99"):
    build_report(graph, scenarios, [], Router([100.0]), lambda s: None, TODAY)


@pytest.mark.parametrize("missing", ["community_id", "hospital_id"])
def test_inv_07_a_reference_without_community_or_hospital_is_a_clean_error(tmp_path: Path, missing: str):
  entry = reference()
  del entry[missing]
  with pytest.raises(CrossCheckError, match=rf"entry 1 .*{missing}"):
    load_references(write_references(tmp_path, [entry]))


@pytest.mark.parametrize("body", ['{"code": "Ok", "routes": [{}]}', "[]", '{"code": "Ok", "routes": [{"duration": "12"}]}', '{"code": "Ok", "routes": [null]}'])
def test_inv_10_an_answer_with_an_unexpected_shape_is_a_clean_error(body: str):
  graph, scenarios = world([100.0])
  with pytest.raises(CrossCheckError):
    build_report(graph, scenarios, [], lambda url, headers: (200, body), lambda s: None, TODAY)


def test_inv_07_a_reference_of_infinite_minutes_is_an_error(tmp_path: Path):
  path = tmp_path / "reference_times.json"
  path.write_text(json.dumps([reference(minutes=float("inf"))]), encoding="utf-8")  # writes Infinity
  with pytest.raises(CrossCheckError, match="minutes"):
    load_references(path)
