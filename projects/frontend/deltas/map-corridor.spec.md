---
slice: map-corridor
---

# map-corridor: spec

> Loads a zone's files and draws its closure units, hospitals and communities on the map, with unit selection (task F1).

## Intent

The user monitors a corridor and needs to see, at a glance, which stretches matter most for access to a referral hospital. This slice is the base the other web slices stand on: it loads the zone's data, owns the map and the selected-unit state, and draws the units colored by criticality. It replaces the current skeleton, which loads one fixed `meta.json`, fails when `overlays` is absent and says "Señal de cambio candidata", wording the project forbids (D6).

## Scope

Owns:

- Loading `areas.json` and the files of the active zone (`meta.json`, `graph.json`, `scenarios.json`), and choosing the active zone.
- The base map, the corridor units, the referral hospitals and the communities.
- The shared state of the app: active zone and selected unit (Zustand store, as planned in `structure.md`).
- The criticality color legend, and the loading and error states.

Non-goals:

- The ranked list: `segment-ranking`. The detail card and the exposure block: `segment-detail`. Closing several units: `closure-whatif`.
- The zone control: `zone-picker`. This slice only reads the active zone from the URL and exposes a way to change it.
- The radar change layer: nothing produces one (purged 14 Nov), so the map never draws overlays even if `meta.json` lists them.
- The footer, the attributions and the "no son derrumbes confirmados" notice: `trust-signals`. The map's own tile attribution stays.
- Responsive layout: `mobile-layout`.
- Computing anything: every figure comes from the files.

## Contract

Reads, from `${BASE_URL}storage/`: `areas.json`, then `<id>/meta.json`, `<id>/graph.json` and `<id>/scenarios.json`, all at `schema_version` `"0.3"`.

| Topic | Behavior |
|---|---|
| Active zone | The `area` query parameter if it names a zone of `areas.json`; otherwise the first zone with `validated: true`; otherwise the first zone. |
| Units | The edges of `graph.json` grouped by `candidate_id` and drawn from their `geometry`, which includes both carriageways. Edges with `candidate_id: null` are not drawn. |
| Color | Units with at least one affected community are colored by `criticality` on a sequential scale with a legend; units without one are gray. |
| Hospitals, communities | Points at the coordinates of their nodes in `graph.json`. |
| Selection | A click on a unit selects it in the store and highlights it; a click elsewhere clears it. |
| Copy | All user-facing text in Spanish: "tramo crítico", never "candidato" or "causado por", and "confirmado" only in "no son derrumbes confirmados". |

## Invariants

- INV-01 [none]
  When the page opens with `?area=<id>` and `areas.json` lists that id, the map loads that zone.
- INV-02 [none]
  When the page opens without a valid `area`, the map loads the first zone with `validated: true`, or the first zone if none is validated.
- INV-04 [none]
  When a zone is drawn, every edge whose `candidate_id` is a unit of `scenarios.json` is drawn in that unit's style, so both carriageways of a unit are shown.
- INV-06 [none]
  When a unit has no affected community, the map draws it gray, and otherwise draws it with a color that is monotone in its `criticality`.
- INV-07 [none]
  When the map is drawn, the legend shows the lowest and highest `criticality` of the zone and the gray "sin impacto" entry.
- INV-08 [none]
  When a zone is drawn, the hospitals and communities shown are exactly those of `graph.json`, at their nodes' coordinates.
- INV-09 [none]
  When the user clicks a unit, the store's selected unit becomes that unit and it is highlighted, and when the user clicks the map elsewhere, the selection is cleared.
- INV-11 [none]
  When the active zone changes in the store, the map removes the previous zone's layers, clears the selected unit and loads the new zone's files.
- INV-12 [none]
  If a data file cannot be loaded or its `schema_version` is not `"0.3"`, then the map shows a Spanish message that names the file and does not render a blank map.
- INV-14 [none]
  When a zone is loaded, the map fits the zone's `bbox`.
- INV-15 [none]
  When the app renders any text, it contains none of the words "candidato", "causado por" or "funciona en cualquier lugar", and "confirmado" appears only in the phrase "no son derrumbes confirmados" or "no es un derrumbe confirmado".

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns the pure ones, as zone choice, grouping and color scale, into `test: bun test` files under `projects/frontend/source/` and leaves the drawing ones `manual`): INV-01, INV-02, INV-04, INV-06, INV-07, INV-08, INV-09, INV-11, INV-12, INV-14, INV-15.

- **Dependencies:** `zustand` is not installed yet (it is in `structure.md`), and `recharts` is for `segment-detail`. No component test library is set up either.
- **Tile server:** the base map uses the public OpenStreetMap tile server, meant for light use; fine for the demo, not for heavy traffic.
- **Color scale:** the sequential palette must be readable for color-blind users and keep contrast on the base map; chosen at build time and checked in `trust-signals`' accessibility review.
- **Skeleton to replace:** `source/App.tsx` (fixed `meta.json`, `overlays.find`, old wording) is replaced by this slice; `graph.ts` and its test stay.
- **Large zones:** only unit edges are drawn, not the whole network, so zone size should not slow the map; unmeasured on a second zone.
- **Both carriageways coincide visually** at low zoom; accepted.
- **Contract 0.3 and mocks:** the app is built against the 0.3 mock set from `contract-update`.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 real data, when a person opens the app, then the map shows the units colored by criticality, the referral hospitals and the communities, with no console errors.
- ACC-02 [manual]
  Given the map is loaded, when a person clicks a unit, then both carriageways of that unit are highlighted and the others are not.
