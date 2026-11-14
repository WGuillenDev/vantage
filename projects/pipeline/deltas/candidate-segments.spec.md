---
slice: candidate-segments
---

# candidate-segments: spec

> Finds the road stretches that a detected change zone touches, groups them into candidate segments and marks them in `graph.json` (task P4).

## Intent

A radar change zone is a signal on a hillside, not a closed road. This slice ties that signal to the network: every road stretch that passes within a margin of a change zone becomes a **candidate segment**, a place to verify on the ground. It is the bridge between step 1 of the method (where the terrain changed, from P2) and step 3 (what happens if it is cut, in P5).

## Scope

Owns:

- Deciding which edges of `graph.json` a change zone touches, with a margin.
- Grouping touched edges into candidates, with their `zone_ids` and `mean_delta_db`.
- Provisional `T-xx` ids, written both in the candidate list and as `candidate_id` in `graph.json`.

Non-goals:

- Building the network or splitting edges: `road-graph` (P3). Edges are at most 1000 m long when they arrive here.
- Final ids, ranking and impact: `impact-scoring` (P5) renumbers by rank and rewrites `candidate_id`.
- Detecting change or producing `change.geojson`: P2 (Ron). Until the real file exists, this slice runs on the contract mock.
- Judging whether a zone is a landslide: a candidate is always a signal to verify.
- Any schema change.

## Contract

Inputs:

| Input | Notes |
|---|---|
| `projects/pipeline/output/graph.json` | From `road-graph`: every `candidate_id` is `null`. |
| `change.geojson` | Contract shape (`change.schema.json` v0.1). Zones are `Polygon` or `MultiPolygon`, each with `id`, `area_m2` and `mean_delta_db`. Default path `projects/pipeline/output/change.geojson`. |
| `MARGIN_M` | Margin around each zone, in meters. **Provisional value 50 m** (Ian, 14 Nov), to revisit when S2 gives real zone sizes. |

Outputs:

- `projects/pipeline/work/candidates.json` (intermediate, not committed), the interface `impact-scoring` already reads:

  ```json
  { "candidates": [ { "id": "T-01", "edge_ids": ["e12", "e13"], "zone_ids": ["z1"], "mean_delta_db": -4.2 } ] }
  ```

- `projects/pipeline/output/graph.json`, identical to the input except that each candidate edge carries its provisional `candidate_id`.

Rules:

| Topic | Rule |
|---|---|
| Touch | An edge touches a zone when its `geometry` polyline comes within `MARGIN_M` meters of the zone's polygon (distances in meters, not degrees). |
| Eligible edges | Every edge of `graph.json`, whatever its road class or `road` value. |
| Grouping | Touched edges that share a node and have the same `road` value (`null` counts as a value) form one candidate. A change of `road` starts another candidate. An edge belongs to exactly one candidate by construction. |
| `edge_ids` | Sorted by edge id number. |
| `zone_ids` | Every zone touched by at least one of the candidate's edges, sorted by zone id number. |
| `mean_delta_db` | Area-weighted mean of the touched zones: Σ(`mean_delta_db` × `area_m2`) / Σ `area_m2`. If that area sum is 0, the plain mean. Never made up; since every candidate touches at least one zone, it is always a number. |
| Provisional ids | `T-01`, `T-02`, … ordered by the smallest edge id number in each candidate. They follow the schema pattern `^T-\d{2,}$`, and P5 replaces them. |
| No zones | A `change.geojson` with no features, or with zones that touch no edge, gives `{"candidates": []}` and a `graph.json` equal to the input. |

## Invariants

- INV-01 [none]
  When candidate-segments finishes, the `graph.json` it wrote passes the graph schema and every non-null `candidate_id` names a candidate in `candidates.json`.
- INV-02 [none]
  When candidate-segments marks an edge, that edge's geometry lies within `MARGIN_M` meters of at least one zone listed in its candidate's `zone_ids`.
- INV-03 [none]
  When an edge's geometry lies within `MARGIN_M` meters of any zone, candidate-segments puts it in exactly one candidate.
- INV-04 [none]
  When candidate-segments writes a candidate, all its edges have the same `road` value and form one connected chain through shared nodes.
- INV-05 [none]
  When two touched edges share a node and have the same `road` value, candidate-segments puts them in the same candidate.
- INV-06 [none]
  When candidate-segments writes a candidate, `mean_delta_db` equals the area-weighted mean of its zones' `mean_delta_db`, or their plain mean when their total area is 0.
- INV-07 [none]
  When candidate-segments assigns provisional ids, they are `T-01`, `T-02`, … in ascending order of each candidate's smallest edge id number.
- INV-08 [none]
  When candidate-segments writes `graph.json`, every field other than `candidate_id` equals the input `graph.json`, and edges outside every candidate keep `candidate_id: null`.
- INV-09 [none]
  If the input `graph.json` already has a non-null `candidate_id`, then candidate-segments exits non-zero with an English error naming the edge and writes no output.
- INV-10 [none]
  If `change.geojson` fails its schema, then candidate-segments exits non-zero with an English error from the validator and writes no output.
- INV-11 [none]
  When candidate-segments runs twice on the same inputs and `MARGIN_M`, both `candidates.json` and both `graph.json` files are byte-identical.

## Deferred / Open questions

- **`MARGIN_M`** (Ian, after S2 from Ron): 50 m is provisional; Ron delivers the real `change.geojson` and the typical zone size from S2.
- **Real `change.geojson`** (Ron, P2): until then, runs use `projects/contract/examples/change.geojson`, whose zones are fake.
- **Candidates on parallel roads** (Ian): a zone between two parallel roads marks both; this spec accepts it, because the ranking decides which matters.
- **Testing gaps:** INV-01 to INV-11 and ACC-01 to ACC-03 are `none` until `/builder candidate-segments` adds tests.

## Acceptance criteria

- ACC-01 [none]
  Given a small fixture graph with one road crossed by one zone, when candidate-segments runs with `MARGIN_M` 50, then exactly the edges within 50 m of the zone form one candidate `T-01` with that zone's id and `mean_delta_db`.
- ACC-02 [none]
  Given a fixture where one zone touches a `Ruta 32` edge and the side road joined to it at a shared node, when candidate-segments runs, then it writes two candidates, one per `road` value.
- ACC-03 [none]
  Given the `candidates.json` and `graph.json` that candidate-segments wrote from a fixture, when `impact-scoring` reads them, then it accepts them without an input error.
