---
slice: closure-whatif
---

# closure-whatif: spec

> Lets the user close one or several units and see, instantly and without a server, how access to the referral hospital changes (task F5).

## Intent

The ranking closes one unit at a time, but real events close several stretches together. The user needs to try those combinations and read the result at once: who loses the route, who gets a longer trip, and by how much. The browser computes it from `graph.json` with the same rules as the pipeline, so that closing a single unit gives exactly the numbers in `scenarios.json`. `graph.ts` already does this for one community at a time; this slice makes it fast enough for a real zone and builds the interface around it.

## Scope

Owns:

- The closed set of units in the store, with add, remove and reset.
- `graph.ts` (`computeAccess`): time and hospital per community for a set of closed edges, now with one search from the referral hospitals instead of one per community.
- The simulation panel: chips, reset, summary figures and the before and after comparison per community.
- Drawing the closed units and the alternate roads on the map.

Non-goals:

- Rank, criticality or any figure of `scenarios.json`: the pipeline's. The browser never recomputes the ranking.
- The map and the selected unit: `map-corridor`. The "Simular cierre" button: `segment-detail`.
- The exact detour path of each community: not computed; alternate roads are highlighted by name only.
- Closing parts of a unit or edges: the unit is the smallest closure.

## Contract

Reads `graph.json` and `scenarios.json` (the baseline and the units' `edge_ids` and `alternates`) of the active zone.

| Topic | Behavior |
|---|---|
| Closed set | Unit ids, without duplicates and without order. The closed edges are the union of their `edge_ids`. |
| Computation | The fastest route from each community's node to a referral hospital's node, following `oneway` edges only `from → to`, with cost the sum of `time_s`; one search from all hospitals over reversed edges. A tie between hospitals goes to the lowest hospital number. |
| Affected | A community that had a baseline route and, with the closure, is without a route or has extra time above 0. A community with no baseline route is never affected. |
| Summary | Extra time: the largest extra time among affected communities that keep a route (none if there are none); the number of communities without a route; the affected population (sum of known populations, "sin dato" if none is known). |
| Comparison | Per affected community: time without closures, time with them, extra (durations as approximate durations, `trust-signals`), hospital reached; "sin ruta al hospital de referencia" when there is no route. |
| Map | Closed units drawn in a distinct style; edges whose `road` equals the name of any alternate of a closed unit highlighted and labeled "rutas alternas". |
| Chips | One per closed unit, with its label and a remove control, plus "Restablecer". |

## Invariants

- INV-01 [test: bun test --cwd projects/frontend]
  When no edge is closed, `computeAccess` returns exactly the `baseline` of `scenarios.json`.
- INV-02 [test: bun test --cwd projects/frontend]
  When exactly the edges of one unit are closed, `computeAccess` returns for every community in that unit's `per_community` the same time and hospital as `scenarios.json`.
- INV-03 [test: bun test --cwd projects/frontend]
  When an edge is `oneway`, `computeAccess` follows it only from its `from` node to its `to` node.
- INV-04 [test: bun test --cwd projects/frontend source/graph.test.ts]
  When two referral hospitals are equally near a community, `computeAccess` reports the one with the lowest hospital number.
- INV-06 [test: bun test --cwd projects/frontend source/closureWhatif.test.ts]
  When a community had a baseline route and has none after closing, the simulation lists it as affected and shows "sin ruta al hospital de referencia" for it, and when a community had no baseline route, the simulation never lists it as affected.
- INV-08 [test: bun test --cwd projects/frontend source/closureWhatif.test.ts]
  When units are closed, the summary shows the largest extra time among affected communities that keep a route, the number of communities without a route, and the sum of the known populations of the affected ones, with "sin dato" if none is known.
- INV-09 [test: bun test --cwd projects/frontend source/closureWhatif.test.ts]
  When a unit is closed, the simulation shows one chip for it, when the chip's remove control is used the unit is open again, and when "Restablecer" is pressed nothing is closed, with the results updating each time.
- INV-12 [none]
  When the closed set changes, the map draws the closed units in the closed style and highlights the edges whose `road` equals a name in the `alternates` of any closed unit.
- INV-13 [test: bun test --cwd projects/frontend source/closureWhatif.test.ts]
  When the active zone changes, the closed set is emptied.
- INV-15 [manual]
  When the user changes the closed set on the Ruta 32 real graph, the results update within 300 ms on a mid-range laptop.

## Deferred / Open questions

Testing gaps (`none`, which `builder` turns into `test: bun test --cwd projects/frontend` for the pure rules and leaves `manual` for the interface): INV-04, INV-06, INV-08, INV-09, INV-12, INV-13. INV-01 to INV-03 already run in `source/graph.test.ts` and pass.

- **Rewrite of `computeAccess`:** the current one runs a Dijkstra per community (its own `shortcut:` comment); with the ~758 communities of Ruta 32 it would take seconds. Decided 14 Nov: one search from the hospitals, same API, same tests. S8 measured 230 ms for 50 communities.
- **Performance target:** 300 ms (INV-15) is a proposal, not measured on the real graph; revisit after the first real run.
- **Alternates by name:** only highlights roads named like an alternate; it is not the detour a community would take, and the label says so. Computing real paths is deferred and likely cut at G2.
- **Pipeline parity:** the pipeline's `impact-scoring` uses the same rules; a shared fixture is the contract mock (agree with whoever builds `impact-scoring`). The browser does not compute suspect-isolation marks.
- **Closed set and the URL:** the closed set is not kept in the URL; a reload clears it.
- **Dependencies on the store:** the closed set is a slice of the `map-corridor` store; `segment-detail` calls its add action.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 real data, when a person closes two units, then the summary and the comparison update at once and the closed units and the alternate roads appear on the map.
- ACC-02 [manual]
  Given two closed units, when a person removes one chip and then presses "Restablecer", then the results follow each step and end with nothing closed.
