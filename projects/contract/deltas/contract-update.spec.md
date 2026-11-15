---
slice: contract-update
---

# contract-update: spec

> Takes the shared data files from schema 0.2 to 0.3 so the pipeline and the web app can express several zones, fine closure units, suspect isolations and the referral hospital list, and makes the validator enforce them.

## Intent

After the spikes (D8) the product is the consequence of closing a road segment. The 0.2 files cannot yet say how long a closure unit is, which isolated communities are probably adjustment artifacts, or which hospitals were used as the referral set. The pipeline deltas (`closure-units`, `impact-scoring`, `road-graph`) and the frontend deltas (`segment-detail`, `trust-signals`) all depend on those facts being in the files, so this slice fixes the shape once, before they build against it. It also removes `exposure.soil_moisture_pctl`, which has been dead since D7. The app is meant to show several zones (Ruta 32 is the only validated one), so the files are published per zone and a small index tells the app which zones exist.

## Scope

Owns:

- The JSON Schemas in `projects/contract/schemas/` and the mocks in `projects/contract/examples/` and `projects/contract/shared/no-toggle/`.
- The consistency checks in the validator (`projects/pipeline/source/pipeline/validate.py`) and its tests.
- The bump of every `schema_version` to `"0.3"`.

Non-goals:

- How any value is computed (closure units, suspect detection, population, rain). Those are the pipeline deltas.
- How any value is rendered. That is the frontend deltas.
- The rain period itself: it is a zone parameter owned by `area-config`. This slice only keeps the rule that `rain.csv` covers `meta.rain.start`..`end`.
- Population provenance fields (source, year, share of `null`). Not requested; revisit if `population-data` needs them.
- Rewriting `context/contracts.md`. A person updates it after approving this spec; until then the schemas win.
- Removing the radar fields (`passes`, `overlays`, `change.geojson`). They stay optional.

## Contract

Changes from 0.2 to 0.3. Every other field keeps its 0.2 meaning.

| File | Change | Shape |
|---|---|---|
| all | `schema_version` | `"0.3"`. `meta.files.rain_csv_schema` stays `"0.1"`. |
| `areas.json` | New file at the root of `storage/` (schema `areas.schema.json`) | `{ "schema_version": "0.3", "areas": [ { "id", "name", "bbox", "validated" } ] }`. `id` is lowercase words joined by hyphens, unique in the list. `validated` is a boolean: `true` only for a zone whose results were checked, so the UI can label the rest "not validated". At least one area. |
| layout | One folder per zone | `storage/areas.json` plus `storage/<id>/` holding that zone's `meta.json`, `graph.json`, `scenarios.json`, `rain.csv` and the optional radar files. The mock set follows the same layout. |
| `scenarios.json` | New required `candidates[].length_m` | number, greater than 0: length of the closure unit along the road, counting a paired carriageway once (two parallel one-way carriageways of length L give L). |
| `scenarios.json` | New required `candidates[].suspect_isolated_community_ids` | array of community ids, subset of `isolated_community_ids`. Isolations the pipeline considers probable artifacts (snapped to a node of the closed unit, or isolated only because of `oneway`). Empty array when none. |
| `scenarios.json` | Removed `candidates[].exposure.soil_moisture_pctl` and `exposure.radar_evidence` | `exposure` keeps only `rain_mm_12d`. The radar finding lives in `meta.json → detection_limits` (already optional in 0.2). |

Validator behavior: every error names the file, the field and the rule, in English.

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  When the validator reads a contract JSON file whose `schema_version` is not `"0.3"`, it reports an error naming that file.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  If a candidate lacks `length_m` or `suspect_isolated_community_ids`, then the validator reports an error naming the candidate.
- INV-03 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  If a candidate's `suspect_isolated_community_ids` contains an id that is not in its `isolated_community_ids`, then the validator reports an error naming the candidate and the id.
- INV-05 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  If a candidate's `exposure` contains `soil_moisture_pctl` or `radar_evidence`, then the validator rejects the file as an unknown field.
- INV-06 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  If a contract file contains a field the schema does not define, then the validator rejects it.
- INV-07 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  If a candidate's `isolated_community_ids` contains an id not in its `affected_community_ids`, then the validator reports an error.
- INV-08 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  If `rain.csv` dates do not cover `meta.json → rain.start`..`end`, then the validator reports an error.
- INV-10 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  If `areas.json` is missing, empty, lists the same `id` twice, or lists an area with no folder `storage/<id>/`, then the validator reports an error naming the file or the area.
- INV-12 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  When the validator runs on `storage/`, it validates every zone folder listed in `areas.json` with the same checks, and its exit code is non-zero if any zone fails.

## Deferred / Open questions

Testing gaps: none; every claim has a `test:` tag.

- **Shape proposals not yet confirmed:** the names `length_m` and `suspect_isolated_community_ids`. Decide at review of this spec. (Purged 14 Nov: `granularity`, `area.id`, `area.referral_hospitals` and `radar_evidence` were dropped as redundant; the UI reads the hospital names from `graph.json` and shows the length itself.)
- **Suspect reason (decided 14 Nov):** this version only says an isolation is suspect, not why (adjusted to the closed unit or `oneway`). A reason is added only if `trust-signals` needs to show it.
- **Unlisted folders and bbox (decided 14 Nov):** a folder in `storage/` that `areas.json` does not list is ignored, so only listed zones are published (pinned by a test). `areas.json → bbox` is not cross-checked against `meta.area.bbox`: both are written from the same zone config.
- **Duplicate ids (decided 14 Nov):** `affected_community_ids`, `isolated_community_ids` and `suspect_isolated_community_ids` must hold unique ids.
- **Referral list assumption (D8, contracts §13):** that `graph.json → hospitals` holds only the referral hospitals is still unconfirmed with Ian.
- **Multi-zone layout (decided 14 Nov, user):** one folder per zone plus `areas.json`; the zone picker and the second zone are cuttable at G2 (`zone-picker` in `STATUS.md`), but the layout is not. Which second zone, if any, is not chosen and is never invented.
- **Mock layout and `make` targets:** `make mock` and `make validate` must move to the per-zone layout; that wiring is `pipeline-run`, and the mock files move here. Until both land, ACC-01 and ACC-02 describe the target layout.
- **Docs out of sync:** `context/contracts.md` §0 still says "not committed yet" and `CLAUDE.md` says the pipeline and `Makefile` do not exist. A person edits both.
- **Frontend on 0.3 (done 14 Nov):** `App.tsx` and `graph.ts` read the first zone of `areas.json` and `App.tsx` guards the optional overlay; the zone picker and the full map stay with `zone-picker` and `map-corridor`.

## Acceptance criteria

- ACC-01 [test: make mock validate]
  Given the default mock set copied into `storage/`, when `make mock validate` runs, then it exits 0.
- ACC-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  Given the `no-toggle` variant (the mock set without `overlay_before.png` and `overlay_after.png`), when the validator runs, then it exits 0.
- ACC-03 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  Given the 0.3 mock set, when it is inspected, then it contains at least one candidate with a non-empty `suspect_isolated_community_ids` and `area.name` marked as a mock.
- ACC-04 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_validate.py]
  Given the mock set with two zones (one `validated: true`, one `validated: false`), when the validator runs on `storage/`, then it exits 0.
