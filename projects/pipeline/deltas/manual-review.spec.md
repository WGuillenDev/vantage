---
slice: manual-review
---

# manual-review: spec

> Prepares the hand review of isolated communities for three closure units, and computes the verdict once a person has classified them (task P12, `RELIABILITY.md` step 2).

## Intent

No case of the model has been checked by hand. S4′ showed that many "isolated" communities were artifacts: adjusted to the closed road, or cut off only because of a one-way road. A person who knows the area must look at them. This slice cannot replace that judgment, but it can choose the cases by a fixed rule, collect the evidence for each community so the person does not start from zero, refuse to count an unclassified community, and compute the share of real isolations in a way anyone can repeat.

## Scope

Owns:

- Choosing the three units to review by a rule fixed before looking at results.
- Listing, per unit, the isolated communities to review, with automatic evidence and a suggestion.
- Keeping the person's classification, reviewer and date in `reports/<id>/manual_review.json`.
- Computing the counts per class, the share of real isolations and the verdict.

Non-goals:

- Classifying the communities: only a person does it, and the suggestions are not the classification.
- Correcting the artifacts found: that is a change in `road-graph` or `closure-units`, followed by moving the old sheet away (git keeps it) and preparing a new one.
- Reviewing communities that are not isolated, or units other than the three chosen.
- Publishing the review or adding it to the contract.

## Contract

Commands:

| Command | Effect |
|---|---|
| `manual-review prepare --area <id>` | Writes the review sheet with the person's fields empty. |
| `manual-review summarize --area <id>` | Reads the filled sheet, checks it and writes the `summary` and `verdict` into it. |

Inputs: the zone and its files `output/<id>/graph.json` and `scenarios.json`, `work/<id>/closure_units.json` and `work/<id>/communities.json`.

Output: `projects/pipeline/reports/<id>/manual_review.json`:

| Field | Content |
|---|---|
| `reviewer`, `reviewed_on` | Written by the person (name and date); empty after `prepare`. |
| `units[]` | Per chosen unit: `id`, `why` (`highest_criticality`, `median_criticality` or `longest`) and `communities[]`. |
| `communities[]` | `community_id`, `name`, `population`, `distance_to_node_m`, `node_is_closed_endpoint`, `joined_ignoring_direction`, `suggested_class`, and the person's `class` and `note` (empty after `prepare`). |
| `summary`, `verdict` | After `summarize`: counts per class, `share_real`, and `"pass"`, `"fail"` or `"incomplete"`. |

Classes: `real` (no route to a referral hospital in reality), `snapping_artifact` (adjusted to the closed road or to a wrong node), `oneway_artifact` (cut off only by a one-way road), `outside_network` (the place is not served by the road network considered).

Rules:

| Topic | Rule |
|---|---|
| Unit A | The unit with rank 1 (highest criticality). |
| Unit B | Among units with at least one affected community, in rank order, the one at position ⌈n/2⌉ (n units). |
| Unit C | The unit with the greatest `length_m` (ties to the lower id). In Ruta 32 it should be the stretch inside Braulio Carrillo; verified on the first run. |
| Duplicates | A unit chosen once is not chosen again; the next one by that rule is taken. With fewer units than three, as many as exist. |
| Communities per unit | The isolated ones, up to 20, by population descending (`null` last) and then id number. |
| Evidence | `distance_to_node_m`: from the community's original coordinates (`communities.json`) to its snapped node. `node_is_closed_endpoint` and `joined_ignoring_direction`: as defined for suspect isolations in `impact-scoring`. |
| Suggestion | `oneway_artifact` if `joined_ignoring_direction`; else `snapping_artifact` if `node_is_closed_endpoint`; else `null`. No distance threshold is invented. |
| Verdict | `incomplete` if any listed community has no `class`; else `pass` if the share of `real` among all listed communities is at least 0.8, else `fail`. |

## Invariants

- INV-01 [none]
  When `prepare` chooses units, it takes the rank-1 unit, the unit at position ⌈n/2⌉ among units with impact, and the unit with the greatest `length_m`, with ties to the lower id.
- INV-03 [none]
  When `prepare` lists the communities of a unit, they are exactly its isolated communities, up to 20, ordered by population descending with `null` last and then by id number.
- INV-05 [none]
  When `prepare` writes a community, `distance_to_node_m` is measured from its original coordinates in `communities.json` to its snapped node and `suggested_class` is `oneway_artifact` if it is joined ignoring direction, `snapping_artifact` if not and its node is an endpoint of a closed edge, and `null` otherwise.
- INV-06 [none]
  When `prepare` writes the sheet, every `class`, `note`, `reviewer` and `reviewed_on` is empty and `verdict` is absent.
- INV-07 [none]
  If a sheet already exists, then `prepare` exits non-zero with an English error and leaves it unchanged.
- INV-09 [none]
  If `reviewer` or `reviewed_on` is empty, then `summarize` exits non-zero with an English error naming the field and does not change the sheet.
- INV-10 [none]
  If a `class` is not one of the four classes, then `summarize` exits non-zero with an English error naming the community and does not change the sheet.
- INV-11 [none]
  When any listed community has no `class`, `summarize` writes the verdict `incomplete`.
- INV-12 [none]
  When every listed community has a class, `summarize` writes the verdict `pass` if the share of `real` is at least 0.8 and `fail` otherwise.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns each into `test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_manual_review.py`): INV-01, INV-03, INV-05, INV-06, INV-07, INV-09, INV-10, INV-11, INV-12.

- **Criterion changed from `RELIABILITY.md` (decided 14 Nov):** it fixed the third case as "the unit that crosses Braulio Carrillo", a fixed datum of Ruta 32 (D3). It is now the longest unit, which should be the same stretch; if the first run shows it is not, add the park unit by hand as a fourth case and record it. A person updates the doc.
- **Who reviews:** needs someone who knows the area. `reviewer` makes the author explicit. Unassigned (`RELIABILITY.md` §6); without a person the step stays at "artifacts detected by rules".
- **Sampling bias:** taking the 20 most populated isolated communities favors the larger places; the share of real isolations says nothing about the small ones.
- **Share over all communities:** the 80 % is over all listed communities of the three units, not per unit, as `RELIABILITY.md` states it.
- **Correction loop:** artifacts found are fixed in `road-graph` or `closure-units`, then the old sheet is moved away and `prepare` runs again; git history keeps the earlier sheet (no round counter, purged 14 Nov).
- **`outside_network`:** the person judges it; the tool offers no suggestion because no distance threshold exists.
- **`make` targets:** `make review-prepare AREA=<id>` and `make review-summary AREA=<id>` are added with this slice.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 run, when a person runs `prepare`, then the sheet names three units and, for each, its isolated communities with the automatic evidence, and no community is classified.
- ACC-02 [manual]
  Given a sheet filled in by a person who knows the area, when `summarize` runs, then the verdict states the share of real isolations, and the artifact cases are listed so they can be corrected before preparing a new sheet.
