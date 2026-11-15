---
slice: pipeline-run
---

# pipeline-run: spec

> Runs every pipeline stage for a zone in order, writes `meta.json` and `areas.json`, validates the result and publishes it (tasks P7 and P8).

## Intent

Each stage writes its own fields and trusts the one before it. Something must run them in the right order, leave the published folder either complete and valid or untouched, describe what was computed from what (`meta.json`), list the zones the app can show (`areas.json`), and make the real data reach the site. Without this slice, "regenerate everything and publish" is a sequence of manual commands, and a failed run can leave the site with half of a zone.

## Scope

Owns:

- The fixed order of stages for a zone: `road-graph`, `population-data`, `closure-units`, `impact-scoring`, `rain-context`.
- `meta.json` and `areas.json`.
- Atomic publication of a zone into `output/<id>/`, after the validator passes.
- The `make` targets: `all`, `publish`, `mock`, `validate`, and the download steps `osm`, `worldpop` and `imerg` (each calls its own slice).
- The attribution lines of `meta.json`.

Non-goals:

- What each stage computes: their own slices.
- Downloads. `make all` never uses the network; the three download steps are separate and explicit.
- Which zones exist: the files in `configs/`.
- The deploy workflow itself. Switching `.github/workflows/deploy.yml` from `make mock` to `make publish` is part of the first real deploy (task P8) and is checked by hand (ACC-02).
- The frontend that reads the files.

## Contract

Layout. `output/` has the same layout as the app's `storage/`:

```
output/areas.json
output/<id>/meta.json
output/<id>/graph.json
output/<id>/scenarios.json
output/<id>/rain.csv
```

`make publish` replaces `projects/frontend/public/storage/` with a copy of `output/`; `make mock` replaces it with the contract examples. Every stage and report command writes only under its own zone's folders (`output/<id>/`, `work/<id>/`, `reports/<id>/`). `storage/` is git-ignored; `output/` is committed (decision of 14 Nov: light real data).

Targets:

| Target | Effect |
|---|---|
| `make osm AREA=<id>` | `road-graph --download` (network). |
| `make worldpop AREA=<id>` | `population-data` download (network). |
| `make imerg AREA=<id>` | `rain-context` download (network, Earthdata credentials). |
| `make all [AREA=<id>]` | Runs the stages for the zone, or for every zone in `configs/` when `AREA` is not given. No network. |
| `make validate` | Runs the validator on `storage/`. |
| `make publish`, `make mock` | As above. |

`meta.json` (schema 0.3), written by this slice:

| Field | Source |
|---|---|
| `schema_version`, `generated_at` | `"0.3"` and the UTC time of the run. |
| `files.rain_csv_schema` | `"0.1"`. |
| `area` | `name` and `bbox` from the zone. |
| `speed_model_kmh` | The zone's, unchanged. |
| `rain` | `product`, `version` from `work/<id>/imerg/source.json`; `start` and `end` from the zone; `aggregation` `"area_mean"`. |
| `detection_limits` | Copied from the zone's `detection_limits` table, present only if the table is. |
| `attributions` | See below. No `passes` and no `overlays`. |

Attributions: the OpenStreetMap line with the date of the extract (`© OpenStreetMap contributors (ODbL), extract YYYY-MM-DD`), the IMERG Late line (NASA GPM), and a WorldPop line ("modelled population estimate") only when population was filled, meaning at least one community has a `population` other than `null`. A NISAR line appears only if the zone has radar files.

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When a zone's run finishes, `output/<id>/` holds `meta.json`, `graph.json`, `scenarios.json` and `rain.csv`, and the validator passes on it.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When a stage of a zone's run fails or the validator fails on the new files, pipeline-run exits non-zero with an English error naming the stage or the validator, and `output/<id>/` equals what it was before the run.
- INV-04 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When pipeline-run runs the stages of a zone, it runs them in the order `road-graph`, `population-data`, `closure-units`, `impact-scoring`, `rain-context`.
- INV-05 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When `make all` runs, it makes no network request.
- INV-06 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When pipeline-run writes `meta.json`, `area.name`, `area.bbox`, `rain.start`, `rain.end`, `speed_model_kmh` and `detection_limits` (present only if the zone has it) equal the zone config's values, and `rain.product` and `rain.version` equal those in `work/<id>/imerg/source.json`.
- INV-10 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When pipeline-run writes `meta.json`, its attributions include the OpenStreetMap line with the extract date and the IMERG line, and include the WorldPop line only if population was filled.
- INV-11 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When pipeline-run writes `areas.json`, it lists every zone folder under `output/` once, ordered by id, with `id`, `name`, `bbox` and `validated` taken from that zone's config.
- INV-13 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When `make all` runs twice on the same inputs, every file of `output/` is byte-identical except `generated_at` in each `meta.json`.
- INV-14 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run.py]
  When `make publish` or `make mock` runs, `storage/` becomes an exact copy of its source (`output/` or the contract examples) and holds nothing else.
- INV-15 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run_adversarial.py]
  If `meta.json` cannot be built (`source.json` or `extract_date.txt` is missing or invalid, the date not being `YYYY-MM-DD`), then pipeline-run exits non-zero with an English error naming the file and leaves `output/<id>/` as it was.
- INV-16 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run_adversarial.py]
  If the process stopped between the two moves of a publication, leaving `.<id>.old` and no `output/<id>/`, then the next run restores `.<id>.old` to `output/<id>/` before running the stages and deletes any leftover `.<id>.new`.
- INV-17 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run_adversarial.py]
  If `output/` holds a folder whose name is not a zone id with a config in `configs/`, then pipeline-run exits non-zero with an English error naming the folder and does not rewrite `areas.json`.
- INV-18 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run_adversarial.py]
  When pipeline-run writes `meta.json` or `areas.json`, the file uses LF line endings on every operating system.
- INV-19 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_pipeline_run_adversarial.py]
  If `make publish` or `make mock` is given a source folder that does not exist, then it exits non-zero and leaves `storage/` as it was.

## Deferred / Open questions

Testing gaps: none; every invariant has a `test:` tag, and ACC-01 and ACC-02 are manual.

- **`make all` without `AREA`:** runs every zone in `configs/`, so one unprepared zone (no raster, no extract) fails the whole run. Use `AREA` for a single zone. Revisit if a second zone is added.
- **Mocks follow the new layout:** `contract-update` moves the examples to `areas.json` plus a zone folder; `make mock` and the CI workflow must be updated with it.
- **First real deploy (P8):** `.github/workflows/deploy.yml` still runs `make mock` with a `shortcut:` note; switching to `make publish` happens when `output/` holds real data. Nothing here can check the deployed site (ACC-02).
- **Blocked inputs:** the first real run needs Ian's hospital list and the `unclassified` speed (see `area-config`), and all three downloads done by hand.
- **`generated_at`:** the run time, so `meta.json` is outside the byte-identical guarantee.
- **Attribution wording:** the NASA/JPL line for NISAR is dropped while there is no radar layer; the interface must not name NISAR as a source then (`trust-signals`).
- **Concurrent runs of one zone:** two runs share `.<id>.new`, so they can corrupt each other. Nothing prevents it; revisit if runs are ever automated in parallel.
- **Partial publication across zones:** atomicity is per zone; `areas.json` is rewritten last, so an interrupted multi-zone run can leave it older than the folders.

## Acceptance criteria

- ACC-01 [manual]
  Given the three downloads done for the Ruta 32 zone, when a person runs `make all AREA=ruta-32` and then `make publish validate`, then both exit 0 and `output/ruta-32/meta.json` names a real area, not a mock.
- ACC-02 [manual]
  Given real data committed in `output/` and the deploy workflow running `make publish`, when the Pages site is opened in a private window, then the app shows the real Ruta 32 results and no "MOCK" label.
