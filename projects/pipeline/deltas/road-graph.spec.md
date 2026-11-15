---
slice: road-graph
---

# road-graph: spec

> Builds the routable road network, referral hospitals and communities of one zone from OpenStreetMap and writes that zone's `graph.json` (task P3).

## Intent

To say who loses the route to a referral hospital when a road segment is cut, the pipeline needs a road network that the impact step and the browser (`graph.ts`) can route on and get the same numbers. This slice turns a zone's OpenStreetMap roads, its referral hospitals and its named settlements into that network, with travel times from one constant speed per road class. It was first written for Ruta 32 only (branch `feat/road-graph`); this version takes every zone-specific value from the zone config (`area-config`) and snaps hospitals and communities so that closing a road cannot produce false isolations (D8).

## Scope

Owns:

- Downloading OSM roads, hospitals and places for the zone's `bbox`, which is the network area and is larger than the road being studied so that the alternates (Ruta 126, Ruta 10 in Ruta 32) stay inside it. Spike S4 showed that clipping to the corridor removes every alternate and turns a cut into a false "no path".
- Simplifying the network, splitting long edges, computing `length_m` and `time_s`.
- Snapping the zone's referral hospitals and the named communities to nodes of the largest strongly connected component of the directed graph, from their original OSM coordinates.
- Writing `work/<id>/communities.json`, an intermediate file with each community's id, OSM id and original `lon`/`lat`, for `population-data`. It is not part of the shared contract and is never published.
- Recording the date of the OSM extract, which `pipeline-run` writes into the OSM line of `meta.json → attributions`.
- Writing the zone's `graph.json` with every `candidate_id` set to `null`.

Non-goals:

- Reading, validating or choosing the zone: that is `area-config`. This slice receives a loaded zone and never reads a config file or a bbox, hospital list or speed from code.
- Assigning `candidate_id`: `closure-units` defines the closure units and rewrites `graph.json` with the ids.
- Shortest paths, extra time, ranking: `impact-scoring`.
- Population per community: `population-data`. This slice writes `population: null`.
- Writing `meta.json`, `areas.json` or the `make` targets: `pipeline-run`.
- Deciding which OSM features count as referral hospitals: that is the zone config's list.
- Changing the `graph.json` schema: that is `contract-update`.

## Contract

Inputs:

| Input | Notes |
|---|---|
| Zone | A loaded zone from `area-config`: `id`, `bbox`, referral hospital OSM ids, `speed_model_kmh`. |
| OSM extract | `work/<id>/osm/roads.osm` and `features.osm`, from Overpass: road classes `motorway`, `trunk`, `primary`, `secondary`, `tertiary`, `unclassified` and their `_link` variants (no `residential` or below), `amenity=hospital` features, and named `place` nodes. |

Output (also `work/<id>/communities.json`, see Scope): `projects/pipeline/output/<id>/graph.json`, shaped as `projects/contract/schemas/graph.schema.json` at `schema_version` `"0.3"`, plus the extract date in `projects/pipeline/work/<id>/osm/extract_date.txt` (`YYYY-MM-DD`, UTC). The extract is never committed. Downloading it is a separate step (`make osm`), the only one that uses the network.

Code constants (not zone parameters): `MAX_EDGE_M` = 1000 and `MAX_SNAP_M` = 3000.

Rules:

| Topic | Rule |
|---|---|
| Road class | The OSM `highway` value with `_link` stripped (`trunk_link` → `trunk`). An edge merged from several ways takes the first class OSMnx reports. |
| Multi-valued tags | For `ref`, a list (merged ways) or a `;`-separated value (`"32;126"`) uses its first value, like the road class. |
| Speed | `time_s` uses the zone's `speed_model_kmh`, the same table `pipeline-run` copies to `meta.json → speed_model_kmh`. Nothing is computed from `maxspeed` at run time. A road class on a kept edge with no entry stops the run. |
| Rounding | Half up: `floor(x + 0.5)`, the same as JavaScript `Math.round` for positive values. Python's `round()` (half to even) is not used. |
| Cost | `time_s = round_half_up(length_m / (speed_kmh / 3.6))`, using the integer `length_m` that is written (itself `round_half_up` of the metric length). |
| Edge length | No edge is longer than `MAX_EDGE_M`; longer ones are split into equal parts. |
| Geometry | Coordinates rounded to 5 decimals, simplified with a ~10 m tolerance; first and last points equal the `from`/`to` node coordinates. |
| Direction | One edge per road piece; `oneway: true` keeps the OSM direction `from → to`. Self-loops are dropped. |
| Network kept | Only the largest weakly connected component, so a stray fragment cannot create a false "no path in baseline". The file keeps all of its edges. |
| Snapping | Hospitals and communities snap to the nearest node of the largest strongly connected component of the directed graph (two-way edges count in both directions, `oneway` edges in one), measured from the feature's original OSM coordinates. |
| `road` | `"Ruta <ref>"` from the first OSM `ref` when present, else the OSM `name`, else `null`. |
| Hospitals | Exactly the zone's referral hospital ids, each found in the extract; `name` is the OSM `name`. A hospital with no `name`, one not found, or one farther than `MAX_SNAP_M` from its snapped node stops the run (names and places are never made up). |
| Referral ids | Compared by kind and number, so `way/301` and `way/0301` name the same hospital. The zone config does not forbid writing both, so this stage rejects the pair (decided 15 Nov; `area-config` could reject it earlier, see Deferred). |
| Communities | OSM `place` nodes of type `city`, `town`, `village` or `hamlet` with a `name`, snapped as above; dropped when farther than `MAX_SNAP_M`, and each drop is logged. Accepted coverage limit for Ruta 32 (Ian, 14 Nov): the first real run dropped 73 communities, mostly in Talamanca and southern Limón, far from the road. |
| Ids | Nodes `n1…` in ascending OSM node id, then the nodes created by splitting long edges, numbered after all OSM nodes in edge order and, within an edge, from `from` to `to`; edges `e1…` in ascending `(from, to)` OSM ids of their ends, then ascending smallest OSM way id (parallel edges), then split order; hospitals `h1…` and communities `c1…` in ascending OSM id. |
| Size | `graph.json` is at most 3 MB, written as compact JSON; a larger result stops the run without writing the file. The first real run over the Ruta 32 network area measured 2.29 MB (7 136 nodes, 8 715 edges, 758 communities). |
| Extract files | `roads.osm` and `features.osm` must each be well-formed OSM XML, and `roads.osm` must hold at least one road. A `features.osm` that is well-formed but holds no features is not unreadable: the zone always lists at least one referral hospital, so it is the case of INV-07. |
| Download | Both Overpass answers are obtained and checked before any file of the extract is replaced, and `extract_date.txt` is written last. An answer is unusable when it is not well-formed OSM XML, holds no elements or contains a `remark` element (how Overpass reports a runtime error such as a timeout, inside a 200 answer). A failed request (network error, timeout or HTTP error status) is an English exit, never a traceback (decided 15 Nov). |

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph finishes, the `graph.json` it wrote passes `make validate`'s graph schema and node-reference checks.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes an edge, the first and last points of its `geometry` equal the `lon`/`lat` of its `from` and `to` nodes.
- INV-03 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes an edge, its `length_m` and `time_s` are integers and `time_s` equals `length_m / (speed_kmh / 3.6)` rounded half up, with the speed of the edge's road class in the zone's `speed_model_kmh`.
- INV-04 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, no edge has `length_m` greater than 1000.
- INV-05 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every edge has `candidate_id: null`.
- INV-06 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, its hospitals are exactly the zone's referral hospital ids, one per id.
- INV-07 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If a referral hospital id is not found in the OSM extract, then road-graph exits non-zero with an English error that names that id and writes no `graph.json`.
- INV-08 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every community comes from a named OSM `place` node of type `city`, `town`, `village` or `hamlet` and lies at most 3000 m from its snapped node.
- INV-09 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If a community's nearest node of the largest strongly connected component is farther than 3000 m, then road-graph leaves it out of `graph.json` and logs its name and distance in English.
- INV-10 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every community has `population: null`.
- INV-11 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph computes `time_s`, it uses the speed of the zone's `speed_model_kmh` for the edge's road class and no other speed source.
- INV-12 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph runs twice on the same OSM data and zone, the two `graph.json` files are byte-identical.
- INV-13 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, the file is at most 3 MB.
- INV-14 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every node is reachable from every other node when edge direction is ignored.
- INV-15 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, no edge has the same `from` and `to`.
- INV-16 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If a referral hospital has no OSM `name`, then road-graph exits non-zero with an English error that names its OSM id and writes no `graph.json`.
- INV-17 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If a road class on a kept edge has no entry in the zone's `speed_model_kmh`, then road-graph exits non-zero with an English error that names the class and writes no `graph.json`.
- INV-18 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If the compact `graph.json` would exceed 3 MB, then road-graph exits non-zero with an English error that states the size and writes no `graph.json`.
- INV-19 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When two edges join the same pair of OSM end nodes, road-graph numbers first the one with the smaller OSM way id.
- INV-20 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If the local OSM extract of the zone is missing, then road-graph (without `--download`) exits non-zero with an English error that says how to obtain it (`make osm`) and writes no `graph.json`.
- INV-21 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When the download step finishes, `work/<id>/osm/extract_date.txt` holds the UTC download date as `YYYY-MM-DD`.
- INV-22 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph runs with `--download`, it only downloads the extract and records its date, and writes no `graph.json`.
- INV-23 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, every hospital node and every community node belongs to the largest strongly connected component of the directed graph.
- INV-24 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If a referral hospital lies more than 3000 m from its snapped node, then road-graph exits non-zero with an English error that names the hospital and the distance and writes no `graph.json`.
- INV-26 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  When road-graph writes `graph.json`, it also writes `work/<id>/communities.json` with exactly one entry per community of `graph.json`, holding its id, its OSM id and its original `lon` and `lat`.
- INV-27 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If `roads.osm` is empty, is not well-formed OSM XML or holds no roads, or `features.osm` is empty or is not well-formed OSM XML, then road-graph exits non-zero with an English error that names the file and writes no `graph.json` and no `communities.json`.
- INV-28 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If any Overpass request of `--download` fails (network error, timeout or HTTP error status), then road-graph exits non-zero with an English error and leaves the zone's `roads.osm`, `features.osm` and `extract_date.txt` as they were.
- INV-29 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If an Overpass answer is not well-formed OSM XML, holds no elements or contains a `remark` element, then road-graph with `--download` exits non-zero with an English error and leaves the zone's `roads.osm`, `features.osm` and `extract_date.txt` as they were.
- INV-30 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py]
  If the zone's referral hospital ids include two that name the same OSM element (for example `way/301` and `way/0301`), then road-graph exits non-zero with an English error that names both ids and writes no `graph.json`.

## Deferred / Open questions

Testing gaps: ACC-01 is `none` because it needs the real extract, which needs the network and a complete `speed_model_kmh`. INV-27 to INV-30 are `none` until `builder` runs: their tests already exist as the 8 tests of `test_road_graph_findings.py`, red on purpose. `builder` moves them to `test_road_graph.py` and turns each tag into `test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_road_graph.py`. One of them changes with this revision: the test for `way/0301` expects one hospital and must expect the INV-30 error instead.

- **Network without cycles (undecided):** when no strongly connected component has more than one node (for example a network of only one-way roads), every hospital and community snaps to the same node and the run succeeds without a warning. Whether to stop the run, and below what component size, is not decided; the first real run shows how large the component is for Ruta 32 and settles it.
- **Duplicate ids at load (undecided):** INV-30 rejects the pair in this stage. `area-config` could reject it when it loads the config, which fails earlier; that is its contract, not this slice's.
- **Overpass `remark` check:** INV-29 relies on Overpass reporting a runtime error as a `remark` element inside a 200 answer. If that changes, a truncated extract can pass the download.
- **Replacing the extract is not atomic across files:** a crash between replacing `roads.osm` and `features.osm` can still leave a mixed extract. `extract_date.txt` is written last, so a stale date is the sign.

- **Referral hospital ids and criterion (Ian):** the list and the criterion for what counts are decided in the zone config (`area-config`). S4 found 27 `amenity=hospital` features in the corridor, including a dental clinic, a blood bank and a psychiatric hospital.
- **`unclassified` speed (Ian):** the zone config needs a value with a cited source before the real run; until then the real run stops by INV-17, which is the intended behavior.
- **Approximate re-snap (S4′):** the spike re-snapped from the current node because the coordinates were not kept; this slice snaps from the original coordinates, so the real-run numbers may differ from S4′'s. Compare once on the real extract.
- **`MAX_EDGE_M` and `MAX_SNAP_M`:** code constants, not zone parameters. Revisit if a second zone needs different values, and when `closure-units` sees what edge length it needs.
- **OSM snapshot:** Overpass returns live data, so INV-12 only holds for the same download. Whether to keep the raw extract outside git, and where, is open; only its date is recorded.
- **Parity with `graph.ts`:** the browser must reproduce `impact-scoring`'s numbers from this file; integer costs make that exact, and it is checked there, not here.
- **Network-area dependency:** the zone's `bbox` must include the alternates; nothing here can check that it does.
- **Docs out of sync:** `context/structure.md` §4 still describes the P3 stage with the config proposal of the `area-config` era; a person updates it.

## Acceptance criteria

- ACC-01 [none]
  Given the graph built for the Ruta 32 zone, when every edge whose `road` is `"Ruta 32"` and whose `from`/`to` midpoint longitude lies in `[-83.98, -83.92]` (Ruta 32 inside Braulio Carrillo, both carriageways) is removed, then a path still exists from the node of the Calderón Guardia hospital to the node of the community named "Guápiles".
- ACC-02 [manual]
  Given the graph built for the Ruta 32 zone, when Ian computes the baseline time from the Calderón Guardia hospital to the community "Guápiles", then Ian judges it plausible against a cited reference (S4 corridor spike: 68.8 min to Hospital Guápiles).
