---
slice: road-graph
---

# road-graph: spec

> Builds the routable road network, hospitals and communities from OpenStreetMap and writes `graph.json` (task P3).

## Intent

NISAR shows where a hillside moved; to say who loses a good route to a hospital, the pipeline needs a road network that the impact step (P5) and the browser (`graph.ts`) can route on and get the same numbers. This slice turns OpenStreetMap roads, a curated set of hospitals and named settlements into that network, with travel times from one constant speed per road class.

## Scope

Owns:

- Downloading OSM roads, hospitals and places for the **network area**, which is larger than the change corridor (`meta.area.bbox`) so that the known alternates (Ruta 126, Ruta 10) stay inside it. Spike S4 showed that clipping to the corridor removes every alternate and turns a Ruta 32 cut into a false "no path".
- Simplifying the network, splitting long edges, computing `length_m` and `time_s`, snapping hospitals and communities to nodes.
- Applying the per-class speed constant (`SPEED_MODEL_KMH`) to every edge, and exposing it so P7 copies it to `meta.json → speed_model_kmh`.
- Recording the date of the OSM extract, which P7 writes into the OSM line of `meta.json → attributions`.
- Writing `graph.json` with every `candidate_id` set to `null`.

Non-goals:

- Assigning `candidate_id`: that is `candidate-segments` (P4), which rewrites `graph.json` on top of this output.
- Shortest paths, extra time, ranking: that is `impact-scoring` (P5).
- Population per community: not decided (see Deferred); this slice writes `population: null`.
- Writing `meta.json`: that is P7. This slice only exposes the speed constant and the extract date.
- Changing the `graph.json` schema. Nothing here needs a contract change.

## Contract

Inputs:

| Input | Notes |
|---|---|
| Network area | `[w, s, e, n]`, a pipeline setting: `[-84.30, 9.80, -82.95, 10.45]` (Ian, 14 Nov). It reaches Limón so that Hospital Tony Facio is inside; spike S4 with the east edge at -83.40 left 18 communities isolated by a Guápiles–Siquirres cut, likely falsely. |
| OSM data | Overpass, road classes `motorway`, `trunk`, `primary`, `secondary`, `tertiary`, `unclassified` and their `_link` variants. No `residential` or below. |
| Hospital allowlist | A versioned file in the pipeline listing OSM element ids (`way/…`, `node/…`, `relation/…`) of `amenity=hospital` features, reviewed by hand. |

Output: `projects/pipeline/output/graph.json`, shaped as `projects/contract/schemas/graph.schema.json` v0.1, plus the extract date in `projects/pipeline/work/osm/extract_date.txt` (`YYYY-MM-DD`, UTC). The OSM extract itself (`work/osm/`) is never committed; downloading it is a separate step (`make osm`), the only one that uses the network.

Rules:

| Topic | Rule |
|---|---|
| Road class | The OSM `highway` value with `_link` stripped (`trunk_link` → `trunk`). An edge merged from several ways takes the first class OSMnx reports. |
| Multi-valued tags | For `ref`, a list (merged ways) or a `;`-separated value (`"32;126"`) uses its first value, like the road class. |
| Speed | One code constant `SPEED_MODEL_KMH` (class → km/h), the single source for `time_s` and for `meta.json → speed_model_kmh` (team decision, 14 Nov). Values: `trunk` 60, `primary` 40, `secondary` 40, `tertiary` 40, from the medians of OSM `maxspeed` tags measured in spike S4 on the 14 Nov extract; `unclassified` pending (Ian, with a cited source). Nothing is computed from `maxspeed` at run time. A class with no entry stops the run. |
| Rounding | Half up: `floor(x + 0.5)`, the same as JavaScript `Math.round` for positive values. Python's `round()` (half to even) is not used. |
| Cost | `time_s = round_half_up(length_m / (speed_kmh / 3.6))`, using the integer `length_m` that is written (itself `round_half_up` of the metric length). |
| Edge length | No edge is longer than `MAX_EDGE_M` (1000 m); longer ones are split into equal parts at intermediate geometry points or interpolated points. |
| Geometry | Coordinates rounded to 5 decimals, simplified with a ~10 m tolerance; first and last points equal the `from`/`to` node coordinates. |
| Direction | One edge per road piece; `oneway: true` keeps the OSM direction `from → to`. Self-loops (`from == to`) are dropped. |
| Connectivity | Only the largest weakly connected component is kept, so a stray fragment cannot create a false "no path in baseline". |
| `road` | `"Ruta <ref>"` from the first OSM `ref` when present, else the OSM `name`, else `null`. |
| Hospitals | Exactly the allowlisted features, snapped to the nearest kept node; `name` is the OSM `name`. An allowlisted feature with no `name` stops the run (names are never made up). |
| Communities | OSM `place` nodes of type `city`, `town`, `village` or `hamlet` that have a `name`, snapped to the nearest kept node; dropped when farther than `MAX_SNAP_M` (3000 m), and each drop is logged. Accepted coverage limit (Ian, 14 Nov): the first real run dropped 73 communities, mostly in Talamanca and southern Limón, far from Ruta 32, because no `unclassified`-or-higher road passes within 3 km. |
| Ids | Nodes `n1…` in ascending OSM node id, then the nodes created by splitting long edges, numbered after all OSM nodes in edge order and, within an edge, from `from` to `to`; edges `e1…` in ascending `(from, to)` OSM ids of their ends, then ascending smallest OSM way id of the edge (parallel edges), then split order; hospitals `h1…` and communities `c1…` in ascending OSM id. |
| Size | `graph.json` is at most 3 MB, written as compact JSON; a larger result stops the run without writing the file. The first real run over the network area measured 2.29 MB (7 136 nodes, 8 715 edges, 758 communities), with `unclassified` kept. |

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph finishes, the `graph.json` it wrote passes `make validate`'s graph schema and node-reference checks.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes an edge, the first and last points of its `geometry` equal the `lon`/`lat` of its `from` and `to` nodes.
- INV-03 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes an edge, its `length_m` and `time_s` are integers and `time_s` equals `length_m / (speed_kmh / 3.6)` rounded half up for the edge's road class.
- INV-04 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, no edge has `length_m` greater than 1000.
- INV-05 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every edge has `candidate_id: null`.
- INV-06 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, its hospitals are exactly the features in the hospital allowlist, one per allowlisted id.
- INV-07 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If an allowlisted OSM id is not found in the network area, then road-graph exits non-zero with an English error that names that id and writes no `graph.json`.
- INV-08 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every community comes from a named OSM `place` node of type `city`, `town`, `village` or `hamlet` and lies at most 3000 m from its snapped node.
- INV-09 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If a community's nearest kept node is farther than 3000 m, then road-graph leaves it out of `graph.json` and logs its name and distance in English.
- INV-10 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every community has `population: null`.
- INV-11 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph computes `time_s`, it uses the speed of `SPEED_MODEL_KMH` for the edge's road class and no other speed source.
- INV-12 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph runs twice on the same OSM data and settings, the two `graph.json` files are byte-identical.
- INV-13 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, the file is at most 3 MB.
- INV-14 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every node is reachable from every other node when edge direction is ignored.
- INV-15 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, no edge has the same `from` and `to`.
- INV-16 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If an allowlisted hospital has no OSM `name`, then road-graph exits non-zero with an English error that names its OSM id and writes no `graph.json`.
- INV-17 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If a road class on a kept edge has no entry in `SPEED_MODEL_KMH`, then road-graph exits non-zero with an English error that names the class and writes no `graph.json`.
- INV-18 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If the compact `graph.json` would exceed 3 MB, then road-graph exits non-zero with an English error that states the size and writes no `graph.json`.
- INV-19 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If the hospital allowlist has no ids, then road-graph exits non-zero with an English error saying the allowlist is empty and writes no `graph.json`.
- INV-20 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When two edges join the same pair of OSM end nodes, road-graph numbers first the one with the smaller OSM way id.
- INV-21 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If the local OSM extract is missing, then road-graph (without `--download`) exits non-zero with an English error that says how to obtain it (`make osm`) and writes no `graph.json`.
- INV-22 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When the download step finishes, `work/osm/extract_date.txt` holds the UTC download date as `YYYY-MM-DD`.

## Deferred / Open questions

- **Hospital allowlist contents** (Ian, team review): which `amenity=hospital` features count (S4 found 27 in the corridor, including a dental clinic, a blood bank and a psychiatric hospital). The criterion and its source must be written next to the list. Hospital Guápiles (`way/326924912`) and Hospital Dr. Rafael Ángel Calderón Guardia (`way/1168011056`, the one ACC-01 needs) were seen in spike S4; Ian confirms whether they enter.
- **`unclassified` speed** (Ian): needs a value with a cited source before the real run; the 14 Nov extract has 13 tagged edges, too few for a median. Until then the real run stops by INV-17, which is the intended behavior.
- **`meta.json` speed check** (P7): a test that `meta.json → speed_model_kmh` equals `SPEED_MODEL_KMH` belongs to P7, not here. `work/speed_model_kmh.json`, if kept, is an intermediate and never the source.
- **`make osm` and `make all`** (Ian, when P7 lands): `make osm` wraps the download; `make all` never downloads.
- **Population per community** (Wilberth via S7, then Ian or team): source and method (radius, Voronoi on the graph, …). Until decided, INV-10 holds and P5 uses its `null` fallback.
- **`MAX_EDGE_M`** (Ian): 1000 m is a starting value; revisit when P4 sees real change-zone sizes.
- **OSM snapshot** (team): Overpass returns live data, so INV-12 only holds for the same download. Whether to keep the raw extract outside git, and where to record its date, is open.
- **Parity with `graph.ts`** (Iván): the browser must reproduce P5's numbers from this file; integer costs make that exact, but it is checked in `impact-scoring`, not here.
- **Testing gaps:** INV-11, INV-17, INV-21 and INV-22 are `none` until `/builder road-graph` adds or updates tests. ACC-01's test skips, with an explicit reason, when the real network download is absent (as in CI). ACC-02 stays `manual`.

## Acceptance criteria

- ACC-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  Given the graph built for the network area, when every edge whose `road` is `"Ruta 32"` and whose `from`/`to` midpoint longitude lies in `[-83.98, -83.92]` (Ruta 32 inside Braulio Carrillo, as cut in spike S4) is removed, then a path still exists from the node of hospital `way/1168011056` to the node of hospital `way/326924912`.
- ACC-02 [manual]
  Given the graph built for the network area, when Ian computes the baseline time from Hospital Dr. Rafael Ángel Calderón Guardia to Hospital Guápiles, then Ian judges it plausible against a cited reference (S4 corridor spike: 68.8 min).
