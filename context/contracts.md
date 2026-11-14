# VANTAGE — Contract reference

> Field-by-field reference for the files in `projects/frontend/public/storage/`, the only coupling between the pipeline (writes) and the SPA (reads).

| File | Written by | Read by | Format |
|---|---|---|---|
| `meta.json` | Pipeline | SPA | JSON |
| `change.geojson` | Pipeline | SPA | GeoJSON |
| `overlay_*.png` | Pipeline | SPA | PNG (RGBA) |
| `graph.json` | Pipeline | SPA | JSON |
| `scenarios.json` | Pipeline | SPA | JSON |
| `rain.csv` | Pipeline | SPA | CSV |

## 0. Status: FROZEN v0.1 (14 Nov)

The schemas in `projects/contract/schemas/` are written and frozen at `schema_version` `"0.1"`; the six open decisions are closed in §11. Changes follow §10.

This file must match the schemas exactly. If they differ, the schemas win; fix this file.

## 1. Global conventions

| Topic | Rule |
|---|---|
| Versioning | Every JSON file has a top-level `schema_version` (string, e.g. `"0.1"`). `rain.csv` carries its version in `meta.json` (`files.rain_csv_schema`). |
| Coordinates | WGS84 (EPSG:4326), always **`[longitude, latitude]`** order (GeoJSON order). |
| Time | Travel times in **seconds** (`*_s`); the UI converts to minutes. Dates as `YYYY-MM-DD`; timestamps as ISO 8601 UTC. |
| Distance / area | Meters (`*_m`), square meters (`*_m2`). |
| Radar change | Decibels (`*_db`). Change = after − before. |
| IDs | Stable strings. Candidate segments: `T-01`, `T-02`, … (ranked order at generation time, but the **id is not the rank**: read `rank`). Others: `n123`, `e45`, `h1`, `c7`. |
| Unknown values | Use `null`, never `0` and never a made-up number. Example: `population: null` if WorldPop is unavailable. The UI must handle `null`. |
| Language | Field names in English. Display names (places, hospitals) keep their original Spanish names. |
| Size | Keep files light. Never embed raw NISAR data. Overlay PNGs should be small (target well under a few MB each). |
| Extra fields | Schemas should **reject unknown top-level fields** (`additionalProperties: false`) so drift is caught by `make validate`. |

## 2. `meta.json`

Describes what was computed from what, and where the overlay images go on the map.

```json
{
  "schema_version": "0.1",
  "generated_at": "2026-11-14T20:00:00Z",
  "files": { "rain_csv_schema": "0.1" },
  "area": { "name": "Ruta 32 corridor", "bbox": [-84.20, 9.95, -83.70, 10.30] },
  "passes": {
    "before": { "date": "YYYY-MM-DD", "granule": "string", "track": 0, "direction": "ascending", "crid": "P05023" },
    "after":  { "date": "YYYY-MM-DD", "granule": "string", "track": 0, "direction": "ascending", "crid": "P05023" }
  },
  "overlays": [
    { "id": "change", "label": "Change", "file": "overlay_change.png", "bounds": [-84.20, 9.95, -83.70, 10.30], "kind": "delta_db" },
    { "id": "before", "label": "Before", "file": "overlay_before.png", "bounds": [-84.20, 9.95, -83.70, 10.30], "kind": "backscatter" },
    { "id": "after",  "label": "After",  "file": "overlay_after.png",  "bounds": [-84.20, 9.95, -83.70, 10.30], "kind": "backscatter" }
  ],
  "rain": { "product": "GPM_3IMERGDL", "version": "V07", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "attributions": [
    "Contains modified NISAR GCOV data (NASA/JPL)",
    "IMERG Late (NASA GPM)",
    "© OpenStreetMap contributors (ODbL)"
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `files.rain_csv_schema` | string | Version of the `rain.csv` layout, since a CSV cannot carry `schema_version`. |
| `area.bbox` | `[w, s, e, n]` | Corridor extent the pipeline clipped to. Values above are **placeholders**. |
| `passes.*.track`, `direction`, `crid` | int, `"ascending"` \| `"descending"`, string | `before` and `after` **must be identical** in track, direction and CRID. The validator should check it. |
| `passes.*.date` | date | Acquisition date. |
| `overlays[].bounds` | `[w, s, e, n]` | Georeferencing for the PNG. MapLibre needs the four corners: `[[w,n],[e,n],[e,s],[w,s]]`. Image must already be reprojected to match (EPSG:4326 corners are fine for a small area). |
| `overlays[].kind` | `"delta_db"` \| `"backscatter"` | Lets the UI pick a legend. |
| `overlays` | array | Remove `before`/`after` entries if the before/after toggle is cut; the UI must hide the toggle when absent. |
| `attributions` | string[] | The UI footer renders these. OSM's ODbL credit is mandatory. |

## 3. `change.geojson`

Detected change zones from step 1 of the method.

GeoJSON `FeatureCollection`, with `schema_version` as a top-level foreign member.

```json
{
  "type": "FeatureCollection",
  "schema_version": "0.1",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Polygon", "coordinates": [[[-83.9, 10.1], [-83.89, 10.1], [-83.89, 10.11], [-83.9, 10.1]]] },
      "properties": { "id": "z1", "area_m2": 0, "mean_delta_db": 0.0, "min_delta_db": 0.0 }
    }
  ]
}
```

| Property | Type | Notes |
|---|---|---|
| `id` | string | Zone id (`z1`, …). |
| `area_m2` | number | After removing blobs below the minimum area. |
| `mean_delta_db` | number | Mean ΔdB inside the zone. The UI shows it as "mean backscatter change". |
| `min_delta_db` | number | Optional; strongest change. |

Polygons are `Polygon` or `MultiPolygon`; no holes required. This is a **signal**, not a confirmed landslide.

## 4. Overlay PNGs

Referenced by `meta.json → overlays[].file`, in the same folder.

- RGBA PNG with transparency where there is no data or no change.
- Reprojected to match `bounds` (north-up, no rotation).
- Change overlay: a continuous ΔdB color ramp. Before/After: grayscale backscatter.
- Pipeline and UI agree on the ramp's range through `meta.json → overlays[].range_db` (`[min, max]`, only for `delta_db`); the legend is drawn from it.
- Light files only. Raw NISAR data is never committed.

## 5. `graph.json`

Road network and facilities. The browser runs shortest-path on this to simulate closures (`graph.ts`).

```json
{
  "schema_version": "0.1",
  "nodes": [ { "id": "n1", "lon": -83.9, "lat": 10.1 } ],
  "edges": [
    { "id": "e1", "from": "n1", "to": "n2", "length_m": 0, "time_s": 0, "road": "Ruta 32", "oneway": false, "candidate_id": null, "geometry": [[-83.9, 10.1], [-83.89, 10.11]] }
  ],
  "hospitals":   [ { "id": "h1", "name": "string", "node": "n1" } ],
  "communities": [ { "id": "c1", "name": "string", "node": "n2", "population": null } ]
}
```

| Field | Notes |
|---|---|
| `edges[].time_s` | Free-flow travel time. Same cost model as the pipeline, so the browser and the pipeline give the same numbers. One constant speed per OSM road class, listed in `meta.json → speed_model_kmh` (class → km/h). |
| `edges[].oneway` | `false` = traversable both ways. Edges are otherwise directed `from → to`. |
| `edges[].candidate_id` | The `T-xx` id if this edge belongs to a candidate segment, else `null`. |
| `edges[].geometry` | Polyline for drawing; endpoints equal the `from`/`to` node coordinates. |
| `hospitals[].node`, `communities[].node` | Snapped node ids. |
| `communities[].population` | Integer or `null`. Never `0` for "unknown". |

Rules:

- Every `from`, `to` and `node` must exist in `nodes`.
- A candidate may span several edges (see `scenarios.json → edge_ids`); an edge belongs to at most one candidate.
- Node positions use separate `lon` and `lat` fields, while `geometry` and all other coordinates use `[longitude, latitude]` pairs.

## 6. `scenarios.json`

Per candidate segment: the result of removing it from the network (step 3 and 4 of the method).

```json
{
  "schema_version": "0.1",
  "baseline": [ { "community_id": "c1", "time_s": 0, "hospital_id": "h1" } ],
  "candidates": [
    {
      "id": "T-01",
      "rank": 1,
      "edge_ids": ["e1", "e2"],
      "zone_ids": ["z1"],
      "mean_delta_db": 0.0,
      "criticality": 0.0,
      "extra_time_s": 0,
      "population_dependent": null,
      "affected_community_ids": ["c1"],
      "isolated_community_ids": [],
      "per_community": [ { "community_id": "c1", "time_s": 0, "extra_s": 0, "hospital_id": "h1" } ],
      "alternates": [ { "name": "Ruta 126", "vehicles": "light" }, { "name": "Ruta 10", "vehicles": "freight" } ]
    }
  ]
}
```

| Field | Notes |
|---|---|
| `baseline[]` | Time to the nearest hospital with **no** closures. `time_s` and `hospital_id` are `null` for a community with no path even before any closure. |
| `candidates[].rank` | 1 = most critical. Sort order for the list. |
| `edge_ids` | Edges removed together when this candidate is closed. |
| `extra_time_s` | The headline number: the maximum `extra_s` among affected, non-isolated communities. |
| `criticality` | Sum over affected communities of `population × extra_s`. An isolated community uses as `extra_s` the largest finite `extra_s` across all candidates (its penalty). A community with `population: null` adds 0. Ties, and the case where no population is known, rank by `extra_time_s` and then by isolated count. |
| `population_dependent` | Integer or `null`. Total population of affected communities. |
| `isolated_community_ids` | Communities with **no path** to any hospital. Subset of `affected_community_ids`. Their `per_community.time_s` is `null`. |
| `per_community[].time_s`, `extra_s` | `time_s` is `null` if isolated; then `extra_s` is `null` too. |
| `alternates` | Alternate routes shown in the panel. Source: project knowledge (Ruta 126 light only, Ruta 10 freight); do not add routes without a source. |

The browser's own simulation (closing several segments at once) is computed from `graph.json`, not from this file. `scenarios.json` covers the one-at-a-time results and the ranking.

## 7. `rain.csv`

Daily IMERG Late rainfall for the period.

```csv
date,precip_mm
YYYY-MM-DD,0.0
```

| Column | Notes |
|---|---|
| `date` | One row per day, ascending, no gaps. |
| `precip_mm` | Daily precipitation in mm, mean of the IMERG cells inside the corridor (`meta.json → rain.aggregation: "area_mean"`). IMERG is 0.1° (~10 km), so it is context only. |

Header row is required. The pass dates in `meta.json` mark the interval on the chart.

## 8. Validation

`make validate` (`jsonschema` in Python, runs in CI and before every deploy) should cover:

1. **Schema checks** for every file above, including `schema_version`.
2. **Consistency checks**, which JSON Schema cannot express (add as small Python tests):
   - `passes.before` and `passes.after` share track, direction and CRID.
   - Every `from`/`to`/`node` id exists in `graph.nodes`.
   - Every `scenarios.candidates[].edge_ids` exists in `graph.edges`; every `candidate_id` in the graph appears in `scenarios`.
   - `isolated_community_ids ⊆ affected_community_ids`; community and hospital ids exist.
   - Overlay files named in `meta.json` exist and `bounds` has `west < east` and `south < north`.
   - `rain.csv` dates cover the period in `meta.json`.
   - `meta.files.rain_csv_schema` is present.
3. **English error messages**: the validator names the file, the field and the rule that failed, in English.

## 9. Mock data (`contract/examples/`)

- Mocks must satisfy the schemas and include: 4 candidates, 3 hospitals, 5 communities, one candidate with an isolated community, one community with `population: null`, and both `before`/`after` overlays absent in a second variant (to test the hidden toggle).
- Mock values are **fake**. Mark them clearly (for example `meta.area.name: "MOCK — not real data"`) so they never reach the demo as if real.
- Layout: `examples/` holds the default set (3 overlays); `variants/no-toggle/meta.json` is the second variant, to be used together with the same files minus `overlay_before.png` and `overlay_after.png`. `pipeline/tests/` validates both.
- `make mock` copies `examples/` into `frontend/public/storage/`, replacing what was there. `storage/` is git-ignored.

## 10. Changing the contract

1. Edit the schema in `contract/schemas/`.
2. Update the mock in `contract/examples/`.
3. Bump `schema_version`.
4. Update producer (pipeline) and consumer (frontend) in the same PR.
5. Run `make validate`.
6. Get review from one backend and one frontend person (CODEOWNERS).

## 11. Decisions closed before freezing (14 Nov)

| # | Decision | Resolution |
|---|---|---|
| 1 | How is `extra_time_s` aggregated across communities? | Max over affected non-isolated communities |
| 2 | How is `criticality` computed? | Sum of `population × extra_s`, isolation as max penalty; falls back to `extra_time_s` then isolated count when population is `null` |
| 3 | Speed model per road class for `time_s` | One constant speed per OSM class, in `meta.json → speed_model_kmh` |
| 4 | Overlay legend range | `meta.json → overlays[].range_db` (`[min, max]`) |
| 5 | Rain value: area mean or nearest cell | Area mean over the corridor, `meta.json → rain.aggregation: "area_mean"` |
| 6 | Keep `before`/`after` overlays? | Optional; decide at the Sunday 14:00 feature freeze (G2); contract allows removing them |

New `meta.json` fields to add to the schema (B4): `speed_model_kmh`, `overlays[].range_db`, `rain.aggregation`. The speed values themselves are set when the road graph is built (P3).