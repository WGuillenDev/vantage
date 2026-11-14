"""Spike S5: daily IMERG Late (GPM_3IMERGDL V07) area mean over the Ruta 32 corridor bbox.

Evidence for the S5 card in SPIKING.md; criteria were written there before reading values.
Usage: uv run --no-project --python 3.12 --with earthaccess --with h5py --with numpy python -I measure.py <OUT_DIR>
Needs Earthdata credentials in ~/.netrc and the "NASA GESDISC DATA ARCHIVE" app authorized.
Cells whose centre lies strictly inside the bbox; days are UTC days.
"""
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import earthaccess
import h5py
import numpy as np

W, S, E, N = -84.15, 9.95, -83.75, 10.25
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

earthaccess.login(strategy="netrc")
granules = earthaccess.search_data(short_name="GPM_3IMERGDL", version="07",
                                   temporal=("2026-01-01", "2026-11-14"), count=400)
files = earthaccess.open(granules)


def read(args):
    g, fh = args
    day = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]
    t0 = time.time()
    with h5py.File(fh) as h:
        lon, lat = h["lon"][:], h["lat"][:]
        ci = np.where((lon > W) & (lon < E))[0]
        ri = np.where((lat > S) & (lat < N))[0]
        v = h["precipitation"][0, ci[0]:ci[-1] + 1, ri[0]:ri[-1] + 1]
    ok = v > -9000
    return {"day": day, "cells": int(v.size), "valid": int(ok.sum()),
            "mm": f"{v[ok].mean():.3f}" if ok.any() else "", "seconds": round(time.time() - t0, 2),
            "bytes_requested": int(v.nbytes)}


with ThreadPoolExecutor(8) as ex:
    rows = list(ex.map(read, zip(granules, files)))
rows.sort(key=lambda r: r["day"])
with open(out / "imerg_daily.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(len(rows), "days", rows[0]["day"], rows[-1]["day"])
