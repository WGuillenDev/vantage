# VANTAGE — Functions

> What VANTAGE does, feature by feature. Language note: UI copy is Spanish (the team and users are in Costa Rica); names in code and in this document are English.

## 1. User and main flow

One user type: someone who monitors the route and needs to know which segments matter most for hospital access. No login, no roles.

Flow: open the map → see where the surface changed → pick a segment → read how hospital access changes if it is cut → optionally simulate closing more segments → check rainfall context.

## 2. Web app functions

### F1. Corridor map with change layer
- Shows the Ruta 32 corridor with the detected change drawn over the road network.
- An **opacity control** compares before and after; a layer switch offers Change / Before / After.
- Shows hospitals and communities, with attribution (NASA/JPL, OpenStreetMap) always visible.

### F2. Pass selection
- Shows which two NISAR passes are being compared (before and after dates).

### F3. Candidate segments list
- Ordered by **criticality**: how much hospital access worsens if the segment is cut.
- Each row shows rank, segment id, extra time, dependent population and a criticality bar.
- Clicking a row selects the segment on the map.

### F4. Segment detail
On selecting a segment, show:
- **Extra time to hospital** and **population that depends on the segment** (the headline metrics).
- **Affected communities**.
- **Alternate routes** (for example Ruta 126, light vehicles only; Ruta 10, freight).
- The mean backscatter change (ΔdB) of the zone.
- A label saying it is a **candidate**, not a confirmed closure.
- Two actions: "Simulate closure of this segment" and "Why did it change?".

### F5. Closure simulation
- The user closes one or more segments and the results update instantly, with no server.
- Closed segments appear as chips that can be removed individually, plus a **Reset** action.
- Summary figures: total extra time, number of isolated communities, affected population.
- Per-community comparison: time without closures versus with closures.
- A community is marked **isolated** only when it has no path to any hospital. Alternate routes are highlighted on the map.

### F6. "Why?" panel (rain context)
- Daily rainfall chart for the period between the two passes, with both pass dates marked.
- A short list of hypotheses: rain accumulated between passes; slope and soil of the segment; soil moisture also changes the radar return.
- Always labeled **"Hypothesis, not confirmed cause"**.

### F7. Responsive behavior
- Desktop: a side panel (list and controls), the map filling the rest, and a floating detail card.
- Mobile: map on top, a bottom sheet with the selected segment, and tabs for Segments / Simulation / Why?. Touch targets are at least 44 px.

### F8. Global UI rules
- A visible notice that candidates must be verified and that radar does not confirm closures.
- Attribution footer: NISAR GCOV (NASA/JPL), IMERG Late, © OpenStreetMap contributors (ODbL).
- Accessibility: real buttons and inputs, visible keyboard focus, contrast of at least 4.5:1, labeled map controls.

## 3. Analysis functions (offline)

| # | Function | What it does |
|---|---|---|
| P1 | Acquire NISAR data | Select **two compatible passes**: same track, direction and processing version; outside the Jul 27 – Aug 10 gap; enclosing a real closure event. Use only the corridor area. |
| P2 | Detect change | Compare the two passes in dB, discard noise, water, shadow and very small blobs, and produce change zones plus a map image. |
| P3 | Build road network | Turn the corridor's OpenStreetMap roads into segments, with hospitals and communities. |
| P4 | Find candidate segments | Pick segments that touch a change zone, with a margin. |
| P5 | Compute impact | For each community, find the fastest route to the nearest hospital. Remove one candidate at a time to get extra time, dependent population and communities left without a path. Rank by criticality. If population is unavailable, fall back to extra time and the count of communities. |
| P6 | Add rain context | Fetch daily rainfall for the period. |
| P7 | Export and validate | Write every result with its version and sources, and check it before use. |

## 4. Out of scope

Do not build any of these unless the team decides otherwise:

- Accounts, roles or authentication.
- A backend server or database.
- Regions beyond the Ruta 32 corridor.
- Claims of confirmed closures or causes.
- Downloading or storing whole raw NISAR scenes.

## 5. Acceptance checklist

- [ ] The map loads with the change layer and opacity control, locally and deployed.
- [ ] The candidate list is ordered by criticality and selecting a row highlights it on the map.
- [ ] The detail view shows extra time, dependent population, communities and alternate routes.
- [ ] Closing segments recalculates in the browser; isolated communities appear only when there is truly no path.
- [ ] The "Why?" panel shows rain with the hypothesis label.
- [ ] Every data file passes validation.
- [ ] Attribution is visible (NASA/JPL, IMERG, OpenStreetMap).
- [ ] The app works on a phone, in a private browser window and offline.
