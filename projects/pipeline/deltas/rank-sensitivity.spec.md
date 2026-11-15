---
slice: rank-sensitivity
---

# rank-sensitivity: spec

> Measures how much the ranking of closure units changes when the model's assumptions change, and writes the result as a report (task P10, `RELIABILITY.md` step 1).

## Intent

The ranking depends on assumptions the project cannot verify: one constant speed per road class and which hospitals count as referral. The claim "the ranking is stable under these assumptions" is worth saying only if it was measured, and it must say plainly when it was not. This slice varies each assumption, recomputes, and reports how much of the top of the list and the order survive, using thresholds fixed on 14 Nov before any result.

## Scope

Owns:

- The perturbations: speeds ×0.8 and ×1.2 for every road class, and the removal of each referral hospital in turn.
- Re-scoring the closure units in memory with each change, using the scoring rules of `impact-scoring`.
- The comparison with the baseline ranking and the report `reports/<id>/sensitivity.json`, committed as evidence.

Non-goals:

- Judging the hospital removals: they change the ranking by nature, so they are reported, not graded.
- Changing the model or its parameters when a result is poor: that is a decision for the team, after reading the report.
- Validating the ranking against real closures: not what consequence measures (`RELIABILITY.md` §5).
- Publishing the report or adding it to the contract.
- Perturbations beyond the list (population method, closure units, alternate routes).

## Contract

Inputs: the zone (`area-config`) and its built files in `output/<id>/`, from `pipeline-run`, and `work/<id>/closure_units.json`. Nothing is downloaded and the network is not rebuilt.

Output: `projects/pipeline/reports/<id>/sensitivity.json`, with no timestamps:

| Field | Content |
|---|---|
| `thresholds` | `{ "top5_min_overlap": 4 }`, the fixed rule. |
| `baseline` | The unit ids in rank order, and the number of units with impact. |
| `runs[]` | One entry per perturbation: `kind` (`speed` or `hospital`), the parameter value (factor or removed hospital name), `top5_overlap`, `top10_overlap`, `rank_correlation`, `compared_units` and, for `speed`, `passes`. |
| `verdict` | `"pass"`, `"fail"` or `"insufficient_units"`. |

Definitions:

| Term | Definition |
|---|---|
| Unit with impact | A unit with at least one affected community. |
| Top-k overlap | The number of unit ids in both the baseline's top k and the perturbed run's top k (by `rank`). |
| Rank correlation | Spearman correlation of the ranks, with average ranks for ties, over the units with impact in both runs; `null` with fewer than 2 such units. |
| Speed perturbation | Every `time_s` of `graph.json` divided by the factor and rounded half up; population and the network are unchanged. |
| Perturbation passes | A `speed` run with `top5_overlap` of at least 4. |
| Verdict | `pass` if both `speed` runs pass; `fail` if any does not; `insufficient_units` if the baseline has fewer than 5 units with impact. Hospital runs never affect it. |

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  When rank-sensitivity runs with no perturbation, the scenarios it computes are identical to `output/<id>/scenarios.json`.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  If the unperturbed run differs from `output/<id>/scenarios.json`, then rank-sensitivity exits non-zero with an English error saying the baseline is not reproducible and writes no report.
- INV-03 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  When rank-sensitivity finishes, the report has one run for speed ×0.8, one for ×1.2, and one for each referral hospital removed.
- INV-06 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  When rank-sensitivity removes a hospital, the recomputed network has every other referral hospital and not the removed one.
- INV-07 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  When rank-sensitivity reports a run, its top-k overlap equals the number of unit ids shared by the baseline's and the run's top k by `rank`.
- INV-08 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  When rank-sensitivity reports a rank correlation, it is the Spearman correlation, with average ranks for ties, over the units with impact in both runs, and `null` when fewer than 2 such units exist.
- INV-09 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  When rank-sensitivity grades a run, `passes` is true exactly when it is a speed run with a top-5 overlap of at least 4, and hospital runs have no `passes`.
- INV-10 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  When the baseline has fewer than 5 units with impact, rank-sensitivity writes the verdict `insufficient_units` and no `passes`.
- INV-11 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  If the zone has a single referral hospital, then rank-sensitivity skips the hospital removal, records that it did, and does not fail.
- INV-14 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py]
  If `output/<id>/scenarios.json` is missing, then rank-sensitivity exits non-zero with an English error that says to run `make all` and writes no report.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns each into `test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rank_sensitivity.py` against a small synthetic zone): INV-01, INV-02, INV-03, INV-06 to INV-11, INV-14.

- **A failed verdict is a finding:** if the top 5 does not share 4 units, the report says so, and the presentation reports it with its number, as with S2, S2c and S5. It is not tuned until it passes.
- **Few units with impact:** if the Ruta 32 baseline has fewer than 5 units with impact, the verdict is `insufficient_units`. Depends on `closure-units` and the first real run.
- **Snapping distance not varied (purged 14 Nov):** `RELIABILITY.md` step 1 also lists 1 500 and 5 000 m. Varying it means re-snapping and reassigning population (three stages); it was dropped to keep this slice to the one stage it needs. Add it only if the first report suggests the ranking is fragile.
- **Tie handling in the top 5:** units tied in the ranking order by the rules of `impact-scoring`; a perturbation can reorder ties without a real change. Not corrected.
- **`make` target:** `make sensitivity AREA=<id>` is added with this slice; `pipeline-run` does not run it in `make all`.
- **Docs out of sync:** `RELIABILITY.md` step 1 lists the snapping perturbations; a person updates it.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 run, when a person reads `reports/ruta-32/sensitivity.json`, then the report states the verdict and the top-5 overlap of each of its runs (two speed, one per hospital removed), so the person can quote the verdict and its numbers in the presentation.
