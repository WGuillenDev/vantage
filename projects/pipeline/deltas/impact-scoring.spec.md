---
slice: impact-scoring
---

# impact-scoring: spec

> Closes one closure unit at a time, measures what each community loses in access to a referral hospital, ranks the units and writes the zone's `scenarios.json` (task P5, with the metric decision E5).

## Intent

A road stretch matters because of who loses a good route to a referral hospital if it is cut. This slice answers that per closure unit: extra time, people who depend on it, communities left with no route, and a criticality ranking that tells the monitor which stretches matter most. The product is the consequence of a closure, not a prediction of one (D8). The browser repeats the same computation for multi-segment closures, so the numbers must be exactly reproducible from `graph.json`.

## Scope

Owns:

- Baseline: fastest time from each community to the nearest referral hospital with no closures.
- One-at-a-time closure of each unit: per-community time, extra time, isolation.
- Per-unit aggregates: `extra_time_s`, `population_dependent`, `criticality`, affected, isolated and suspect lists.
- Ranking.
- Copying each unit's id, edges and length from `closure-units`, and the zone's alternate routes.
- The public scoring function `score`, which the writer of `output/<id>/scenarios.json` also calls.
- Writing `output/<id>/scenarios.json`.

Non-goals:

- Building the network and the referral hospitals: `road-graph`. Population: `population-data`. Units and their ids: `closure-units`.
- Writing `exposure`: `rain-context` adds it to this file afterwards.
- Renumbering ids or rewriting `graph.json`: ids are place-based and come from `closure-units`; this slice never writes `graph.json`.
- Multi-unit closures: computed in the browser by `graph.ts`.
- Deciding which referral hospitals count: the zone config, through the hospitals of `graph.json`.
- Correcting false isolations: they are marked, not removed, and corrected in `road-graph` after the manual review (`RELIABILITY.md` step 2).
- Predicting whether a unit will close, or any radar evidence.

## Contract

Inputs (the stage runs after `closure-units`):

| Input | Notes |
|---|---|
| Zone | A loaded zone from `area-config`: `id`, `closure.alternates`. |
| `output/<id>/graph.json` | With population and `candidate_id` filled. Its hospitals are the zone's referral hospitals. |
| `work/<id>/closure_units.json` | From `closure-units`: per unit `id`, `edge_ids`, `length_m`. |

Output: `output/<id>/scenarios.json`, shaped as `projects/contract/schemas/scenarios.schema.json` at `schema_version` `"0.3"`.

Public function (decided 15 Nov, for `rank-sensitivity`): besides the file, the stage exposes `score(graph, units, alternates=())` in `pipeline.impact_scoring`.

| Part | Contract |
|---|---|
| `graph` | The content of `graph.json`, already loaded. Hospitals (`graph["hospitals"]`) and every `time_s` are read from it, never from the zone config or a module value. |
| `units` | A list of `{id, edge_ids, length_m}`, already loaded. |
| `alternates` | A list of `{name, vehicles}`, copied to every unit; empty by default, so the function does not depend on the zone config. |
| Returns | The content of `scenarios.json`: a dict with `schema_version`, `baseline` and `candidates`. Not a tuple, and it never rewrites the graph. |

`rank-sensitivity` calls it as `scorer(graph, units)` with copies of the graph (every `time_s` scaled, or one hospital less) and compares the unperturbed result with the whole `scenarios.json`. For that comparison to hold, the caller binds the zone's alternates into the scorer it passes (for example with `functools.partial`). The signature is a commitment: it changes only by changing this spec.

Definitions (all times are integer seconds, because every `time_s` in `graph.json` is an integer):

| Term | Definition |
|---|---|
| Route | Directed path from the community's node to a hospital's node, following `oneway` edges only `from → to`, cost = sum of `time_s` as written in `graph.json`. |
| Nearest referral hospital | The hospital with the lowest route time; on a tie, the lowest hospital id by number (`h2` before `h10`). |
| Closing a unit | Removing all of its `edge_ids`, in both directions. |
| Isolated | After closing, no route to **any** referral hospital. `time_s`, `extra_s` and `hospital_id` are `null`. The UI says "sin ruta al hospital de referencia". |
| Affected | Had a route in the baseline, and after closing either is isolated or has `extra_s > 0`. A community with no baseline route is never affected. |
| `extra_s` | `time_s` after closing − baseline `time_s`. |
| `extra_time_s` | Max `extra_s` over affected non-isolated communities; `null` if every affected community is isolated; `0` if none is affected. |
| Penalty | The largest finite `extra_s` over all units' affected communities; `0` if none exists. |
| `criticality` | Σ over affected communities of `population × extra_s`, using the penalty as `extra_s` for isolated ones; `population: null` adds 0. Suspect isolated communities count like any other isolated one (decided 14 Nov). |
| `population_dependent` | Sum of the known populations of affected communities; `null` only when none of them has a population (including when there are none affected). |
| Suspect isolation | An isolated community is suspect if its node is an endpoint (`from` or `to`) of a closed edge, or if after closing it is still joined to a hospital when edge direction is ignored (isolated only because of `oneway`). Listed in `suspect_isolated_community_ids`, a subset of `isolated_community_ids`. |
| Ranking | `criticality` desc → isolated count desc → `extra_time_s` desc with `null` last → smallest edge id (by number) in `edge_ids`. `rank` = position, starting at 1. Every unit appears, including those with no impact (the UI hides them and counts them). |
| Fixed fields | `source: "network_consequence"`, `zone_ids: []`, `mean_delta_db: null` on every unit; no `exposure`. |
| `alternates` | The zone's `closure.alternates`, copied to every unit (empty when the config lists none). |
| Array order | `baseline` and `per_community` by community id number; `affected_community_ids`, `isolated_community_ids`, `suspect_isolated_community_ids` and `edge_ids` by id number; `candidates` by `rank`. |

Decision notes:

- Isolated count ranks before `extra_time_s` (team decision, 14 Nov): losing every path is worse than a longer one. Without population every `criticality` is 0 and the tie-break is the whole ranking.
- `extra_time_s = 0` for a unit with no affected community is a measured result, not an unknown.

## Invariants

- INV-01 [none]
  When impact-scoring finishes, the `scenarios.json` it wrote passes `make validate` together with the zone's `graph.json`.
- INV-02 [none]
  When impact-scoring writes `baseline`, it lists every community in `graph.json` exactly once, with the nearest-referral-hospital route time and hospital id, or `null` for both when no route exists.
- INV-03 [none]
  When a unit is closed, impact-scoring lists a community as affected exactly when it had a baseline route and is then isolated or has `extra_s > 0`.
- INV-04 [none]
  When impact-scoring writes a unit, `per_community` lists exactly its affected communities.
- INV-05 [none]
  When a community has no route to any referral hospital after closing, impact-scoring lists it in `isolated_community_ids` with `time_s`, `extra_s` and `hospital_id` set to `null`.
- INV-06 [none]
  When impact-scoring writes a unit, `extra_time_s` is the maximum `extra_s` among its affected non-isolated communities, `null` if all affected communities are isolated, and `0` if none is affected.
- INV-07 [none]
  When impact-scoring writes a unit, `criticality` equals the sum over its affected communities of population times `extra_s`, where isolated communities use the penalty and `null` populations add 0.
- INV-08 [none]
  When impact-scoring computes the penalty, it uses the largest finite `extra_s` across all units, or 0 if there is none.
- INV-09 [none]
  When impact-scoring writes a unit, `population_dependent` is the sum of the known populations of its affected communities, or `null` if none is known.
- INV-10 [none]
  When impact-scoring ranks units, it orders them by `criticality` desc, then isolated count desc, then `extra_time_s` desc with `null` last, then smallest edge id, and sets `rank` 1, 2, … in that order.
- INV-11 [none]
  When impact-scoring writes a unit, its `id`, `edge_ids` and `length_m` equal the unit's entry in `closure_units.json`, and no id is renumbered.
- INV-12 [none]
  When impact-scoring writes a unit, it has `source` `"network_consequence"`, empty `zone_ids`, `mean_delta_db` `null` and no `exposure` field.
- INV-13 [none]
  When two referral hospitals are reached in the same time, impact-scoring reports the one with the lowest id number.
- INV-15 [none]
  When impact-scoring writes a unit, its `alternates` equal the zone's `closure.alternates`.
- INV-18 [none]
  When impact-scoring writes `scenarios.json`, every unit of `closure_units.json` appears exactly once, including units with no affected community.
- INV-19 [none]
  When impact-scoring writes a unit, `suspect_isolated_community_ids` is exactly the set of its isolated communities whose node is an endpoint of a closed edge or is still joined to a referral hospital when edge direction is ignored.
- INV-20 [none]
  When a community is suspect, impact-scoring still counts it in `isolated_community_ids`, in `criticality`, in the isolated count used for ranking and in `affected_community_ids`.
- INV-21 [none]
  impact-scoring exposes `score(graph, units, alternates=())`, a function that returns the content of `scenarios.json` for the graph, units and alternates it is given.
- INV-22 [none]
  When impact-scoring writes `scenarios.json`, its content is exactly what `score` returns for the same graph, units and the zone's alternates.
- INV-23 [none]
  When `score` runs, it derives its result only from its arguments: it reads no file, zone config or module-level value, and it leaves its arguments unmodified.
- INV-24 [none]
  When `score` is called twice with equal arguments, the two results serialize to identical JSON.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; the old spec on `origin/feat/impact-scoring` had 19 tests and `impact_scoring.py`, and `builder` ports them to zones and units and turns each tag into `test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_impact_scoring.py`): INV-01 to INV-13, INV-15, INV-18, INV-19, INV-20, ACC-01 to ACC-04. INV-21 to INV-24 (the public function, added 15 Nov) are `none` too; their tests are plain unit tests on `score`, including one that passes a graph with scaled `time_s` and one hospital less and checks the result follows it.

- **Parity with `graph.ts`:** the browser must use the same route direction (community → hospital), the same tie rule and the same "affected" rule. It does not compute suspect marks. The contract mock is the proposed shared fixture (agree with Iván).
- **Suspect rule limits:** it only knows the two causes found in S4′ (snapped to the closed unit, isolated by `oneway`). Other artifacts, such as a community adjusted to a wrong road, are not detected; the manual review (P12) looks for them.
- **Suspect counted in the ranking:** decided to keep them in, flagged for the UI. Reopen if the manual review shows they dominate the top of the list.
- **`closure.alternates` source:** the zone config must cite where the alternates come from; for Ruta 32 the old spec named Ruta 126 (light) and Ruta 10 (freight) from "project knowledge", without a source. Pending (Ian).
- **Referral set meaning:** an isolated community may have a nearer regional hospital; the UI wording "sin ruta al hospital de referencia" carries that (D8). The referral hospital list is still pending (Ian).
- **Performance:** one search per unit over a graph of about 8 700 edges is cheap, but the number of units is open (`closure-units`).
- **Mock fixture:** ACC-01 to ACC-04 use the contract mock; `contract-update` rewrites it for 0.3, and these criteria must be checked against that mock, not the 0.1 one.
- **Old `score`:** the function of `origin/feat/impact-scoring` returned a tuple `(scenarios, graph)`, renumbered the ids by rank and took the alternates from a module constant tied to "Ruta 32". None of that survives: the contract above returns only the scenarios and takes the alternates as an argument.
- **Binding the alternates (`pipeline-run`):** `rank-sensitivity` raises "the baseline is not reproducible" when `scorer(graph, units)` differs from the whole `scenarios.json`. The wiring that builds the scorer must therefore bind the zone's alternates; `pipeline-run` owns that wiring, and an unbound scorer would fail the check on every run.
- **Cross-slice edits:** `area-config` gains the required list `closure.alternates` (may be empty), updated with this spec. The old rule "final ids in rank order, graph.json rewritten" is dropped (see `closure-units`).

## Acceptance criteria

- ACC-01 [none]
  Given the contract mock as input, when impact-scoring runs, then the unit with `edge_ids ["e3"]` gets `rank` 1 and `criticality` 2 622 000 even though the one with `["e2"]` has the larger `extra_time_s` (1200).
- ACC-02 [none]
  Given the contract mock as input, when impact-scoring runs, then baseline, per-community values, `extra_time_s`, `population_dependent`, `criticality` and `rank` match `projects/contract/examples/scenarios.json` for each unit matched by `edge_ids` (ids and `alternates` are excluded).
- ACC-03 [none]
  Given a graph where a unit's closure leaves no community affected, when impact-scoring runs, then that unit has `extra_time_s` 0, `criticality` 0, `population_dependent` `null` and empty affected, isolated and suspect lists.
- ACC-04 [none]
  Given two units with `criticality` 0, one with an isolated community and `extra_time_s` `null` and the other with no isolated community and `extra_time_s` greater than 0, when impact-scoring ranks them, then the one with the isolated community gets the better `rank`.
- ACC-05 [manual]
  Given the real Ruta 32 run, when a person reads `scenarios.json`, then the units of the Braulio Carrillo stretch have affected communities greater than 0 (the stretch counts, as it did under R2 in S4′) and at least one unit has `extra_time_s` greater than 0.
