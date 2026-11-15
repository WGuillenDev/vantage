---
slice: closure-units
---

# closure-units: spec

> Splits the studied road of a zone into closure units (both carriageways together, between junctions) and writes their ids into `graph.json` (task P9).

## Intent

The spikes showed that the useful question is "which stretch of the corridor, if cut, leaves communities without a route to a referral hospital". Spike S4′ answered it with 19 units of 1 to 61 km, because it chained every stretch to its parallel carriageway through a 120 m window and merged whatever overlapped. A 61 km unit says "the corridor is critical", not "this stretch is". This slice defines a finer unit: a stretch between two consecutive junctions, always closed with both carriageways, so a closure cannot leave one direction open and fake an isolation (87 % of Ruta 32 in OSM is one-way pairs).

## Scope

Owns:

- Choosing which edges are closure candidates, from the zone's `closure.roads`.
- Cutting those edges into units at junctions, keeping both carriageways of a stretch in one unit.
- Each unit's stable id and its length along the road.
- Writing the unit ids into `candidate_id` of `output/<id>/graph.json`.
- Writing `work/<id>/closure_units.json`, an intermediate file that `impact-scoring` reads.

Non-goals:

- Building or snapping the network: `road-graph`. Population: `population-data`.
- Closing a unit, measuring impact, ranking: `impact-scoring`. This slice never computes a route.
- Cutting a junction-free stretch into smaller pieces. Cutting it anywhere has the same consequence, so it stays one unit.
- Chainage or kilometre posts: OSM has almost none (S1), so units are cut by junctions only.
- Changing the `graph.json` schema: `contract-update`.
- Choosing the roads to study: that is the zone config. This slice never names Ruta 32.

## Contract

Inputs:

| Input | Notes |
|---|---|
| Zone | A loaded zone from `area-config`: `id` and `closure.roads`, a non-empty list of `road` values (for Ruta 32: `["Ruta 32"]`). |
| `output/<id>/graph.json` | From `road-graph`, filled by `population-data`. Every `candidate_id` is `null`. |

Outputs:

- `output/<id>/graph.json`, identical to the input except that every corridor edge has its unit id in `candidate_id`.
- `work/<id>/closure_units.json`: one entry per unit with `id`, `edge_ids` and `length_m`. Not part of the shared contract and never published.

Code constant (not a zone parameter): `PAIR_M` = 120.

Rules:

| Topic | Rule |
|---|---|
| Corridor edges | Edges whose `road` is one of the zone's `closure.roads`. All other edges keep `candidate_id: null` and are never closed. |
| Junction | A node where a corridor edge meets an edge of another road, or ends (undirected degree other than 2). Any road class in the graph counts, including ramps and `unclassified` (decided 14 Nov, as in S4′). |
| Unit | The corridor edges between two consecutive junctions, including both carriageways. |
| Carriageway pairing | A one-way corridor edge is paired with the nearest corridor edge of opposite direction whose midpoint is within `PAIR_M` of its own. A pair is never split between units. |
| Length | `length_m` is the length of the unit along the road, counting a paired stretch once: for two parallel one-way carriageways it is the longer one's total edge length; for a two-way stretch it is the sum of its edge lengths. |
| Ids | `T-01`, `T-02`, … (two digits minimum), numbered by ascending midpoint longitude of the unit, then latitude. An id names a place on the corridor, not a rank; `impact-scoring` copies it and never renumbers (reverses its earlier rule of final ids in rank order). |
| Order | `edge_ids` in ascending edge number; units in id order. |

## Invariants

- INV-01 [none]
  When closure-units finishes, the `graph.json` it wrote passes `make validate` and differs from its input only in `candidate_id`.
- INV-02 [none]
  When closure-units writes `graph.json`, an edge has a non-null `candidate_id` if and only if its `road` is in the zone's `closure.roads`.
- INV-03 [none]
  When closure-units writes `graph.json`, every corridor edge has exactly one `candidate_id`, and it is in `closure_units.json`.
- INV-04 [none]
  When closure-units numbers the units, the ids are unique, have the form `T-NN`, and follow ascending midpoint longitude with ties broken by latitude.
- INV-05 [none]
  When a one-way corridor edge has an opposite-direction corridor edge whose midpoint is within 120 m, closure-units puts both in the same unit.
- INV-06 [none]
  When a junction joins two consecutive edges of a two-way corridor, closure-units puts them in different units.
- INV-07 [none]
  When a junction lies on both carriageways of a dual carriageway within 120 m, closure-units puts the edges before it and after it in different units.
- INV-09 [none]
  When a unit holds two parallel one-way carriageways of equal length L, closure-units gives it `length_m` equal to L and not 2L.
- INV-11 [none]
  If none of the zone's `closure.roads` matches an edge, then closure-units exits non-zero with an English error naming the roads and writes no output.
- INV-12 [none]
  When closure-units finishes, `work/<id>/closure_units.json` has one entry per unit, and each entry's `edge_ids` is exactly the set of edges carrying that `candidate_id`.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns each into `test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_closure_units.py` against small synthetic networks): INV-01 to INV-07, INV-09, INV-11, INV-12.

- **Offset junctions:** the two carriageways of a dual road may meet a ramp a few hundred metres apart. Pairs are never split, so units near such a junction may merge or extend over the offset; INV-07 only holds when the junction is aligned. Measure on the real extract and decide whether to relax or refine.
- **Number of units:** cutting at every junction may give decades of units on Ruta 32 (S4′ had 19 only because of the 120 m merging). No minimum length is set; revisit after the first real run if slivers of tens of metres flood the ranking.
- **`PAIR_M`:** 120 m (S4′) is a code constant, not a zone parameter; revisit with a second zone. The "about 5 km" of `RELIABILITY.md` step 5 is not a rule here: cutting at every junction already leaves no junction inside a unit, so a long unit is simply a junction-free stretch (the badge "Corredor largo" was dropped; the UI shows the length).
- **Road matching:** `closure.roads` matches the `road` field (`"Ruta <ref>"` or the OSM name). A zone whose studied road has no `ref` must list its OSM name; not tested.
- **Ramps stay open:** links that join the corridor are not part of any unit, so a closure leaves ramps open on both sides. Accepted; they lead nowhere without the road.
- **`impact-scoring` and ids:** the spec of that slice on `origin/feat/impact-scoring` renumbers `T-xx` by rank and rewrites `graph.json`; it must copy the ids from this slice instead (decided 14 Nov).
- **Docs and cross-slice edits:** `area-config` gains the required key `closure.roads`, and `contract-update` defines `length_m` as the length along the road, not summed over carriageways. Both specs were updated with this one.
- **Wording:** the contract keeps the key name `candidates` for units; the UI says "tramo" (D6).

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 zone with the real extract, when closure-units runs, then there are more than 19 units, and the stretch inside Braulio Carrillo is a single unit or very few.
- ACC-02 [manual]
  Given three units of the Ruta 32 result (the largest by criticality once scored, a mid-sized one and the one crossing Braulio Carrillo), when a person draws their edges on the map, then both carriageways are highlighted over the same stretch.
