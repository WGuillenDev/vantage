---
slice: trust-signals
---

# trust-signals: spec

> Makes the interface say what the numbers are and are not: notice, attributions, unvalidated-zone banner, suspect marks, approximate times and estimated population (tasks F8 and F10).

## Intent

Everything on screen is a model result: travel times from constant speeds, population from a modelled raster, "isolated" communities that sometimes are artifacts, and in a zone nobody reviewed it may be wrong in ways nobody has seen. The project's hard rule is never to overclaim. This slice puts that rule in the interface, in one place, so a reader cannot take a critical segment for a confirmed landslide, a time for a measurement, or an unreviewed zone for a validated one.

## Scope

Owns:

- The permanent notice and the attribution footer.
- The banner shown for a zone that is not validated.
- The "Cómo leer estos números" panel.
- The marks for suspect isolations in the detail card, and the note in the simulation.
- The shared rules for showing a duration (approximate) and a population (estimated).

Non-goals:

- Computing which isolations are suspect: `impact-scoring`. This slice only shows them.
- The detail card, the list and the simulation themselves: `segment-detail`, `segment-ranking`, `closure-whatif`; this slice supplies the formatting rules they apply.
- The zone control: `zone-picker`. The banner does not depend on it.
- Layout on small screens: `mobile-layout`.
- Writing the attribution strings: `pipeline-run` (`meta.json → attributions`).

## Contract

Reads `meta.json` and `areas.json` of the active zone, and `scenarios.json` for the suspect marks.

| Element | Behavior |
|---|---|
| Notice | Always visible: "Tramos críticos por consecuencia; no son derrumbes confirmados." |
| Footer | One line per string of `meta.attributions`, inside the footer's collapsible panel "Cómo leer estos números y fuentes". |
| Banner | "Zona no validada: sus resultados no se han revisado." while the active zone has `validated: false`. Always visible from 768 px; below that, a "No validada" chip (with the full text as its label) opens it. |
| "Cómo leer estos números" | A panel with: times use one constant speed per road class (the table from `meta.speed_model_kmh`), the referral hospitals (the names in `graph.json → hospitals`), the radar finding (`meta.detection_limits.note`) when the zone has one, "sin ruta al hospital de referencia" means no route to them, population is a modelled estimate, and OpenStreetMap quality varies. |
| Suspect mark | In the detail card, a community in `suspect_isolated_community_ids` shows "sin ruta al hospital de referencia (posible artefacto del modelo)". |
| Simulation note | While the simulation shows a community without a route: "Las comunidades sin ruta pueden incluir artefactos del modelo." |
| Approximate duration | `m` = seconds / 60. Under 5 minutes: "< 5 min". Otherwise round `m` half up to a multiple of 5 and show "≈ N min" under 60, "≈ H h" or "≈ H h M min" from 60. Used for every duration in the app. |
| Population | Every population figure is labeled "estimada" (a modelled estimate), with `null` shown as "sin dato". |

## Invariants

- INV-01 [none]
  When the app is visible, the notice "Tramos críticos por consecuencia; no son derrumbes confirmados." is visible.
- INV-02 [test: bun test --cwd projects/frontend source/trustSignals.test.ts]
  When the footer renders, it shows every string of `meta.attributions` of the active zone.
- INV-03 [test: bun test --cwd projects/frontend source/trustSignals.test.ts]
  While the active zone has `validated: false`, the banner "Zona no validada: sus resultados no se han revisado." is visible, and while it has `validated: true`, the banner is not shown.
- INV-04 [test: bun test --cwd projects/frontend source/trustSignals.test.ts]
  When the "Cómo leer estos números" panel opens, it shows the speed per road class from `meta.speed_model_kmh` and the referral hospital names from `graph.json`, and the radar note only when `meta.detection_limits` exists.
- INV-05 [test: bun test --cwd projects/frontend source/trustSignals.test.ts]
  When the detail card lists an isolated community that is in `suspect_isolated_community_ids`, it adds "posible artefacto del modelo" to it, and it adds nothing to an isolated community that is not.
- INV-06 [test: bun test --cwd projects/frontend source/trustSignals.test.ts]
  While the simulation shows at least one community without a route, it shows the note that such communities may include model artifacts.
- INV-07 [test: bun test --cwd projects/frontend source/format.test.ts]
  When a duration under 300 seconds is shown, it reads "< 5 min".
- INV-08 [test: bun test --cwd projects/frontend source/format.test.ts]
  When a duration of 300 seconds or more is shown, it is rounded half up to a multiple of 5 minutes and prefixed with "≈", as "≈ N min" under 60 minutes and "≈ H h" or "≈ H h M min" from 60.
- INV-09 [test: bun test --cwd projects/frontend source/format.test.ts]
  When a population figure is shown, it is labeled "estimada", and a `null` population is shown as "sin dato".
- INV-10 [manual]
  When text is shown on the map panels, its contrast against its background is at least 4.5:1. (axe-core 4.10, wcag2a/2aa and best-practice, 15 Nov: no violations at 390 and 1280 px; a person still checks it on a real phone.)
- INV-11 [manual]
  When the user moves through the interface with the keyboard, every button, tab and control has a visible focus and an accessible label.

## Deferred / Open questions

Testing gaps (`none`; `builder` turns the formatting rules, INV-07 to INV-09, into `test: bun test --cwd projects/frontend` and leaves the rendering ones `manual`): INV-01 to INV-09.

- **Earlier specs updated with this one (decided 14 Nov):** `segment-ranking` and `segment-detail` showed minutes rounded to the minute; they now use the approximate-duration rule here, so a single function formats every duration.
- **No measured uncertainty:** "≈" with 5-minute steps signals order of magnitude without inventing an error range. When `time-crosscheck` reports its median error, a range could replace it; not decided.
- **Suspect marks only on one unit:** the browser does not compute suspect marks for a simulation of several units, so the simulation carries a general note instead (decided with `closure-whatif`).
- **Wording of the notice:** `map-corridor` INV-15 already allows "confirmado" only inside "no son derrumbes confirmados".
- **NISAR credit:** shown only if the zone's attributions include it; with no radar layer it does not appear, so the app never names NISAR as a source of what it shows.
- **Zone label:** `zone-picker` repeats the "no validada" label in its list; if it is cut, the banner still covers it.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 real data, when a person opens the app, then the notice and the attribution footer with the OpenStreetMap credit are visible, and "Cómo leer estos números" lists the speeds and the referral hospitals.
- ACC-02 [manual]
  Given a zone with `validated: false` opened with `?area=<id>` and no zone control, when a person opens the app, then the unvalidated-zone banner is visible.
