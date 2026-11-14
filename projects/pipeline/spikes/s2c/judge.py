"""Spike S2c: apply the criteria written in SPIKING.md to sme2_strip.csv.
Usage: uv run --no-project --python 3.12 --with numpy python -I judge.py sme2_strip.csv
Times are UTC in the file, converted to Costa Rica time (UTC-6). Press gives no closure hour for B, C and the end of D, so day starts and ends are assumed."""
import csv, numpy as np
from datetime import datetime, timedelta
CR = timedelta(hours=6)
import sys
rows = list(csv.DictReader(open(sys.argv[1])))
for r in rows:
    r["t"] = datetime.strptime(r["date"]+r["time"], "%Y%m%d%H%M%S") - CR   # Costa Rica time
    r["sm"] = float(r["sm_all"]) if r["sm_all"] else None
# closure windows (CR time): start, end (end generous where press gives none)
ev = {"B": (datetime(2026,7,2), datetime(2026,7,4,23,59)),
      "C": (datetime(2026,8,17), datetime(2026,8,18,23,59)),
      "F": (datetime(2026,9,13,7,30), datetime(2026,9,19,0,0)),   # incl. 18 Sep episode
      "D": (datetime(2026,10,5,18,0), datetime(2026,10,6,23,59))}
D3 = timedelta(days=3)
def excluded(t): return any(s-D3 <= t <= e for s,e in ev.values())
series = {}
for r in rows:
    if r["sm"] is not None: series.setdefault((r["track"], r["frame"]), []).append(r)
main = {("069","083"), ("105","007")}   # coverage >= ~80% of the strip
res = {}
for k, s in sorted(series.items()):
    s.sort(key=lambda r: r["t"])
    base = [r["sm"] for r in s if not excluded(r["t"])]
    if len(base) < 3: print(k, "baseline too small", len(base)); continue
    p75 = np.percentile(base, 75); med = np.median(base)
    print(f"\n{k} {'(MAIN)' if k in main else ''} n_base={len(base)} base median={med:.3f} p75={p75:.3f}  valid px ~{int(np.median([int(r['n_valid']) for r in s]))}")
    for e,(st,_) in ev.items():
        pre = [r for r in s if r["t"] < st]
        if not pre: print(f"  {e}: no pre-event pass"); continue
        p = pre[-1]; lag = (st-p["t"]).days
        flag = p["sm"] > p75
        print(f"  {e}: pre pass {p['t']:%d %b %H:%M} lag {lag:2d} d  sm={p['sm']:.3f}  >p75: {flag}")
        res.setdefault(e, []).append((k in main, flag, p["sm"], med))
print("\nPer event, MAIN series only:")
passes = 0
for e, v in res.items():
    m = [x for x in v if x[0]]
    ok = all(x[1] for x in m) if m else None
    passes += bool(ok)
    print(f"  {e}: exceed p75 in {sum(x[1] for x in m)}/{len(m)} main series, all-series {sum(x[1] for x in v)}/{len(v)}")
pre_vals = [np.mean([x[2] for x in v if x[0]]) for v in res.values()]
base_meds = [np.mean([x[3] for x in v if x[0]]) for v in res.values()]
print(f"events passing (all main series exceed p75): {passes}/4;  median event SM {np.median(pre_vals):.3f} vs median baseline {np.median(base_meds):.3f}")
