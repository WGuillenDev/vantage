"""Spike S5: apply the criteria written in SPIKING.md to imerg_daily.csv.

Usage: uv run --no-project --python 3.12 --with numpy python -I judge.py imerg_daily.csv
Rain signal: 12-day sum of the area-mean daily rain ending the day before a closure starts
(Costa Rica date), against the same 12-day sum on dates with no closure and not within 3 days
before one. PASS if >= 75 % of events exceed the baseline p75 and the event median exceeds the
baseline median. Closure start hours and end dates not given by the press are assumed (see SPIKING.md).
"""
import csv
import sys
from datetime import date, datetime, timedelta

import numpy as np

rain = {}
bad_days = []
for r in csv.DictReader(open(sys.argv[1])):
    d = date.fromisoformat(r["day"])
    if r["mm"] == "" or int(r["valid"]) < int(r["cells"]):
        bad_days.append(r["day"])
    if r["mm"] != "":
        rain[d] = float(r["mm"])

dt = datetime
EV = {  # name: (start date in Costa Rica, last closed day)
    "A": (date(2026, 2, 5), date(2026, 2, 8)),
    "A2": (date(2026, 2, 14), date(2026, 2, 16)),
    "B": (date(2026, 7, 2), date(2026, 7, 4)),
    "B2": (date(2026, 7, 17), date(2026, 7, 17)),
    "C": (date(2026, 8, 17), date(2026, 8, 18)),
    "F": (date(2026, 9, 13), date(2026, 9, 19)),
    "D": (date(2026, 10, 5), date(2026, 10, 6)),
    "D2": (date(2026, 10, 8), date(2026, 10, 10)),
}


def s12(start):
    days = [start - timedelta(days=k) for k in range(1, 13)]
    return sum(rain[d] for d in days) if all(d in rain for d in days) else None


def excluded(d):
    return any(s - timedelta(days=3) <= d <= e for s, e in EV.values())


days = sorted(rain)
base = [v for d in days if d - timedelta(days=12) >= days[0] and not excluded(d) and (v := s12(d)) is not None]
p75, med = np.percentile(base, 75), float(np.median(base))
print(f"days {len(rain)} ({days[0]}..{days[-1]}); missing/partial days: {bad_days or 'none'}")
print(f"baseline n={len(base)} median={med:.1f} mm p75={p75:.1f} mm p90={np.percentile(base, 90):.1f} mm")
vals, hits = {}, 0
for name, (s, _) in EV.items():
    v = s12(s)
    vals[name] = v
    if v is None:
        print(f"  {name} {s}: window incomplete")
        continue
    hit = v > p75
    hits += hit
    print(f"  {name} {s}: 12-day sum {v:6.1f} mm  > p75: {hit}  (percentile in baseline: {100 * np.mean(np.array(base) < v):.0f})")
valid = [v for v in vals.values() if v is not None]
ev_med = float(np.median(valid))
print(f"events above p75: {hits}/{len(valid)} ({hits / len(valid):.0%}); event median {ev_med:.1f} mm vs baseline median {med:.1f} mm")
print("VERDICT:", "PASS" if hits / len(valid) >= 0.75 and ev_med > med else "FAIL")
