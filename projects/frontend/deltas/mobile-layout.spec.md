---
slice: mobile-layout
---

# mobile-layout: spec

> Arranges the app as a side panel on wide screens and as a map with a bottom sheet on phones (task F7).

## Intent

The people who monitor a route are often on a phone, on the road. The same list, detail, simulation and explanation have to be usable there, without a second app. This slice decides where each piece goes at each width, and nothing else.

## Scope

Owns:

- The breakpoint and the two arrangements of the panels.
- The side panel with tabs on wide screens, and the bottom sheet with tabs on narrow ones.
- Touch-target size and the absence of horizontal page scroll.
- Where the notice and attributions stay reachable.

Non-goals:

- The content of any panel: `segment-ranking`, `segment-detail`, `closure-whatif`, `trust-signals`.
- The map: `map-corridor`.
- Drag gestures on the sheet: decided against (see Deferred).
- A native app or an offline mode.

## Contract

| Topic | Behavior |
|---|---|
| Breakpoint | 768 px (Tailwind `md`). |
| Wide (≥ 768 px) | A side panel on the left with the tabs "Tramos" and "Simulación"; the map fills the rest; the detail card and the "¿Por qué?" panel float over the map. |
| Narrow (< 768 px) | The map on top; a bottom sheet with the tabs "Tramos", "Simulación" and "¿Por qué?". |
| Sheet | Two states, collapsed and expanded, switched by activating its handle (a button with `aria-expanded`). Expanded, it leaves at least 30 % of the viewport height to the map. |
| Selection on narrow | Selecting a unit expands the sheet to show its detail. |
| Touch targets | At least 44 × 44 CSS px for every button, tab and chip on narrow screens. |
| Always reachable | The notice is always visible; the attributions are visible or one tap away at every width. |

## Invariants

- INV-01 [manual]
  When the viewport is 768 px wide or more, the app shows a side panel with the tabs "Tramos" and "Simulación" and the map fills the rest.
- INV-02 [manual]
  When the viewport is under 768 px wide, the app shows the map above a bottom sheet with the tabs "Tramos", "Simulación" and "¿Por qué?".
- INV-03 [manual]
  When the user activates the sheet's handle, the sheet switches between collapsed and expanded and the handle's `aria-expanded` follows it.
- INV-05 [manual]
  When a unit is selected on a narrow screen, the sheet expands and shows the unit's detail.
- INV-06 [manual]
  When the viewport is under 768 px wide, every button, tab and chip has a touch target of at least 44 × 44 CSS px.
- INV-07 [manual]
  When the viewport is 360 px wide, the page has no horizontal scroll.
- INV-09 [manual]
  When the app renders at any width, the notice is visible and the attributions are visible or one tap away.

## Deferred / Open questions

No claim is automated: layout is checked by a person in a browser at 360 px and 1280 px wide and on a real phone, as G3 asks (`STATUS.md` X2). There are no `none` claims; every one is `manual`.

- **Drag gestures:** the sheet has two fixed states, switched by a button (decided 14 Nov). A draggable sheet is more natural on a phone but costs code and is harder with keyboard and screen readers.
- **Landscape phones:** under 768 px high the expanded sheet may cover most of the map; the 30 % rule applies but is not tuned.
- **Tablet range:** 768 px and up uses the side panel; a narrow tablet in portrait may feel cramped.
- **Tab content on wide screens:** "¿Por qué?" opens in the floating card there, not as a tab; two ways to reach the same panel.
- **Dependencies:** needs the panels of the other slices to exist; if `closure-whatif` is cut, the "Simulación" tab disappears.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 real data on a real phone, when a person selects a unit from the list, then the sheet expands with its detail, the map stays usable above it and all controls can be pressed without zooming.
- ACC-02 [manual]
  Given the app at 1280 px and at 360 px wide in a browser, when a person uses the list, the detail and the simulation, then every function works at both widths.
