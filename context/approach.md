# VANTAGE — Approach

> Orientation for anyone joining the project, human or agent. Source of truth: the VANTAGE project document (NASA Space Apps 2026). If this text and the work disagree, flag it; do not silently pick one.

## 1. Summary

VANTAGE uses NISAR radar data to show **where a hillside moved near Ruta 32 (Costa Rica)** and **which communities lose a good route to a hospital** because of it.

> NISAR sees where the mountain moved; VANTAGE says who it leaves without a way out.

It is our entry for the NASA Space Apps 2026 challenge **"Dancing with the SARs"** (Nov 14–15, 2026): use NISAR radar to detect changes on Earth's surface.

The product has two parts:

1. **Offline analysis.** Detects surface change from NISAR, places it on the road network and measures the effect on hospital access.
2. **Static web app.** Shows the results on a map and lets the user simulate closing a road segment, with no server.

The two parts are connected only by shared data files. Neither depends on the inner workings of the other.

## 2. Problem

- Ruta 32 (San José–Limón, through Braulio Carrillo) closes during heavy rain because of landslides. Anyone who depends on the affected stretch loses the way to a hospital.
- July 2026 had several closures reported by the press (dates to be confirmed with MOPT, CONAVI or CNE): Jul 8–11, Jul 9, Jul 16–17, Jul 20.
- Alternate routes are limited: Ruta 126 for light vehicles only, Ruta 10 for freight.

**Why radar.** Optical satellites cannot see through clouds, and the rainy season is when landslides happen. NISAR's radar does not depend on light or clear skies and revisits the same point every 12 days. Comparing two passes shows where the surface changed.

**The gap we fill.** NISAR says *where* the terrain changed, not *who it affects*. VANTAGE connects that change to the road network and measures what happens to hospital access.

## 3. Objective and user

Give one kind of user a clear answer: *which road segments matter most for hospital access, and what happens if one is cut?*

- **User:** someone monitoring the route (risk management, emergency response). No accounts or roles: open the page and use it.
- **Headline metric:** extra time to hospital, plus the population that depends on the segment.
- A community is **isolated** only when it has no path to any hospital after the segment is removed.

## 4. Method

The method is deterministic: same data in, same result out. Four steps, each answering one question.

| Step | Question | What happens |
|---|---|---|
| 1 | Where did the terrain change? | Compare two NISAR passes (before and after an event) by subtracting backscatter in dB. Noise, water and radar shadow are handled first; very small changes are dropped afterwards. Result: change zones. |
| 2 | Which road segments does that change touch? | Split the corridor's roads into segments. Those that touch a change zone, with a margin, become **candidate segments** (*tramos candidatos*). |
| 3 | What happens if they are cut? | For each community, find the fastest route to the nearest hospital. Remove one candidate segment at a time and compare. The difference is the extra time. Also count the population that depends on the segment and the communities left with no path. |
| 4 | Which matter most? | Rank segments by **criticality**: how much hospital access worsens if the segment is cut. Add daily rainfall for the period as context. |

Example: a landslide cuts a stretch of Ruta 32. A community that reached the hospital through it must take an alternate route or go to another hospital. That time difference is the "extra time" users see.

### Input constraints (NISAR)

- Both passes must share the **same track, the same direction (ascending or descending) and the same processing version (CRID)**. Never mix them.
- Pixel size is 10 m or 20 m depending on location.
- Provisional data: CRID `P05023` (released from Jul 20; acquisitions from Jun 17 to part of Oct). Validated data: CRID `P05036` (acquisitions from Oct 21; released Nov 6).
- **Data gap: Jul 27 – Aug 10.** Repeat cycle: 12 days.
- NISAR data is large: work only with the corridor, never with whole scenes.

## 5. How to read the results

These points shape every piece of user-facing text.

- A radar change is a **signal, not a confirmation**. Soil moisture also alters the radar return. This is why results are **candidate segments**: places to verify on the ground, not confirmed closures.
- Two passes are 12 days apart, so a change may include more than one event.
- A small landslide covers few pixels; in that case we show change zones at hillside scale.
- Rainfall data has ~10 km resolution. It gives context and is consistent with the change, but it is a **hypothesis, not the cause**. Always word it that way.

## 6. Scope

The core is a map showing the detected change, the critical segments and the extra time to hospital. Everything else is built around that.

| Piece | Includes |
|---|---|
| Analysis | NISAR change, road network, hospital-access impact |
| Map | Corridor map, change layer, before/after comparison |
| Segments and impact | Candidate list, with extra time, dependent population and affected communities |
| Simulation | Manual closure of a segment, recalculated in the browser |
| Rain context | Rainfall chart and a "Why?" explanation |
| Delivery | Public static site, also usable offline; open-source repository, MIT license |

If it is not in this table, it is out of scope. Do not add accounts, a backend server or other regions unless the team decides it.

## 7. Data sources

| Source | Use | Status |
|---|---|---|
| NISAR L2 GCOV (ASF / Earthdata) | Core: radar backscatter | Docs verified; coverage over the route pending |
| IMERG Late daily (GPM) | Rain context, 0.1° (~10 km). "Late" because the Final version takes up to 4 months | Docs verified; access test pending |
| OpenStreetMap | Roads, hospitals, communities. **ODbL: attribution required** | Pending |
| WorldPop | Population that depends on the segment | Pending: access unverified |
| Real closures (MOPT, CONAVI, CNE, press) | Choose the validation event | Dates to confirm |

## 8. Team, timeline and decisions

- Team of 4: **backend** Ron and Ian Angulo; **frontend** Wilberth Guillen and Iván Barboza. Task split: pending.
- Times are Costa Rica time. Start Sat Nov 14 09:00; assumed close Sun Nov 15 23:59 (to confirm).
- Gates: **Sat 15:00** (do compatible NISAR passes exist and is the change visible? if not, Plan B), **Sun 14:00** feature freeze, **Sun 18:00** code freeze (bug fixes only).
- Six spikes on Saturday decide the path: NISAR coverage, resolution and detectability, validation event, road network and metric, rainfall, frontend smoke test.

Decisions already made (Nov 13, 2026):

| Decision | Value |
|---|---|
| License | MIT for code; attribution to NASA and OpenStreetMap |
| Headline metric | Extra time to hospital + population dependent on the segment |
| Before/after | Own opacity control |
| Hosting | Static site |
| Branching | Short branches merged into `main`; two-sided review only for changes to the shared data format |

## 9. Risks and fallbacks

| Risk | Fallback |
|---|---|
| No usable NISAR passes over the route at the event dates | Change event or area within Costa Rica |
| Landslide too small for a 10–20 m pixel | Hillside-scale disturbance zones |
| Very few people actually isolated | Headline stays extra time + dependent population |
| No official source for the closure date | Present results as "candidates" |
| Heavy data or slow download | Limit to the corridor and a single pair of passes |
| WorldPop not accessible | Use only extra time and count of communities |
| Deployment fails at the end | Publish a skeleton in the first hour; test on every deploy |
| Shared data format breaks between analysis and web | Validate it automatically; changes need review from both sides |

## 10. Working principles

1. **Keep the two parts independent.** The analysis writes data; the web reads it. Neither depends on the other's internals.
2. **Never overclaim.** Say "candidate", "signal", "hypothesis". Never say "confirmed closure" or "caused by rain".
3. **Do not invent data.** If a number is unknown, leave a placeholder or mark it pending; never fabricate figures, dates or community names.
4. **The frontend never waits for the analysis.** It works from sample data from the start.
5. **No raw NISAR data in version control.**
6. **Keep scope tight.** Prefer cutting a feature over breaking the demo.

## 11. Glossary

| Term | Meaning here |
|---|---|
| NISAR | NASA–ISRO radar satellite, 12-day repeat |
| SAR | Synthetic aperture radar; images day and night, through clouds |
| L-band | NISAR's radar wavelength |
| GCOV | NISAR product: calibrated backscatter on a map grid, 10 or 20 m pixels |
| Gamma-0 | Backscatter corrected for terrain relief |
| dB / ΔdB | Decibels; the dB difference between two passes is our change measure |
| Speckle | Grainy radar noise, filtered before comparing |
| CRID | Processing-version code of a product; never mixed |
| Provisional / validated | Maturity level of NISAR data |
| IMERG | NASA (GPM) rainfall product, 0.1° |
| OSM | OpenStreetMap, our road network |
| Candidate segment (*tramo candidato*) | Road segment crossing a change zone; must be verified on the ground |
