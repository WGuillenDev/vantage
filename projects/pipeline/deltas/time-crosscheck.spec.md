---
slice: time-crosscheck
---

# time-crosscheck: spec

> Compares a sample of the model's travel times with an independent router and with documented reference times, and writes the result as a report (task P11, `RELIABILITY.md` step 3).

## Intent

Every time in the project comes from one constant speed per OSM road class. If those speeds are far from how long the trips really take, every extra time and every ranking is off by the same bias. This slice measures that gap on a fixed sample and reports it. An OSRM router running on OpenStreetMap shares our data, so it checks the calculation (speeds and routing), not the ground truth; documented reference times, cited by hand, are the only check that touches the real world, and there are only a few.

## Scope

Owns:

- Choosing a deterministic sample of community → referral hospital pairs from the baseline.
- Querying the public OSRM router for each pair (`make timecheck`, the only network step of this slice).
- Comparing times, computing the relative error, its median and its bias.
- Comparing the model with the hand-written reference times.
- The report `reports/<id>/time_crosscheck.json`, committed as evidence.

Non-goals:

- Changing the speeds when the check fails: the report says it, and the team decides and records it (`RELIABILITY.md`: "se ajustan las velocidades y se declara").
- Writing the reference times: a person writes `reports/<id>/reference_times.json` with a citation each; this slice never invents one.
- Checking routes, only times; and closures, only the baseline without closures.
- Publishing the report or adding it to the contract.

## Contract

Inputs: the zone (`area-config`) and its built files `output/<id>/graph.json` and `output/<id>/scenarios.json` (the baseline); optionally `reports/<id>/reference_times.json`: a list of 3 to 5 entries `{ "community_id", "hospital_id", "minutes", "source", "accessed_on" }`.

Output: `projects/pipeline/reports/<id>/time_crosscheck.json`:

| Field | Content |
|---|---|
| `router` | `"OSRM public demo, driving profile"` and `queried_on` (`YYYY-MM-DD`). |
| `limitation` | The text: "the router uses OpenStreetMap too, so it checks the calculation, not ground truth". |
| `threshold` | `{ "median_relative_error": 0.25, "min_pairs": 15 }`, the fixed rule. |
| `pairs[]` | Per pair: `community_id`, `hospital_id`, `model_s`, `router_s` (or `null`), `relative_error`. |
| `excluded` | Number of pairs the router could not route. |
| `median_relative_error`, `median_bias` | Median of `|model − router| / router` and of `(model − router) / router`. |
| `references[]` | Per reference time: the entry, `model_s` and `relative_error`; not graded. |
| `verdict` | `"pass"`, `"fail"` or `"insufficient_pairs"`. |

Definitions:

| Term | Definition |
|---|---|
| Sample | Communities with a baseline route, sorted by baseline time ascending then id number, from which up to 20 are taken at evenly spaced positions; if fewer than 20 exist, all of them. |
| Endpoints | The coordinates of the community's node and of its baseline hospital's node, both from `graph.json`. The router snaps them to its own roads. |
| Verdict | `pass` if at least 15 pairs have a router time and their median relative error is at most 0.25; `fail` if at least 15 have one and the median is above it; `insufficient_pairs` otherwise. |

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py]
  When time-crosscheck builds the sample, it takes up to 20 communities with a baseline route at evenly spaced positions of the list sorted by baseline time and then by id number, and the same inputs always give the same sample.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py]
  When time-crosscheck queries a pair, it uses the `graph.json` coordinates of the community's node and of the node of its baseline hospital.
- INV-04 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py]
  When time-crosscheck finishes, `median_relative_error` and `median_bias` are the medians, over the pairs that have a router time, of the absolute difference between `model_s` and `router_s` divided by `router_s`, and of the signed difference divided by `router_s`.
- INV-05 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py]
  When time-crosscheck finishes, the verdict is `pass` when at least 15 pairs have a router time and the median relative error is at most 0.25, `fail` when at least 15 do and the median is above it, and `insufficient_pairs` otherwise.
- INV-06 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py]
  If the router finds no route for a pair, then time-crosscheck records `router_s: null`, leaves the pair out of the medians and counts it in `excluded`.
- INV-07 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py]
  If a reference time has no `source` or no `accessed_on`, then time-crosscheck exits non-zero with an English error naming the entry and writes no report.
- INV-09 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py]
  When time-crosscheck sends a request, it identifies itself with a generic client name and no personal data, and waits at least one second between requests.
- INV-10 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py]
  If the router answers with an error status or the network fails, then time-crosscheck exits non-zero with an English error naming the status and writes no report.

## Deferred / Open questions

Testing gaps (all claims are tagged `none`; `builder` turns each into `test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_time_crosscheck.py` with a stubbed router): INV-01, INV-02, INV-04, INV-05, INV-06, INV-07, INV-09, INV-10.

- **Expected result:** OSRM's default car profile is faster than the model's constants (trunk 60 and primary 40 km/h against OSRM's higher defaults), so a `fail` with a negative bias is plausible. It is a finding about the speeds, not an error; the team then decides whether to adjust and records it.
- **Reference times (RELIABILITY asks for 3 to 5):** nobody has written them. Without them the report has an empty `references` and the check is router-only. Who writes them, and from which sources, is open.
- **Public server limits:** the OSRM demo server is for light use; about 20 requests spaced one second apart stay inside it. A hosted or self-run OSRM is out of scope.
- **Snapping differences:** the router snaps the node coordinates to its own roads, so a few seconds of noise per pair is expected and not corrected.
- **`make` target:** `make timecheck AREA=<id>` is added with this slice; `pipeline-run` does not run it in `make all`.
- **Docs out of sync:** `RELIABILITY.md` step 3 asks for 15 to 20 pairs and a median error of at most 25 %; this spec keeps both.

## Acceptance criteria

- ACC-01 [manual]
  Given the Ruta 32 run, when a person reads `reports/ruta-32/time_crosscheck.json`, then it states the verdict, the median relative error and its bias, and the person can quote them, whatever the verdict.
