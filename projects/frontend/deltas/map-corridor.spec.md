---
slice: map-corridor
---

# map-corridor: spec

> Loads a zone's files and draws its closure units, hospitals and communities on the map, with unit selection (task F1).

## Intent

The user monitors a corridor and needs to see, at a glance, which stretches matter most for access to a referral hospital. This slice is the base the other web slices stand on: it loads the zone's data, owns the map and the selected-unit state, and draws the units colored by criticality. It replaced the first skeleton, which loaded one fixed `meta.json`, failed when `overlays` was absent and said "Señal de cambio candidata", wording the project forbids (D6).

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
| Valid data | `areas.json` carries `areas`; `graph.json` carries `nodes`, `edges`, `hospitals` and `communities`; `scenarios.json` carries `candidates`; each is a list. An edge is an object with `id` and `candidate_id` (a string or `null`), plus a `geometry` of at least two `[lon, lat]` positions when `candidate_id` is a string. A unit has an `id`, a numeric `criticality` and an `affected_community_ids` list. A hospital or community has an `id`, a `name` and a `node` that `graph.json` lists. `meta.json` is only checked for its version. |
| Units | The edges of `graph.json` grouped by `candidate_id` and drawn from their `geometry`, which includes both carriageways. Edges with `candidate_id: null` are not drawn. |
| Color | Units with at least one affected community are colored by `criticality` on a sequential scale with a legend; units without one are gray. The scale runs from the lowest to the highest `criticality` among the units that have an affected community. |
| Hospitals, communities | Points at the coordinates of their nodes in `graph.json`. |
| Selection | A click on a unit selects it in the store and highlights it; a click elsewhere clears it. |
| Hover and focus | The pointer over a hospital or a community shows its name. The pointer over a unit shows its label and extra time in a tooltip and highlights it; the same highlight follows a hovered list row. Selecting a unit that is out of view moves the map to it. |
| Base map | The OpenStreetMap raster is desaturated so the criticality colors stand out; the legend collapses to a button and starts collapsed on narrow screens. |
| Copy | All user-facing text in Spanish: "tramo crítico", never "candidato" or "causado por", and "confirmado" only in "no son derrumbes confirmados". |

## Invariants

- INV-01 [test: bun test --cwd projects/frontend source/mapCorridor]
  When the page opens with `?area=<id>` and `areas.json` lists that id, the map loads that zone.
- INV-02 [test: bun test --cwd projects/frontend source/mapCorridor]
  When the page opens without a valid `area`, the map loads the first zone with `validated: true`, or the first zone if none is validated.
- INV-04 [test: bun test --cwd projects/frontend source/mapCorridor]
  When a zone is drawn, every edge whose `candidate_id` is a unit of `scenarios.json` is drawn in that unit's style, so both carriageways of a unit are shown.
- INV-06 [test: bun test --cwd projects/frontend source/mapCorridor]
  When a unit has no affected community, the map draws it gray, and otherwise draws it with a color that is monotone in its `criticality`.
- INV-07 [test: bun test --cwd projects/frontend source/mapCorridor]
  When the map is drawn, the legend shows the lowest and highest `criticality` among the zone's units that have an affected community, and the gray "sin impacto" entry.
- INV-08 [test: bun test --cwd projects/frontend source/mapCorridor]
  When a zone is drawn, the hospitals and communities shown are exactly those of `graph.json`, at their nodes' coordinates.
- INV-09 [test: bun test --cwd projects/frontend source/mapCorridor]
  When a unit is selected, the store's selected unit becomes that unit, and when the selection is cleared it becomes `null`.
- INV-11 [test: bun test --cwd projects/frontend source/mapCorridor]
  When the active zone changes in the store, the store's selected unit is cleared.
- INV-12 [test: bun test --cwd projects/frontend source/mapCorridor]
  If a data file cannot be loaded, is not valid JSON, lacks a list it must carry or has a `schema_version` other than `"0.3"`, then the map shows a Spanish message that names the file and does not render a blank map.
- INV-14 [manual]
  When a zone is loaded, the map fits the zone's `bbox`.
- INV-15 [test: bun test --cwd projects/frontend source/mapCorridor]
  When the app renders any text, it contains none of the words "candidato", "causado por" or "funciona en cualquier lugar", and "confirmado" appears only in the phrase "no son derrumbes confirmados" or "no es un derrumbe confirmado".
- INV-16 [test: bun test --cwd projects/frontend source/mapCorridor]
  If every unit with an affected community has `criticality` 0, then the legend says in Spanish that the color does not rank the units because the population is unknown.
- INV-17 [test: bun test --cwd projects/frontend source/mapCorridor]
  If a data file has a malformed element in a list it must carry, as defined under Valid data, then the map shows a Spanish message that names the file and does not render a blank map.
- INV-18 [test: bun test --cwd projects/frontend source/mapCorridor]
  If a hospital or community of `graph.json` references a node that `graph.json` does not list, then the map shows a Spanish message that names `graph.json` and does not draw a partial zone.
- INV-19 [manual]
  When the user clicks a unit on the map, the map selects and highlights that unit, and when the user clicks the map elsewhere, the selection and the highlight are cleared.
- INV-20 [manual]
  When the active zone changes in the store, the map removes the previous zone's layers and loads the new zone's files.

## Deferred / Open questions

Testing gaps (`none`): INV-07, INV-16, INV-17, INV-18. `builder` writes their tests and retags them. INV-07's old test measures the range over all units and must change with the claim.

Drawing claims verified by hand, as no component test library is set up: INV-14, INV-19, INV-20, ACC-01, ACC-02.

- **Test command:** the tags run every test file of the slice (`source/mapCorridor` matches the plain, the adversarial and the mock-set test files), so a claim covered by an adversarial test is not tagged to a file that lacks it.
- **Tile server:** the base map uses the public OpenStreetMap tile server, meant for light use; fine for the demo, not for heavy traffic.
- **Color scale:** a viridis-like ramp, yellow for the lowest and dark purple for the highest criticality, so the most critical units keep contrast on the light base map. Its accessibility is checked in `trust-signals`' review.
- **`meta.json` shape:** only its version is validated, because this slice reads none of its fields; `trust-signals` declares which it needs.
- **Large zones:** only unit edges are drawn, not the whole network, so zone size should not slow the map; unmeasured on a second zone.
- **Both carriageways coincide visually** at low zoom; accepted.
- **Contract 0.3 and mocks:** the app is built against the 0.3 mock set from `contract-update`.
- **Selecting the zone already active** also clears the selected unit; accepted, as the picker only offers a change.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 real data, when a person opens the app, then the map shows the units colored by criticality, the referral hospitals and the communities, with no console errors.
- ACC-02 [manual]
  Given the map is loaded, when a person clicks a unit, then both carriageways of that unit are highlighted and the others are not.
