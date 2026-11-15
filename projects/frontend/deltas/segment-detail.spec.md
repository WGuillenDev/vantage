---
slice: segment-detail
---

# segment-detail: spec

> Shows what happens if the selected unit is cut, and the rain context behind it, in a detail card and a "¿Por qué?" panel (tasks F4 and F6).

## Intent

Once a user picks a stretch, they need the consequence in plain terms: how much longer the trip to the referral hospital becomes, how many people depend on the stretch, which communities are affected and which alternate roads exist. Next to it, the rain context, always as a hypothesis: the tests showed that recent rain did not anticipate closures (S5), so the interface must show it without implying a cause. Both belong together because they read the same unit and are opened from the same place.

## Scope

Owns:

- The detail card of the selected unit: headline figures, affected communities, alternate routes and the "Exposición" block.
- The "¿Por qué?" panel: the daily rain chart with the 12-day window, and the fixed hypothesis text.
- The action that adds the unit to the closure simulation.

Non-goals:

- Computing figures: all come from `scenarios.json`, `graph.json` and `rain.csv`.
- The ranked list: `segment-ranking`. The simulation itself: `closure-whatif`. The map: `map-corridor`.
- The global notice and the attribution footer: `trust-signals`. Suspect-isolation marks: `trust-signals`.
- Soil moisture (removed from the contract in 0.3) and slope or soil of the stretch: there is no data for them, so nothing is shown or implied.
- Any claim that rain causes, predicts or precedes closures.

## Contract

Reads `scenarios.json`, `graph.json` and `rain.csv` of the active zone and the selected unit of the `map-corridor` store.

| Block | Content |
|---|---|
| Header | The unit's label (as in `segment-ranking`), and its rank. |
| Headline | Extra time and dependent population, formatted as in `segment-ranking` (approximate durations and estimated population, `trust-signals`); every duration in this card follows the same rule. |
| Affected communities | Isolated ones first, then by extra time descending, then by id. Each: name, time without closing, time with the closure, extra time, and the hospital reached by name. |
| Isolated | "sin ruta al hospital de referencia", never "aislada". |
| Alternates | The unit's `alternates`, with "livianos" or "pesados"; "sin alternas registradas" when empty. |
| Exposición | `rain_mm_12d` as "N mm en 12 días" or "sin dato"; always the label "Hipótesis, no causa confirmada". |
| Actions | "Simular cierre de este tramo" and "¿Por qué?". |
| "¿Por qué?" | A chart of `rain.csv` for the whole period with the 12 days ending at `rain.end` highlighted, and the fixed text: recent rain is context and not a prediction, and it was not tested as a signal of closures in this zone. Always labeled "Hipótesis, no causa confirmada". No numbers about past tests. |

## Invariants

- INV-01 [none]
  When a unit is selected, the card shows its extra time and dependent population from `scenarios.json`, with "sin ruta al hospital de referencia" for a `null` extra time and "sin dato" for a `null` population.
- INV-02 [none]
  When the card lists affected communities, they are exactly the unit's `affected_community_ids`, with isolated ones first, then extra time descending, then id, each showing the name of the hospital it reaches from `graph.json` or "sin ruta al hospital de referencia" (never the word "aislada") when it has no route.
- INV-05 [none]
  When a unit has no alternates, the card shows "sin alternas registradas", and otherwise each alternate with "livianos" or "pesados".
- INV-06 [none]
  When `rain_mm_12d` is `null`, the Exposición block shows "sin dato" and never 0.
- INV-08 [none]
  When the Exposición block is visible, the label "Hipótesis, no causa confirmada" is visible with it.
- INV-11 [none]
  When the "¿Por qué?" panel opens, it shows the `rain.csv` chart for the whole period with the 12 days ending at `rain.end` highlighted, and the fixed hypothesis text with the label "Hipótesis, no causa confirmada".
- INV-12 [none]
  If `rain.csv` cannot be loaded, then the panel shows a Spanish message naming the file and the card still works.
- INV-13 [none]
  When the user presses "Simular cierre de este tramo", the unit is added to the closed set of the simulation.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns the formatting rules into `test: bun test --cwd projects/frontend` files and leaves rendering `manual`): INV-01, INV-02, INV-05, INV-06, INV-08, INV-11, INV-12, INV-13.

- **Dependencies:** `recharts` is not installed; the chart needs it (`structure.md`).
- **Simulation action:** the closed set belongs to `closure-whatif`; if that slice is cut at G2, the action "Simular cierre de este tramo" is removed and INV-13 with it.
- **No past-test numbers in the interface:** the S5 finding (3 of 8 closures above the 75th percentile) is specific to Ruta 32, so the panel says only that rain was not tested as a signal here; the number goes in the presentation and README (decided 14 Nov).
- **Original F6 text:** `functions.md` F6 mentions "slope and soil of the segment" as hypotheses; there is no data for them, so they are not shown. A person updates the doc.
- **Rain scale:** 10 km cells mean neighbouring units show the same rain; the block says it is context.
- **Mock fixture:** the contract mock still has `soil_moisture_pctl`; `contract-update` removes it, and the card ignores it either way.
- **Communities without names:** an OSM place always has a name here (`road-graph`), so no fallback label is needed.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 real data, when a person selects a unit, then the card shows the figures of that unit in `scenarios.json` and the Exposición block carries the hypothesis label.
- ACC-02 [manual]
  Given a selected unit, when a person opens "¿Por qué?", then the chart covers the zone's rain period with the last 12 days highlighted and no sentence says or implies that rain caused or predicted closures.
