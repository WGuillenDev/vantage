# VANTAGE — Approach

> Orientation for anyone joining the project, human or agent. Source of truth: the VANTAGE project document (NASA Space Apps 2026). If this text and the work disagree, flag it; do not silently pick one.

## 1. Summary

> **Direction change (G1, Sat 14 Nov 2026, about 16:35 CR time).** Detecting landslide scars with NISAR GCOV was a **NO-GO** (see §5). The product is now **risk = consequence × exposure**. Sections below follow that decision; older text is marked as discarded, not deleted.

VANTAGE answers two questions for the Ruta 32 corridor (Costa Rica):

1. **Who loses access if this road segment is cut?** (consequence: road network + hospitals + population, 100 % computed.)
2. **How exposed is the segment?** (exposure: IMERG rainfall and, if the SME2 test works, NISAR soil moisture. These are context signals, not detection.)

> Provisional project line (rain and consequence only, until the SME2 test, S2c, says otherwise): *VANTAGE shows which road segments, if cut, leave communities without a good route to a hospital, and how exposed they are to rain.*
> Only if S2c passes: *NISAR shows where the slope is saturated and VANTAGE says who it leaves without a way out.*

It is our entry for the NASA Space Apps 2026 challenge **"Dancing with the SARs"** (Nov 14–15, 2026): use NISAR radar to detect changes on Earth's surface. Our honest finding is that, with GCOV at 10 m and our flow, small landslides are not detectable (§5); we present that as a result with numbers.

The product has two parts:

1. **Offline analysis.** Road network → impact (consequence) → exposure layer → export. A radar change layer is **optional** and may be empty.
2. **Static web app.** Shows the results on a map and lets the user simulate closing a road segment, with no server.

The two parts are connected only by shared data files. Neither depends on the inner workings of the other.

## 2. Problem

- Ruta 32 (San José–Limón, through Braulio Carrillo) closes during heavy rain because of landslides. Anyone who depends on the affected stretch loses the way to a hospital.
- Closures with a press source (all are press notes that cite the MOPT; the primary MOPT statement is still missing, so they are **unverified**): Jul 2–4; Aug 17–18; Sep 13 and Sep 18; Oct 5. Earlier closures (Feb 5–8) predate any NISAR GCOV data.
- Discarded as unverified: the July list "8–11, 9, 16–17, 20" that this document carried before, and closures of Jun 21, Jul 17 and Jul 20 that appear in no note.
- Alternate routes are limited: Ruta 126 for light vehicles only, Ruta 10 for freight.

**Why radar, and what we found.** Radar does not depend on light or clouds and NISAR revisits every 12 days. We tested whether subtracting two GCOV passes shows landslide-scale change and it does not (§5). Radar-derived products other than GCOV ΔdB (GUNW coherence, offsets, per-pixel series) remain **untested**, not ruled out.

**The gap we fill.** Whatever the hazard signal, the question "who is left without a route" needs the road network. VANTAGE computes that consequence for every segment, without needing to know in advance where a slope moved.

## 3. Objective and user

Give one kind of user a clear answer: *which road segments matter most for hospital access (critical segments), what happens if one is cut, and how exposed is it?*

- **User:** someone monitoring the route (risk management, emergency response). No accounts or roles: open the page and use it.
- **Headline metric:** extra time to hospital, plus the population that depends on the segment.
- A community is **isolated** only when it has no path to any hospital after the segment is removed.

## 4. Method

The method is deterministic: same data in, same result out. Two questions, no fixed seed sites.

| Step | Question | What happens |
|---|---|---|
| 1 | What is the road network and who depends on it? | Split the area's OSM roads into segments, with hospitals and communities, and attach population (WorldPop). The area is a **pipeline parameter** (name or bbox in config), not fixed in code. |
| 2 | What happens if a segment is cut? | For each community, find the fastest route to the nearest hospital. Remove one segment at a time and compare. The difference is the extra time; also count dependent population and communities left with no path. |
| 3 | How exposed is it? | Add accumulated IMERG rainfall and, if the S2c test works, NISAR SME2 soil moisture as a percentile. These are **context, not detection**. |
| 4 | Which matter most? | Rank segments by **criticality** (by consequence). Segments with zero impact are counted but not listed as critical. |
| optional | Did the radar see change? | ΔdB detection between two GCOV passes, kept as an experimental layer that can be empty. Its result at landslide scale is negative (§5). |

**No fixed data as a seed.** Nothing decides which segments matter from fixed kilometres, sites or coordinates: not the Lanamme (2023) report, not MOPT kilometres, not press coordinates. Press closure dates are used only as validation labels, never to choose where to look. Lanamme stays as a documentary reference.

**Generalization.** The pipeline is designed to generalize to corridors with an OSM road network; Ruta 32 is the demonstration case. It was **not tested** elsewhere, so we do not say it works anywhere. Limits: OSM quality varies, hospitals may be badly registered, and SME2 may be unreliable in dense forest.

Example: a stretch of Ruta 32 is cut. A community that reached the hospital through it must take an alternate route or go to another hospital. That time difference is the "extra time" users see.

### Input constraints (NISAR, for the optional layer and SME2)

- Both GCOV passes must share the **same track, the same direction (ascending or descending) and the same processing version (CRID)**. Never mix them.
- Pixel size is 10 m or 20 m depending on location.
- Provisional data: CRID `P05023` (GCOV exists only from Jun 19, 2026; none before). Validated data: CRID `P05036`.
- **Data gap: Jul 27 – Aug 10.** Repeat cycle: 12 days.
- NISAR data is large: work only with the corridor, never with whole scenes.

## 5. Negative detection result

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

## 6. How to read the results

These points shape every piece of user-facing text.

- Segments are **critical by consequence**, not confirmed landslides. The UI says "critical segment" (*tramo crítico*). The word "candidate" survives only as a key name in the data files (`candidates`) so the frozen schema does not break.
- Exposure is a **hypothesis**: rainfall data has ~10 km resolution and soil moisture changes the radar return. Never say "confirmed closure" or "caused by rain".
- Two radar passes are 12 days apart, so any change may include more than one event.
- Radar evidence is shown as "not detectable at this scale", with its numbers, when no change layer exists.

## 7. Scope

The core is a map showing critical segments, the extra time to hospital and the exposure context. Everything else is built around that.

| Piece | Includes |
|---|---|
| Analysis | Road network, hospital-access impact, exposure (IMERG, optional SME2) |
| Map | Corridor map, critical segments, hospitals, communities; optional radar change layer (hidden if empty) |
| Segments and impact | List of critical segments with extra time, dependent population and affected communities |
| Simulation | Manual closure of a segment, recalculated in the browser |
| Exposure context | Rainfall chart, soil moisture if available, "Why?" explanation (hypotheses) |
| Delivery | Public static site, also usable offline; open-source repository, MIT license |
| Negative result | The detectability finding, shown with its numbers |

If it is not in this table, it is out of scope. Out of scope also: landslide-scar detection as a product feature, fixed seed data (Lanamme sites, MOPT kilometres, press coordinates) and more than one region at once. Do not add accounts, a backend server or other regions unless the team decides it.

## 8. Data sources

| Source | Use | Status |
|---|---|---|
| OpenStreetMap | Roads, hospitals, communities. **ODbL: attribution required** | S4 partial: the graph works, but "nearest hospital" gives zero impact on 43 % of the test segments |
| WorldPop | Population that depends on the segment (exposure of people) | S7 passes: CRI 2020 at 100 m downloads over HTTPS and clips to the bbox |
| IMERG Late daily (GPM) | Exposure: rainfall context, 0.1° (~10 km). "Late" because Final takes up to 4 months | Docs verified; access test (S5) not advanced |
| NISAR L3 SME2 (soil moisture) | Exposure, optional: only if test S2c (does SME2 rise before closures?) works | Pending (S2c, max 40 min) |
| NISAR L2 GCOV (ASF / Earthdata) | **Only** for the detectability result (§5) and the optional change layer | Coverage verified from Jun 19, 2026; detection negative |
| Press closures (citing MOPT, CONAVI, CNE) | **Validation labels only**, never to choose where to look | Press notes only; primary statement missing |
| Lanamme (2023) report | Documentary reference, not an input | — |

## 9. Team, timeline and decisions

- Team of 4 on paper (Ron, Ian Angulo, Wilberth Guillen, Iván Barboza); from Saturday afternoon the work continues **solo (Ron)**, by priority, with no hand-offs.
- Times are Costa Rica time. Start Sat Nov 14 09:00; assumed close Sun Nov 15 23:59 (to confirm).
- Gates: **G1** done (NO-GO on detection, §5); **G2 Sun 14:00** feature freeze; **G3 Sun 18:00** code freeze (bug fixes only).
- Spike results are in `SPIKING.md`; the decision log is in `STATUS.md`. Pending: S2c (SME2, optional).
- Fixed: MIT license with attribution to NASA and OpenStreetMap; static site on GitHub Pages; headline metric = extra time to hospital + dependent population; short branches merged into `main`.

## 10. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Radar cannot detect landslide-scale change (happened) | Product is risk = consequence × exposure; the negative result is shown as a finding with numbers |
| SME2 rise before closures is not shown or is unreliable in dense forest | Exposure uses IMERG only; the project continues unchanged |
| "Nearest hospital" gives zero impact on many segments (43 % in tests) | Compare against a reference hospital instead of the nearest; open question in `STATUS.md` |
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
| Exposure | How exposed a segment is to rain or saturated soil (IMERG, optional SME2). Context, never detection |
| SME2 | NISAR L3 soil-moisture product; its use is pending test S2c |
| GUNW | NISAR interferogram/coherence product; untested for detection |
