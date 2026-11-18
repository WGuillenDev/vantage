---
slice: zone-picker
---

# zone-picker: spec

> Lets the user switch between the zones listed in `areas.json`, labeling the ones that are not validated (task F11).

## Intent

The app is built to show more than one corridor (Ruta 32 is the demonstration case and the only validated one). The user needs to move between zones without editing a URL. Because a zone nobody reviewed must never look like a reviewed one, the control carries that label too. The slice is deliberately small and cuttable: without it, every zone is still reachable by `?area=<id>`.

## Scope

Owns:

- The zone control in the header and the label of zones that are not validated.
- Writing the chosen zone to the store and to the URL.

Non-goals:

- Loading and drawing a zone: `map-corridor`, which reloads when the active zone changes in the store.
- The banner for an unvalidated zone: `trust-signals`; it does not depend on this control.
- Preparing a second zone's data: `area-config` and `pipeline-run`. No second zone is chosen here.
- Remembering the last zone between visits.

## Contract

Reads `areas.json` (`id`, `name`, `validated` per zone) and the active zone from the store.

| Topic | Behavior |
|---|---|
| Two or more zones | A native select labeled "Zona", listing every zone of `areas.json` in file order, with the active one selected. |
| One zone | Its name as plain text, with no control. |
| Label | A zone with `validated: false` is listed as "<name> (unvalidated)". |
| Change | Sets the active zone in the store and updates `?area=<id>` in the URL without adding a history entry. |

## Invariants

- INV-01 [test: bun test --cwd projects/frontend source/zones.test.ts]
  When `areas.json` lists two or more zones, the control lists all of them in file order with the active zone selected.
- INV-02 [test: bun test --cwd projects/frontend source/zones.test.ts]
  When a listed zone has `validated: false`, the control shows its name followed by "(unvalidated)".
- INV-03 [test: bun test --cwd projects/frontend source/zones.test.ts]
  When `areas.json` lists one zone, the header shows its name and no control.
- INV-04 [test: bun test --cwd projects/frontend source/zones.test.ts]
  When the user chooses a zone, the store's active zone becomes that zone and the URL's `area` parameter becomes its id without adding a history entry.

## Deferred / Open questions

Testing gaps (`none`; `builder` turns the list and URL rules into `test: bun test --cwd projects/frontend` and leaves rendering `manual`): INV-01 to INV-04.

- **Cuttable at G2:** if cut, `?area=<id>` still selects a zone (`map-corridor`) and the banner still labels an unvalidated one (`trust-signals`).
- **Second zone:** none is chosen or prepared. The control can be checked only with the two-zone mock set of `contract-update` (ACC-04 there).
- **History:** the URL is replaced, not pushed, so the back button leaves the app; a shared link still opens the chosen zone.
- **Native select:** chosen for accessibility and size; a custom menu with map thumbnails is not planned.

## Acceptance criteria

- ACC-01 [manual]
  Given the two-zone mock set (one validated, one not), when a person chooses the unvalidated zone, then the map shows it, the control reads "(unvalidated)" on it, the unvalidated-zone banner appears and the URL carries its id.
