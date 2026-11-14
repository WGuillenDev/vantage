---
slice: impact-scoring
---

# impact-scoring: spec

> Closes one candidate segment at a time, measures what each community loses in hospital access, ranks the candidates and writes `scenarios.json` plus the final `graph.json` (task P5).

## Intent

A change zone on a road is only a signal; what makes it matter is who loses a good route to a hospital if that stretch is cut. This slice answers that per candidate: extra time, people who depend on it, communities left with no path, and a criticality ranking that tells the monitor which candidates to verify first. The browser repeats the same computation for multi-segment closures, so the numbers must be exactly reproducible from `graph.json`.

## Scope

Owns:

- Baseline: fastest time from each community to its nearest hospital with no closures.
- One-at-a-time closure of each candidate: per-community time, extra time, isolation.
- Aggregates per candidate: `extra_time_s`, `population_dependent`, `criticality`, affected and isolated lists.
- Ranking, final `T-xx` ids, and rewriting `candidate_id` in `graph.json` to those ids.
- `alternates` per candidate.

Non-goals:

- Building the network, speeds, snapping, population: `road-graph` (P3).
- Choosing which edges form a candidate, its `zone_ids` and `mean_delta_db`: `candidate-segments` (P4). This slice copies them.
- Multi-segment closures: computed in the browser by `graph.ts` from `graph.json`.
- `meta.json` and `make all`: P7 (Ron).
- Any schema change. Everything here fits `scenarios.schema.json` and `graph.schema.json` v0.1.

## Contract

Inputs:

| Input | Notes |
|---|---|
| `graph.json` from P4 | Contract shape, with **provisional** `candidate_id`s on candidate edges. |
| Candidate list from P4 | Per provisional candidate: its edges, `zone_ids`, `mean_delta_db` (number or `null`). Shape defined in `candidate-segments`. |

Outputs, both in `projects/pipeline/output/`:

- `scenarios.json` (`scenarios.schema.json` v0.1).
- `graph.json`, identical to the input except that every `candidate_id` is replaced by the final id.

Definitions (all times are integer seconds, because every `time_s` in `graph.json` is an integer):

| Term | Definition |
|---|---|
| Route | Directed path from the community's node to a hospital's node, following `oneway` edges only `from → to`, cost = sum of `time_s` as written in `graph.json`. |
| Nearest hospital | Hospital with the lowest route time; on a tie, the lowest hospital id by number (`h2` before `h10`). |
| Closing a candidate | Removing all of its `edge_ids`, in both directions. |
| Isolated | After closing, no route to **any** hospital. `time_s`, `extra_s` and `hospital_id` are `null`. |
| Affected | Had a route in the baseline, and after closing either is isolated or has `extra_s > 0`. A community with no route in the baseline is never affected. |
| `extra_s` | `time_s` after closing − baseline `time_s`. |
| `extra_time_s` | Max `extra_s` over affected non-isolated communities; `null` if every affected community is isolated; `0` if no community is affected. |
| Penalty | Largest finite `extra_s` over all candidates' affected communities; `0` if none exists. |
| `criticality` | Σ over affected communities of `population × extra_s`, using the penalty as `extra_s` for isolated ones; `population: null` adds 0. |
| `population_dependent` | Sum of the known populations of affected communities; `null` only when none of them has a population (including when there are no affected communities). |
| Ranking | `criticality` desc → isolated count desc → `extra_time_s` desc with `null` last → smallest edge id (by number) in `edge_ids`. `rank` = position, starting at 1. |
| Final ids | `T-01`, `T-02`, … in rank order (two digits minimum, more if needed). Ids change between runs because the ranking does; they are not quoted in the presentation. |
| Joint write | `graph.json` and `scenarios.json` are written together, after the `contracts.md` §8 cross-reference checks pass on the pair. |
| `alternates` | `[{"name": "Ruta 126", "vehicles": "light"}, {"name": "Ruta 10", "vehicles": "freight"}]` when any of the candidate's edges has `road: "Ruta 32"`; otherwise `[]`. |
| Array order | `baseline` and `per_community` by community id number; `affected_community_ids`, `isolated_community_ids`, `edge_ids`, `zone_ids` by id number; `candidates` by `rank`. |

Decision notes:

- The ranking puts isolated count before `extra_time_s` (team decision, 14 Nov), because losing every path is worse than a longer one. Without population every `criticality` is 0, so the tie-break is the whole ranking. `contracts.md` §6 and §11 and the STATUS decision log were updated to match.
- `extra_time_s = 0` for a candidate with no affected community is a measured result, not an unknown. Spike S4 found such a case (Ruta 32 inside Braulio Carrillo with hospitals on both sides).

## Invariants

- INV-01 [none]
  When impact-scoring finishes, the `scenarios.json` and `graph.json` it wrote pass `make validate` together with the `change.geojson` they refer to.
- INV-02 [none]
  When impact-scoring writes `baseline`, it lists every community in `graph.json` exactly once, with the nearest-hospital route time or `null` when no route exists.
- INV-03 [none]
  When a candidate is closed, a community is listed as affected exactly when it had a baseline route and is then isolated or has `extra_s > 0`.
- INV-04 [none]
  When impact-scoring writes a candidate, `per_community` lists exactly its affected communities.
- INV-05 [none]
  When a community has no route to any hospital after closing, impact-scoring lists it in `isolated_community_ids` with `time_s`, `extra_s` and `hospital_id` set to `null`.
- INV-06 [none]
  When impact-scoring writes a candidate, `extra_time_s` is the maximum `extra_s` among its affected non-isolated communities, `null` if all affected communities are isolated, and `0` if none is affected.
- INV-07 [none]
  When impact-scoring writes a candidate, `criticality` equals the sum over its affected communities of population times `extra_s`, where isolated communities use the penalty and `null` populations add 0.
- INV-08 [none]
  When impact-scoring computes the penalty, it uses the largest finite `extra_s` across all candidates, or 0 if there is none.
- INV-09 [none]
  When impact-scoring writes a candidate, `population_dependent` is the sum of the known populations of its affected communities, or `null` if none is known.
- INV-10 [none]
  When impact-scoring ranks candidates, it orders them by `criticality` desc, then isolated count desc, then `extra_time_s` desc with `null` last, then smallest edge id, and sets `rank` 1, 2, … in that order.
- INV-11 [none]
  When impact-scoring assigns ids, the candidate with `rank` n gets id `T-` followed by n zero-padded to at least two digits.
- INV-12 [none]
  When impact-scoring writes `graph.json`, every candidate edge carries its final id and every other field equals the input `graph.json`.
- INV-13 [none]
  When impact-scoring writes a candidate, `zone_ids` and `mean_delta_db` equal what P4 gave for it.
- INV-14 [none]
  When two hospitals are reached in the same time, impact-scoring reports the one with the lowest id number.
- INV-15 [none]
  When impact-scoring runs twice on the same inputs, both output files are byte-identical.
- INV-16 [none]
  When impact-scoring writes a candidate, `alternates` is Ruta 126 (light) and Ruta 10 (freight) if any of its edges has `road: "Ruta 32"`, and empty otherwise.
- INV-17 [none]
  If the `contracts.md` §8 cross-reference checks fail on the pair it is about to write, then impact-scoring exits non-zero with an English error naming the failed check and writes neither `graph.json` nor `scenarios.json`.

## Deferred / Open questions

- **Candidate list shape from P4** (Ian, in `candidate-segments`): provisional id format, file or in-memory hand-off.
- **Population source and method** (Wilberth via S7, then Ian or team): until decided every population is `null`, so `criticality` is 0 everywhere and the ranking runs on isolated count and `extra_time_s`.
- **Parity with `graph.ts`** (Iván): the browser must use the same route direction (community → hospital), the same tie rule for hospitals and the same "affected" rule. A shared fixture (the contract mock) is the proposed check; agree with Iván.
- **Metric fit for G1** (team, at G1): the S4 measurement on the real network found 215 of 495 test segments (43 %) affecting nobody and `criticality` 0 everywhere without population. A corridor-connectivity metric may be added after G1 as an additive field with one schema bump (`contracts.md` §10). Until then this spec keeps the current metric.
- **Testing gaps:** INV-01 to INV-17 and ACC-01 to ACC-04 are `none` until `/builder impact-scoring` adds tests.

## Acceptance criteria

- ACC-01 [none]
  Given the contract mock `graph.json` with its four candidates as P4 input, when impact-scoring runs, then the candidate with `edge_ids ["e3"]` gets `rank` 1 and `criticality` 2 622 000 even though the one with `["e2"]` has the larger `extra_time_s` (1200).
- ACC-02 [none]
  Given the contract mock as input, when impact-scoring runs, then baseline, per-community values, `extra_time_s`, `population_dependent`, `criticality` and `rank` match `projects/contract/examples/scenarios.json` for each candidate matched by `edge_ids` (ids and `alternates` are excluded, since the mock's ids are not in rank order and its `road` values are fake).
- ACC-03 [none]
  Given a graph where a candidate's closure leaves no community affected, when impact-scoring runs, then that candidate has `extra_time_s` 0, `criticality` 0, `population_dependent` `null` and empty affected and isolated lists.
- ACC-04 [none]
  Given two candidates with `criticality` 0, one with an isolated community and `extra_time_s` `null` and the other with no isolated community and `extra_time_s` greater than 0, when impact-scoring ranks them, then the one with the isolated community gets the better `rank`.
