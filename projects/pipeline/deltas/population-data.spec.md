---
slice: population-data
---

# population-data: spec

> Fills `communities[].population` in a zone's `graph.json` from the WorldPop raster, so criticality stops being 0 (task E4).

## Intent

The headline metric is extra time to the referral hospital plus the population that depends on the segment. `road-graph` writes `population: null` for every community, and while it stays `null` the criticality of every segment is 0 and the ranking degrades to extra time. This slice assigns the people of the WorldPop raster to the communities of the graph, once each, and says how much of the raster it could not assign. WorldPop is a modelled 2020 estimate, not a census; the numbers it yields are orders of magnitude (S7).

## Scope

Owns:

- Downloading the WorldPop raster named by the zone config (`make worldpop`, the only step of this slice that uses the network).
- Clipping the raster to the zone `bbox` and assigning each valid pixel to a community.
- Writing each community's `population` into `output/<id>/graph.json`, and a report of what was and was not assigned.
- The fallback: a run with `--no-population` that leaves every `population` as `null`.

Non-goals:

- Choosing the raster or its location: that is the zone config (`area-config`). WorldPop CRI 2020 is one file per country, so a zone outside Costa Rica needs its own raster.
- Building communities or snapping them: `road-graph`. This slice only reads their original coordinates from its intermediate file.
- Criticality, `population_dependent` and ranking: `impact-scoring`.
- Showing the "estimate" label and the WorldPop attribution: the attribution text is written by `pipeline-run` and shown by `trust-signals`.
- Writing `population` into any file other than `graph.json`.
- Committing the raster. It is never committed.

## Contract

Inputs:

| Input | Notes |
|---|---|
| Zone | A loaded zone from `area-config`: `id`, `bbox`, `population.raster` (path), `population.url`. |
| `output/<id>/graph.json` | From `road-graph` (or `closure-units`). Its communities define who receives population. |
| `work/<id>/communities.json` | Written by `road-graph`: per community in `graph.json`, its id, OSM id and original `lon`/`lat`. Not part of the shared contract and never published. |
| Raster | A GeoTIFF in EPSG:4326 with people per pixel (S7: `cri_ppp_2020.tif`, ~100 m, nodata −99999). |

Outputs:

- `output/<id>/graph.json`, identical to the input except for `communities[].population`.
- `work/<id>/population_report.json`: raster total inside `bbox`, population assigned, population unassigned (farther than the cutoff), number of communities with and without a value, and the share with a value.

Rules:

| Topic | Rule |
|---|---|
| Method | Each valid pixel, taken at its center, goes to the nearest community by great-circle distance from the community's original coordinates; ties go to the lowest community id. |
| Cutoff | A pixel farther than 3000 m (the same `MAX_SNAP_M` as `road-graph`) from every community is left unassigned and counted in the report. |
| Value | `population = round_half_up(sum of assigned pixels)`, an integer. A community with no valid pixel assigned gets `null`, never `0`. |
| Nodata | Pixels with the raster's nodata value are never counted, in any total. |
| CRS | The raster must be EPSG:4326; any other CRS stops the run (no reprojection). |
| Clip | Only the part of the raster inside the zone `bbox` is read. |
| Fallback | `--no-population` skips the raster entirely and writes `null` everywhere; without it, a missing raster stops the run. |
| Download | `make worldpop` fetches `population.url` into `population.raster`. It never runs as part of `make all`. |

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When population-data finishes, the `graph.json` it wrote passes `make validate` and differs from its input only in `communities[].population`.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When population-data writes a community, its `population` is a non-negative integer or `null`.
- INV-03 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When no valid pixel is assigned to a community, population-data writes `population: null` for it and never `0`.
- INV-04 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When population-data assigns pixels, each valid pixel is counted for at most one community.
- INV-05 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When a valid pixel is farther than 3000 m from every community, population-data leaves it unassigned and adds its people to the report's unassigned total.
- INV-06 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When a pixel holds the raster's nodata value, population-data counts it in no total.
- INV-07 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When population-data finishes, the report's assigned total plus its unassigned total equals the raster total inside `bbox`, within floating-point tolerance, before any rounding.
- INV-08 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When population-data finishes, `work/<id>/population_report.json` states the raster total, the assigned and unassigned totals, the number of communities with and without a value, and the share with a value.
- INV-09 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  If the raster file does not exist and `--no-population` is not given, then population-data exits non-zero with an English error that names the path and says to run `make worldpop`, and leaves `graph.json` unchanged.
- INV-10 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  When population-data runs with `--no-population`, every community has `population: null` and the log says that population was skipped.
- INV-11 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  If the community ids of `communities.json` and `graph.json` are not the same set, then population-data exits non-zero with an English error naming the first id that differs and leaves `graph.json` unchanged.
- INV-14 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py]
  If the raster is not in EPSG:4326 or does not intersect the zone `bbox`, then population-data exits non-zero with an English error naming the raster and the problem and leaves `graph.json` unchanged.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns each into `test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_population_data.py` against a small synthetic raster): INV-01 to INV-11, INV-14.

- **Coverage on Ruta 32:** RELIABILITY step 4 asks for at least 90 % of communities with a value and the assigned total within ±5 % of the raster total, with the difference explained. The Ruta 32 `bbox` includes the Braulio Carrillo forest, where the cutoff may leave a large share unassigned. Whether the target holds is known only after the first real run (ACC-01, ACC-02).
- **Cutoff value:** 3000 m is borrowed from `road-graph`. Revisit if the report shows the unassigned share is large or the nearest-community rule gives a rural community too much.
- **Rural over-assignment:** a community near a dense area can absorb the population of unlisted places inside the cutoff, because only OSM `place` nodes with a name are communities. Accepted as a limit; report it.
- **Attribution and label:** `meta.json → attributions` has no WorldPop line today. `pipeline-run` must add it, and `trust-signals` must label population as a modelled 2020 estimate.
- **Raster for other countries:** the download URL and file are per country (`population.url`). A second zone outside Costa Rica needs its own, not prepared.
- **Dependency:** reading the raster needs `rasterio`, which is not in `pyproject.toml` yet (S7 only tried it).
- **Cross-slice edits:** `area-config` gains the key `population.url`, and `road-graph` writes `work/<id>/communities.json` (INV-26 there). Both specs were updated with this one.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 zone with the real raster and extract, when population-data runs, then at least 90 % of the communities in `graph.json` have a non-null `population`.
- ACC-02 [manual]
  Given the Ruta 32 report, when a person compares the assigned total with the raster total inside `bbox`, then the two differ by at most 5 % or the report's unassigned total explains the difference.
