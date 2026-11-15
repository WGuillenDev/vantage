---
slice: segment-ranking
---

# segment-ranking: spec

> Shows the zone's closure units as a list ordered by criticality, and selects a unit when its row is clicked (task F3).

## Intent

The user monitors a corridor and wants to know where to look first. The ranked list answers it in one glance: which stretches, if cut, hurt access to a referral hospital the most, how much extra time that means and how many people depend on them. Units that change nothing are not shown, only counted, so the list stays short and the user can still tell that the others were checked.

## Scope

Owns:

- The list of units with impact, in rank order, with the counter of units without impact.
- The row content: label, extra time, dependent population, criticality bar, long-corridor badge.
- The search box and the filter (all, without route, with suspect isolations) that narrow the list.
- Selecting a unit from the list, and keeping the list in step with the selection made on the map.

Non-goals:

- The map and the selected-unit state: `map-corridor`. The detail card: `segment-detail`. Closing units: `closure-whatif`.
- Suspect-isolation marks and the "estimate" labels: `trust-signals`.
- Sorting controls: the order is the pipeline's `rank`, always. The search box and the kind filter only narrow the list, never reorder it.
- Computing rank, criticality or any number: all come from `scenarios.json`.

## Contract

Reads `scenarios.json` and `graph.json` of the active zone, and the store of `map-corridor` (selected unit).

| Topic | Behavior |
|---|---|
| Listed units | The units with at least one affected community, by ascending `rank`. |
| Counter | "N tramos sin impacto" for the others, with the Spanish singular for one. |
| Label | `<road> · <id>`, where `<road>` is the most frequent `road` among the unit's edges, or "Vía sin nombre" if none has one. |
| Length | `length_m` below 1 000 as "N m", otherwise as "N,N km" (comma decimal). |
| Extra time | `extra_time_s` as an approximate duration (rule in `trust-signals`: "< 5 min", "≈ 20 min", "≈ 1 h 15 min"); "sin ruta al hospital de referencia" when `extra_time_s` is `null`. |
| Population | `population_dependent` with thousands separators, labeled "estimada" (`trust-signals`); "sin dato" when `null`, never 0. |
| Search and filter | A text box matches the row label ignoring case and accents; three filter buttons keep all units, those with `extra_time_s` `null`, or those with suspect isolations. Both narrow the list and keep the rank order. |
| Hover | The row under the pointer or with focus is highlighted on the map. |
| Criticality bar | Width proportional to `criticality` over the zone's highest `criticality`; hidden when that highest is 0. |

## Invariants

- INV-01 [test: bun test --cwd projects/frontend source/ranking.test.ts]
  When the list renders, it shows exactly the units with at least one affected community, in ascending `rank`, or a Spanish message saying so when there are none.
- INV-02 [test: bun test --cwd projects/frontend source/ranking.test.ts]
  When the list renders, the counter shows the number of units with no affected community.
- INV-03 [test: bun test --cwd projects/frontend source/ranking.test.ts]
  When a unit's `extra_time_s` is `null`, its row shows "sin ruta al hospital de referencia" and not a time, and when its `population_dependent` is `null`, it shows "sin dato" and never 0.
- INV-05 [test: bun test --cwd projects/frontend source/ranking.test.ts]
  When the zone's highest `criticality` is 0, the list shows no criticality bars and a note that the order comes from extra time and isolated communities because population is unknown.
- INV-07 [test: bun test --cwd projects/frontend source/ranking.test.ts]
  When a row is activated by click or by Enter, the store's selected unit becomes that unit and the row is highlighted.
- INV-08 [none]
  When the selected unit changes from the map, the list highlights its row and scrolls it into view.

- INV-09 [test: bun test --cwd projects/frontend source/ranking.filter.test.ts]
  When the user types a text or picks a filter, the list keeps only the units that match, in the same rank order, ignoring case and accents.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns the formatting and filtering rules into `test: bun test --cwd projects/frontend` files and leaves rendering and focus `manual`): INV-01, INV-02, INV-03, INV-05, INV-07, INV-08.

- **No place names:** units have no name in the data, so the label is a road plus an id that names a place on the corridor, not a rank; a reader cannot tell where "T-07" is without the map. A better label (nearest community) is not decided.
- **Without population:** with no WorldPop the ranking runs on isolated count and extra time (INV-05); until `population-data` runs, every real list will say so.
- **Long lists:** a corridor can give decades of units; no virtual scrolling is planned, and the list scrolls inside its panel.
- **Impact-free units hidden:** they are only counted, as `functions.md` F3 says; the user cannot open one from the list.
- **Docs:** `functions.md` F3 says "segment"; the UI term is "tramo", and the unit id is not the rank (D6).

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 real data, when a person reads the list, then its order matches `rank` in `scenarios.json` and the counter matches the number of units without affected communities.
- ACC-02 [manual]
  Given the list, when a person clicks a row, then the same unit is highlighted on the map and, when they click a unit on the map, then its row is highlighted and visible.
