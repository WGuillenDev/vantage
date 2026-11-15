"""Measures how much the Ruta 32 ranking changes with the maximum snapping distance (RELIABILITY.md step 1).

For each distance it copies the pipeline to a temporary folder, changes MAX_SNAP_M there, runs pipeline-run and compares
the result with the real output. The real code and output are not touched. 3000 m is the value in use, run as a control:
its result must equal the committed output.

Needs the work/ files of a real run (OSM extract, WorldPop raster, IMERG cells). Run from the repo root:
  uv run --project projects/pipeline python projects/pipeline/spikes/snap_distance/measure.py
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pipeline.rank_sensitivity import rank_correlation, top_overlap

ROOT = Path(__file__).resolve().parents[4]
PIPELINE = ROOT / "projects" / "pipeline"
ZONE = "ruta-32"
DISTANCES = (3000, 1500, 5000)
IGNORE = shutil.ignore_patterns(".venv", "__pycache__", "*.pyc")


def run_variant(distance: int, tmp: Path) -> Path:
  copy = tmp / "pipeline"
  shutil.copytree(PIPELINE / "configs", copy / "configs")
  shutil.copytree(PIPELINE / "source", copy / "source", ignore=IGNORE)
  for name in ("pyproject.toml", "uv.lock", ".python-version"):
    shutil.copy(PIPELINE / name, copy / name)
  (copy / "work").mkdir()
  shutil.copytree(PIPELINE / "work" / ZONE, copy / "work" / ZONE)
  shutil.copytree(PIPELINE / "work" / "worldpop", copy / "work" / "worldpop")
  shutil.copytree(ROOT / "projects" / "contract" / "schemas", tmp / "contract" / "schemas")
  road_graph = copy / "source" / "pipeline" / "road_graph.py"
  text = road_graph.read_text(encoding="utf-8")
  road_graph.write_text(re.sub(r"^MAX_SNAP_M = \d+", f"MAX_SNAP_M = {distance}", text, flags=re.M), encoding="utf-8")
  subprocess.run(["uv", "run", "--project", str(copy), "pipeline-run", "--area", ZONE], check=True, capture_output=True)
  return copy / "output" / ZONE


def read(path: Path, name: str):
  return json.loads((path / name).read_text(encoding="utf-8"))


def ranking(scenarios: dict) -> dict:
  return {"candidates": [{"id": c["id"], "rank": c["rank"], "affected_community_ids": c["affected_community_ids"]} for c in scenarios["candidates"]]}


def main() -> None:
  real = PIPELINE / "output" / ZONE
  base = read(real, "scenarios.json")
  results = []
  for distance in DISTANCES:
    with tempfile.TemporaryDirectory() as folder:
      out = run_variant(distance, Path(folder))
      scenarios, graph = read(out, "scenarios.json"), read(out, "graph.json")
    same_units = sorted(c["id"] for c in scenarios["candidates"]) == sorted(c["id"] for c in base["candidates"])
    correlation, compared = rank_correlation(ranking(base), ranking(scenarios))
    row = {
      "max_snap_m": distance,
      "communities": len(graph["communities"]),
      "communities_with_population": sum(1 for c in graph["communities"] if c["population"] is not None),
      "units": len(scenarios["candidates"]),
      "units_with_impact": sum(1 for c in scenarios["candidates"] if c["affected_community_ids"]),
      "isolated_pairs": sum(len(c["isolated_community_ids"]) for c in scenarios["candidates"]),
      "suspect_pairs": sum(len(c["suspect_isolated_community_ids"]) for c in scenarios["candidates"]),
      "same_unit_ids_as_real": same_units,
      "top5_overlap": top_overlap(ranking(base), ranking(scenarios), 5),
      "top10_overlap": top_overlap(ranking(base), ranking(scenarios), 10),
      "top20_overlap": top_overlap(ranking(base), ranking(scenarios), 20),
      "rank_correlation": None if correlation is None else round(correlation, 3),
      "compared_units": compared,
      "scenarios_equal_to_real_output": scenarios == base,
    }
    results.append(row)
    print(json.dumps(row))
  verdict = "pass" if all(r["top5_overlap"] >= 4 for r in results) else "fail"
  report = {"zone": ZONE, "threshold": {"top5_min_overlap": 4}, "runs": results, "verdict": verdict}
  (Path(__file__).parent / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
  print("verdict", verdict)


if __name__ == "__main__":
  main()
