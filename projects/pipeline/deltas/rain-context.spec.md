---
slice: rain-context
---

# rain-context: spec

> Reads daily IMERG rainfall for a zone, writes `rain.csv`, and adds recent-rain context (`exposure`) to each closure unit in `scenarios.json` (task E1).

## Intent

After the spikes, rain is context and not a signal: 3 of 8 closures sat above the 75th percentile of 12-day rain, against 6 needed (S5). The "Exposure" block still helps a reader see how wet the area has been recently, as a hypothesis and never as a cause. This slice produces that context reproducibly, from NASA IMERG Late.

## Scope

Owns:

- Downloading IMERG Late daily precipitation for the cells that cover the zone (`make imerg`, the only step of this slice that uses the network).
- Writing `output/<id>/rain.csv`: one daily area mean over the zone.
- Per closure unit, the 12-day accumulated rain ending at the zone's `rain.end`, written to `exposure.rain_mm_12d` in `scenarios.json`.

Non-goals:

- Any claim that rain precedes, predicts or causes closures. S5 found no such relation; the label "hipótesis" belongs to the interface (`segment-detail`).
- Soil moisture: removed from the contract in 0.3 after S2c failed (D7).
- Writing `meta.json`: `pipeline-run` records the product, version and period from this slice's `source.json`.
- Choosing the period: the zone config (`rain.start`, `rain.end`).
- Rainfall at the scale of a hillside: IMERG cells are 0.1° (about 10 km), so units in the same cell share a value, and this is said, not hidden.

## Contract

Inputs:

| Input | Notes |
|---|---|
| Zone | A loaded zone from `area-config`: `id`, `bbox`, `rain.start` and `rain.end`. |
| IMERG download | `work/<id>/imerg/cells.csv` (`date,cell_lon,cell_lat,precip_mm`, one row per day and cell) and `work/<id>/imerg/source.json` (`product`, `version`, `start`, `end`), written by `make imerg`. Cells are those whose extent intersects the zone `bbox`. |
| `output/<id>/scenarios.json` | From `impact-scoring`, with no `exposure`. |
| `output/<id>/graph.json` | For the geometry of each unit's edges. |
| `work/<id>/closure_units.json` | Which edges form each unit. |

Outputs: `output/<id>/rain.csv` and `output/<id>/scenarios.json`, identical to the input except that each unit gains `exposure: { "rain_mm_12d" }` (schema 0.3).

The download step needs an Earthdata account with the "NASA GESDISC DATA ARCHIVE" application authorized (S5). Credentials stay in the user's environment and are never committed.

Rules:

| Topic | Rule |
|---|---|
| Daily mean | `precip_mm` of `rain.csv` is the mean of the daily values of the cells whose centre lies inside `bbox`, rounded half up to 3 decimals. |
| Period | One row per day from `rain.start` to `rain.end`, ascending, no gaps, UTC days. |
| Window | The 12 days ending at `rain.end`, inclusive; it must lie inside the period. |
| Unit value | For each distinct cell touched by any point of the unit's edge geometries, the sum of its daily values over the window; the unit's `rain_mm_12d` is the mean of those sums, rounded half up to 1 decimal. |
| Missing data | A missing day or cell never becomes `0` and never gets a partial value. |

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rain_context.py]
  When rain-context finishes, the `rain.csv` and `scenarios.json` it wrote pass `make validate`, and `scenarios.json` differs from its input only in `exposure`.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rain_context.py]
  When rain-context writes `rain.csv`, it has one row per day from `rain.start` to `rain.end`, in ascending order, with no gaps.
- INV-03 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rain_context.py]
  When rain-context writes a day's `precip_mm`, it equals the mean of that day's values over the cells whose centre lies inside `bbox`, rounded half up to 3 decimals.
- INV-04 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rain_context.py]
  If a day between `rain.start` and `rain.end` is missing for any cell, or the 12 days ending at `rain.end` are not all inside the period, then rain-context exits non-zero with an English error naming the date or the period and writes no output.
- INV-05 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rain_context.py]
  When rain-context writes a unit's `rain_mm_12d`, it equals the mean, over the distinct cells touched by the unit's edge geometries, of each cell's rain over the 12 days ending at `rain.end`, rounded half up to 1 decimal.
- INV-14 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rain_context.py]
  If Earthdata credentials are missing or the GES DISC application is not authorized, then `make imerg` exits non-zero with an English error that says how to authorize it and writes no file.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns each into `test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_rain_context.py` against a small synthetic cells file; the S5 spike in `projects/pipeline/spikes/s5/measure.py` is the starting point and it reads IMERG without downloading whole files): INV-01 to INV-05, INV-14.

- **Which cells count for each rule:** S5 used cells whose centre lies strictly inside its bbox and found the boundary ambiguous; the daily mean uses centres inside `bbox` and the per-unit value the cells actually touched. Confirm on the first real run that the edges do not change the result.
- **Window:** 12 days, from S5's criterion, not tuned; S5 did not test 3 or 7 days (it would have meant picking the one that came out best).
- **IMERG Late, not Final:** Late has latency of at least 14 h and may be revised. `rain.end` must be a published day (S5: the latest day was missing at run time).
- **UTC days:** IMERG days are UTC and the project's local time is Costa Rica (UTC−6); not corrected.
- **`rain.end` advances by hand** in the zone config (see `area-config`).
- **Radar finding:** not part of this slice any more (purged 14 Nov). The optional `[detection_limits]` table of the zone config is copied to `meta.json` by `pipeline-run` and shown by `trust-signals`.
- **Per-unit resolution:** with 10 km cells, most units of a corridor of tens of kilometres share one or two cells. The block's value to a reader is context, not discrimination.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 zone with the real IMERG download, when rain-context runs, then `rain.csv` covers the zone's period with no gaps and every unit has a non-null `rain_mm_12d`.
- ACC-02 [manual]
  Given one downloaded cell and one day, when a person compares its value in `cells.csv` with the original GES DISC granule, then they match.
