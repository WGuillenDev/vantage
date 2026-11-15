# VANTAGE — Approach

> Orientation for anyone joining the project, human or agent. Source of truth: the VANTAGE project document (NASA Space Apps 2026). If this text and the work disagree, flag it; do not silently pick one.

## 1. Summary

> **Direction change (G1, Sat 14 Nov 2026, about 16:35 CR time).** Detecting landslide scars with NISAR GCOV was a **NO-GO** (see §5). After the later spikes (S2c, S4′, S5; evening of 14 Nov) the product is redefined by decision D8 in `STATUS.md`: it is the **consequence (criticality)** of each segment, with rain as context. "Risk = consequence × exposure" is no longer used, because no exposure signal was validated. Sections below follow that decision; older text is marked as discarded, not deleted.

VANTAGE answers two questions for a road corridor anywhere there is an OSM road network (designed that way, not tested elsewhere). The demonstration case is the Ruta 32 corridor (Costa Rica):

1. **Who loses the route to the referral hospital if this road segment is cut?** (consequence: road network + hospitals + population, 100 % computed; a closure removes both carriageways.)
2. **What was the recent rain on the corridor?** (exposure: IMERG rainfall, shown as context. We tested whether rain, soil moisture and radar change anticipate closures; none did, §5.)

> Project line: *VANTAGE shows which road segments, if cut, leave communities without a route to the referral hospital, and for how long; recent rain is shown as context, not as a prediction.*

It is our entry for the NASA Space Apps 2026 challenge **"Dancing with the SARs"** (Nov 14–15, 2026): use NISAR radar to detect changes on Earth's surface. Our honest findings are negative: with GCOV at 10 m small landslides are not detectable, SME2 soil moisture does not rise before closures, and 12-day rain exceeds its baseline before only 3 of 8 closures (§5). We present them as results with numbers.

The product has two parts:

1. **Offline analysis.** Road network → impact (consequence) → exposure layer → export. A radar change layer is **optional** and may be empty.
2. **Static web app.** Shows the results on a map and lets the user simulate closing a road segment, with no server.

The two parts are connected only by shared data files. Neither depends on the inner workings of the other.

## 2. Problem

- Ruta 32 (San José–Limón, through Braulio Carrillo) closes during heavy rain because of landslides. Anyone who depends on the affected stretch loses the way to a hospital.
- Closures with a press source (all are press notes that cite the MOPT; no primary MOPT statement was found on `mopt.go.cr` or `conavi.go.cr`, so they are **unverified**): Feb 5–8 and a second episode on the following Saturday night (~Feb 14); Jul 2–4; Jul 17 (8:35–15:03, km 23–24); Aug 17–18; Sep 13 and Sep 18; Oct 5–6; Oct 8 (no reopening reported by Oct 9). The February closures predate any NISAR GCOV data. The list is incomplete: May 31, a June closure at km 32 and a preventive closure from 18:00 on Nov 4 appear in searches and are unverified.
- Discarded as unverified: the July list "8–11, 9, 16–17, 20" that this document carried before, and closures of Jun 21 and Jul 20 that appear in no note. (The Jul 17 closure was discarded by mistake earlier and is back in the list above.)
- Alternate routes are limited: Ruta 126 for light vehicles only, Ruta 10 for freight.

**Why radar, and what we found.** Radar does not depend on light or clouds and NISAR revisits every 12 days. We tested whether subtracting two GCOV passes shows landslide-scale change and it does not (§5). Radar-derived products other than GCOV ΔdB (GUNW coherence, offsets, per-pixel series) remain **untested**, not ruled out.

**The gap we fill.** Whatever the hazard signal, the question "who is left without a route" needs the road network. VANTAGE computes that consequence for every segment, without needing to know in advance where a slope moved.

## 3. Objective and user

Give one kind of user a clear answer: *which road segments matter most for hospital access (critical segments), what happens if one is cut, and how exposed is it?*

- **User:** someone monitoring the route (risk management, emergency response). No accounts or roles: open the page and use it.
- **Headline metric:** extra time to the referral hospital, plus the population that depends on the segment.
- A community is **isolated** only when it has no path to any referral hospital after the segment is removed. It may still have a nearer regional hospital, so the UI says "sin ruta al hospital de referencia", not "aislada".

## 4. Method

The method is deterministic: same data in, same result out. Two questions, no fixed seed sites.

| Step | Question | What happens |
|---|---|---|
| 1 | What is the road network and who depends on it? | Split the area's OSM roads into segments, with hospitals and communities, and attach population (WorldPop). Hospitals are the area's referral hospitals, a config list (for Ruta 32: Calderón Guardia, México, San Juan de Dios); communities and hospitals snap to the largest strongly connected component of the directed graph. The area is a **pipeline parameter** (name or bbox in config), not fixed in code. |
| 2 | What happens if a segment is cut? | For each community, find the fastest route to the nearest referral hospital. Remove one segment at a time, **closing both carriageways** (87 % of Ruta 32 edges in OSM are one-way pairs), and compare. The difference is the extra time; also count dependent population and communities left with no path. |
| 3 | What was the rain? | Add accumulated IMERG rainfall as **context, not detection** (S5: it does not separate closures from normal days). SME2 failed S2c and is not used. |
| 4 | Which matter most? | Rank segments by **criticality** (by consequence). Segments with zero impact are counted but not listed as critical. |
| optional | Did the radar see change? | ΔdB detection between two GCOV passes, kept as an experimental layer that can be empty. Its result at landslide scale is negative (§5). |

**No fixed data as a seed.** Nothing decides which segments matter from fixed kilometres, sites or coordinates: not the Lanamme (2023) report, not MOPT kilometres, not press coordinates. Press closure dates are used only as validation labels, never to choose where to look. Lanamme stays as a documentary reference.

**Generalization.** The pipeline is designed to generalize to corridors with an OSM road network; Ruta 32 is the demonstration case. It was **not tested** elsewhere, so we do not say it works anywhere. Limits: OSM quality varies, hospitals may be badly registered, and the referral-hospital metric needs a sensible referral set for each area. Configured per area, so not Ruta-32-specific code: the bbox, the referral hospitals, the speed per road class (the current values are Costa Rican OSM medians) and the population raster (WorldPop CRI 2020 is a per-country file). Specific to Ruta 32: the closure dates used as validation labels and the S2, S2c and S5 test results, which describe this corridor only.

Example: a stretch of Ruta 32 is cut. A community that reached the hospital through it must take an alternate route or go to another hospital. That time difference is the "extra time" users see.

### Input constraints (NISAR, for the optional layer)

- Both GCOV passes must share the **same track, the same direction (ascending or descending) and the same processing version (CRID)**. Never mix them.
- Pixel size is 10 m or 20 m depending on location.
- Provisional data: CRID `P05023` (GCOV exists only from Jun 19, 2026; none before). Validated data: CRID `P05036`.
- **Data gap: Jul 27 – Aug 10.** Repeat cycle: 12 days.
- NISAR data is large: work only with the corridor, never with whole scenes.

## 5. Negative results

Decision G1 (Sat 14 Nov, about 16:35 CR): **NO-GO** for generating candidates by detecting landslide scars with NISAR GCOV.

Evidence:

- **Tests 1, 2 and 3 of S2:** no method separated a real closure event from the control pair.
- **Step A (synthetic detectability).** Criteria were written before computing. Setup: ΔdB in HV, 5×5 boxcar, threshold 3.5 dB (percentile 99.5 of the 069 D control, Aug 30 → Sep 11), 200 random positions in a 500 m strip each side of the OSM axis, minimum blob 9 px. Verdict: **FAIL**.

| Patch | −3 dB | −5 dB | −8 dB |
|---|---|---|---|
| 1×1 (0.01 ha) | 2.5 % | 2.5 % | 2.5 % |
| 3×3 (0.09 ha) | 2.5 % | 2.5 % | 4 % |
| 5×5 (0.25 ha) | 3.5 % | 13.5 % | 52 % |
| 10×10 (1 ha) | 47.5 % | 100 % | 100 % |

  Criterion: a 5×5 patch at −5 dB detected in at least 70 %; result 13.5 %. False detections about 1.1 per km² (so the limit is sensitivity, not noise). **Minimum detectable change: about 10×10 px (≈1 ha) at −5 dB.** Sensitivity only: with a 3 px minimum blob, 5×5 at −5 dB reaches 70 % with 3.1 false per km²; the verdict was fixed at 9 px and does not change.
- **Step B (exploratory, no test value).** Matches between 069 D and 105 A blobs under 100 m (HV, 9 px), observed vs null (null mean, p95): event B (Jul 1→13) 0 (3.8, 7); C (Jul 25→Aug 18) 3 (9.6, 17); D (Oct 5→17) 5 (2.4, 7); F (Sep 11→23) 2 (2.5, 5); control 8 (4.6, 9). No event exceeds p95, and the control is as far above chance as the best event.
- **Step C (GUNW coherence):** not run, because step A failed.

**Honest reading.** With GCOV at 10 m and this flow, small landslides are not seen. We do **not** claim NISAR cannot detect them with other products (GUNW, offsets, per-pixel series); those are untested. The raw step A/B scripts and tables were removed from the repo by the team; the numbers above are the record (see `STATUS.md`, `SPIKING.md`).

### Soil moisture (S2c): FAIL

SME2 covers the route (55 granules since Jun 19, S1′). Criteria were written before computing: mean SME2 in a 500 m strip around Ruta 32, last pass before each closure against the 75th percentile of the same series on non-closure dates. Result: 1 of 4 events (v1) and 2 of 6 (v2, after adding the Jul 17 and Oct 8 closures). The two that exceed the baseline are in early July, the seasonal wet peak. No pixel has a "recommended" retrieval flag (provisional product). Not tested: per-pixel anomaly against a climatology (only 5 months of data).

### Rain (S5): reading passes, signal FAILS

IMERG Late daily was read for 317 days. The 12-day rain before the closure exceeds the 75th percentile of its baseline in 3 of 8 events (Aug 17, Oct 5, Oct 8: percentiles 93 to 97); the event median (81 mm) is below the baseline median (105 mm). We show rain as context, never as a cause. Not tested: other accumulation windows, because choosing one after seeing the data would bias the result.

### Impact metric (S4′)

On the real network (7 136 nodes, 758 communities), closing one carriageway of Ruta 32 creates false isolations (87 % of its edges are one-way). Closing both carriageways (19 closure units), only the nearest referral hospital passed the criteria (12.7 % suspect isolations); the nearest hospital and a regional reference set failed (54.3 %). Limits: closure units are coarse (up to 61 km), the hospital list is provisional, population is not joined, and no case was reviewed by hand (`SPIKING.md` S4′).

## 6. How to read the results

These points shape every piece of user-facing text.

- Segments are **critical by consequence**, not confirmed landslides. The UI says "critical segment" (*tramo crítico*). The word "candidate" survives only as a key name in the data files (`candidates`) so the frozen schema does not break.
- Exposure is a **hypothesis**: rainfall data has ~10 km resolution and, in our test, the 12-day rain exceeded its baseline before only 3 of 8 closures. Never say "confirmed closure" or "caused by rain".
- Two radar passes are 12 days apart, so any change may include more than one event.
- Radar evidence is shown as "not detectable at this scale", with its numbers, when no change layer exists.
- "Isolated" means no route to the referral hospital, not no road. The UI says so.

## 7. Scope

The core is a map showing critical segments, the extra time to hospital and the exposure context. Everything else is built around that.

| Piece | Includes |
|---|---|
| Analysis | Road network, hospital-access impact, rain context (IMERG) |
| Map | Corridor map, critical segments, hospitals, communities; optional radar change layer (hidden if empty) |
| Segments and impact | List of critical segments with extra time, dependent population and affected communities |
| Simulation | Manual closure of a segment, recalculated in the browser |
| Exposure context | Rainfall chart, "Why?" explanation (hypotheses) |
| Delivery | Public static site, also usable offline; open-source repository, MIT license |
| Negative results | The detectability, soil moisture and rain findings, shown with their numbers |

If it is not in this table, it is out of scope. Out of scope also: landslide-scar detection as a product feature, fixed seed data (Lanamme sites, MOPT kilometres, press coordinates) and more than one region at once. Do not add accounts, a backend server or other regions unless the team decides it.

## 8. Data sources

| Source | Use | Status |
|---|---|---|
| OpenStreetMap | Roads, hospitals, communities. **ODbL: attribution required** | S4′: the graph works; closing both carriageways and snapping to the strongly connected component are required (87 % of Ruta 32 is one-way pairs) |
| WorldPop | Population that depends on the segment (exposure of people) | S7 passes: CRI 2020 at 100 m downloads over HTTPS and clips to the bbox |
| IMERG Late daily (GPM) | Exposure: rainfall context, 0.1° (~10 km). "Late" because Final takes up to 4 months | S5: read passes (317 days, 9 cells per day); signal fails (3 of 8 closures) |
| NISAR L3 SME2 (soil moisture) | Not used in the product | Covers the route since Jun 19 (S1′); S2c failed: it does not rise before closures |
| NISAR L2 GCOV (ASF / Earthdata) | **Only** for the detectability result (§5) and the optional change layer | Coverage verified from Jun 19, 2026; detection negative |
| Press closures (citing MOPT, CONAVI, CNE) | **Validation labels only**, never to choose where to look | Press notes only; primary statement missing |
| Lanamme (2023) report | Documentary reference, not an input | — |

## 9. Team, timeline and decisions

- Team of 4 on paper (Ron, Ian Angulo, Wilberth Guillen, Iván Barboza); from Saturday afternoon the work continues **solo (Ron)**, by priority, with no hand-offs.
- Times are Costa Rica time. Start Sat Nov 14 09:00; assumed close Sun Nov 15 23:59 (to confirm).
- Gates: **G1** done (NO-GO on detection, §5); **G2 Sun 14:00** feature freeze; **G3 Sun 18:00** code freeze (bug fixes only).
- Spike results are in `SPIKING.md`; the decision log is in `STATUS.md`. All spikes are closed (S3 partial: no primary statement). Decision D8 in `STATUS.md` sets the product after them.
- Fixed: MIT license with attribution to NASA and OpenStreetMap; static site on GitHub Pages; headline metric = extra time to the referral hospital + dependent population; short branches merged into `main`.

## 10. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Radar cannot detect landslide-scale change (happened) | Product is consequence (criticality); the negative results are shown as findings with numbers |
| SME2 and rain do not anticipate closures (happened) | Exposure is rain as context only; no predictive claim |
| "Nearest hospital" gives false isolations and zero park impact | Nearest referral hospital and both carriageways closed (D8); coarse closure units remain open in `STATUS.md` |
| Very few people actually isolated | Headline stays extra time + dependent population |
| S4 measurements disagree on isolated communities | Listed in `CHANGES.md` and `STATUS.md` until reconciled (E5) |
| WorldPop not integrated in P5 | Criticality is 0 for all while population is `null`; E4 integrates it |
| OSM quality varies; hospitals badly registered | State the limit; do not claim it works anywhere |
| No official source for the closure dates | Use them only as validation labels, worded as press notes |
| Heavy data or slow download | Limit to the corridor |
| Deployment fails at the end | Publish a skeleton in the first hour; test on every deploy |
| Shared data format breaks between analysis and web | `make validate` on every change |

## 11. Working principles

1. **Keep the two parts independent.** The analysis writes data; the web reads it. Neither depends on the other's internals.
2. **Never overclaim.** Say "critical segment", "signal", "hypothesis". Never say "confirmed closure" or "caused by rain". Never say it works anywhere.
3. **No fixed seed data.** Which segments matter comes from the network, not from Lanamme sites, MOPT kilometres or press coordinates.
4. **Do not invent data.** If a number is unknown, leave a placeholder or mark it pending; never fabricate figures, dates or community names.
5. **The frontend never waits for the analysis.** It works from sample data from the start.
6. **No raw NISAR data in version control.**
7. **Keep scope tight.** Prefer cutting a feature over breaking the demo.

## 12. Glossary

| Term | Meaning here |
|---|---|
| NISAR | NASA–ISRO radar satellite, 12-day repeat |
| SAR | Synthetic aperture radar; images day and night, through clouds |
| GCOV | NISAR product: calibrated backscatter on a map grid, 10 or 20 m pixels |
| dB / ΔdB | Decibels; the dB difference between two passes is our change measure |
| CRID | Processing-version code of a product; never mixed |
| Provisional / validated | Maturity level of NISAR data |
| IMERG | NASA (GPM) rainfall product, 0.1° |
| OSM | OpenStreetMap, our road network |
| Critical segment (*tramo crítico*) | Road segment ranked by consequence: what happens to hospital access if it is cut. Not a confirmed landslide. In the data files it keeps the key name `candidates` |
| Exposure | Recent rain on the corridor (IMERG). Context, never detection |
| Referral hospital | A hospital in the area's config list (for Ruta 32: Calderón Guardia, México or San Juan de Dios, in San José). The hospitals of the graph since D8; "isolated" means no route to any of them |
| SME2 | NISAR L3 soil-moisture product; failed test S2c and is not used |
| GUNW | NISAR interferogram/coherence product; untested for detection |
