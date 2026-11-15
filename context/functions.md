# VANTAGE — Functions

> What VANTAGE does, feature by feature. Language note: UI copy is Spanish (the team and users are in Costa Rica); names in code and in this document are English.

## 1. User and main flow

One user type: someone who monitors the route and needs to know which segments matter most for hospital access. No login, no roles.

Flow: open the map → see the critical segments → pick one → read how hospital access changes if it is cut → read its exposure → optionally simulate closing more segments.

> After the spikes (Sat 14 Nov, decision D8 in `STATUS.md`) the product is the consequence (criticality) of each segment, with rain as context. Detection, SME2 and rain did not anticipate closures.

## 2. Web app functions

### F1. Corridor map with optional change layer
- Shows the corridor with the critical segments over the road network, hospitals and communities, with attribution (NASA/JPL, OpenStreetMap) always visible.
- The radar **change layer is optional**: it is hidden when there is no data (empty `change.geojson` or no overlays). The opacity control applies only to overlays that exist. The Before / After toggle was cut (F9).

### F2. Pass selection (cut)
- Cut after G1: it only applies when `meta.json` has `passes`, and there is no radar change layer to explain.

### F3. Critical segments list
- Ordered by **criticality** (consequence): how much hospital access worsens if the segment is cut. Shows only segments with impact > 0, plus a counter "N segments without impact".
- Each row shows rank, segment id, extra time, dependent population and a criticality bar.
- Clicking a row selects the segment on the map.

### F4. Segment detail
On selecting a segment, show:
- **Extra time to the referral hospital** and **population that depends on the segment** (the headline metrics).
- **Affected communities** and **alternate routes** (for example Ruta 126, light vehicles only; Ruta 10, freight).
- A block **Exposure**: accumulated rainfall (`rain_mm_12d`) only; soil moisture and radar evidence were removed from the contract in 0.3 (S2c failed; the radar finding is in `meta.json → detection_limits`). The value handles `null`.
- The mean backscatter change (ΔdB) only if the zone has one.
- A label saying it is a critical segment by consequence, not a confirmed closure.
- Two actions: "Simulate closure of this segment" and "Why?".

### F5. Closure simulation
- The user closes one or more segments and the results update instantly, with no server.
- Closed segments appear as chips that can be removed individually, plus a **Reset** action.
- Summary figures: total extra time, number of isolated communities, affected population.
- Per-community comparison: time without closures versus with closures.
- A community is marked **isolated** only when it has no path to any referral hospital; the UI says "sin ruta al hospital de referencia", not "aislada". Alternate routes are highlighted on the map.

### F6. "Why?" panel (exposure context)
- Daily rainfall chart for the period, with the pass dates marked when passes exist.
- A short list of hypotheses explaining the **exposure**: rain accumulated; slope and soil of the segment.
- State plainly that in our test the 12-day rain exceeded its baseline before only 3 of 8 closures.
- Always labeled **"Hypothesis, not confirmed cause"**.

### F7. Responsive behavior
- Desktop: a side panel (list and controls), the map filling the rest, and a floating detail card.
- Mobile: map on top, a bottom sheet with the selected segment, and tabs for Segments / Simulation / Why?. Touch targets are at least 44 px.

### F8. Global UI rules
- A visible notice: "critical segments by consequence; they are not confirmed landslides". Radar does not confirm closures.
- Attribution footer: NISAR GCOV (NASA/JPL), IMERG Late, © OpenStreetMap contributors (ODbL).
- Accessibility: real buttons and inputs, visible keyboard focus, contrast of at least 4.5:1, labeled map controls.

## 3. Analysis functions (offline)

| # | Function | What it does |
|---|---|---|
| P1 | Acquire NISAR data | **Discarded as generator of candidates** (G1). The spike code was removed from the repo (it was never versioned); rebuild it for SME2 or the optional layer: two compatible passes (same track, direction, CRID; outside the Jul 27 – Aug 10 gap), corridor only. |
| P2 | Detect change | **Experimental / discarded as a generator of candidates.** ΔdB between two passes; negative at landslide scale (`approach.md` §5). May output an empty layer. |
| P3 | Build road network | Turn the area's OpenStreetMap roads into segments, with hospitals and communities. The area comes from config. Hospitals are the referral hospitals; communities and hospitals snap to the largest strongly connected component (D8). |
| P4 | Critical segments by consequence | Rank segments by the consequence of cutting them (formerly "find candidate segments that touch a change zone"). Key name `candidates` stays in the files. Built together with P5 (`STATUS.md`). |
| P5 | Compute impact | For each community, find the fastest route to the nearest referral hospital. Remove one segment at a time, closing both carriageways, to get extra time, dependent population and communities left without a path. Rank by criticality. If population is unavailable, fall back to extra time and the count of communities (E4 joins WorldPop so criticality stops being 0). |
| P6 | Add rain context | Fetch daily IMERG rainfall for the period. |
| P7 | Export and validate | Write every result with its version and sources, and check it before use. |
| P9 | Exposure layer | IMERG accumulated rain per segment, as context, not detection. SME2 failed S2c and is not used. Written to `scenarios.json → exposure`. Task E1 in `STATUS.md`. |

## 3b. Note on generalization

Designed for corridors with an OSM road network; Ruta 32 is the demonstration case. Not tested elsewhere. Named limits: variable OSM quality, badly registered hospitals, and the referral-hospital metric (a referral hospital outside the corridor).

## 4. Out of scope

Do not build any of these unless the team decides otherwise:

- Accounts, roles or authentication.
- A backend server or database.
- More than one region at once (the area is a config parameter, but only Ruta 32 is demonstrated).
- Landslide-scar detection as a product feature, and fixed seed data (Lanamme sites, MOPT kilometres, press coordinates).
- Claims of confirmed closures or causes.
- Downloading or storing whole raw NISAR scenes.

## 5. Acceptance checklist

- [ ] The map loads with critical segments, hospitals and communities, locally and deployed; with no change layer it still loads and the layer controls are hidden.
- [ ] The critical segments list is ordered by criticality, shows only impact > 0 with a "N without impact" counter, and selecting a row highlights it on the map.
- [ ] The detail view shows extra time, dependent population, communities, alternate routes and the Exposure block (nulls handled).
- [ ] Closing segments recalculates in the browser; isolated communities appear only when there is truly no path.
- [ ] The "Why?" panel shows exposure with the hypothesis label.
- [ ] Every data file passes validation (schema 0.3).
- [ ] No text says "confirmed" or "caused by"; the notice about critical segments is visible.
- [ ] Attribution is visible (NASA/JPL, IMERG, OpenStreetMap).
- [ ] The app works on a phone, in a private browser window and offline.
- [ ] The analysis area comes from config, not from code.
