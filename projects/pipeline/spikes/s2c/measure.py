"""Spike S2c: mean NISAR SME2 soil moisture in a 500 m strip around Ruta 32, per pass.

Evidence for the S2c card in SPIKING.md, not pipeline code. Criteria were written
in SPIKING.md before running. Usage:
  uv run --no-project --python 3.12 --with earthaccess --with h5py --with pyproj \
    --with shapely --with numpy python -I measure.py <OUT_DIR>
Needs Earthdata credentials in ~/.netrc (or _netrc). Reads only the strip window of
each granule over HTTP; nothing large is stored.
"""
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import earthaccess
import h5py
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import unary_union

BBOX = (-84.15, 9.95, -83.75, 10.25)  # same as S1/S2: lon_min, lat_min, lon_max, lat_max
BUFFER_M = 500
FILL = -9999
OVERPASS = "https://overpass-api.de/api/interpreter"

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

# Ruta 32 geometry from OSM (ref=32, trunk or motorway), projected to EASE-Grid 2.0.
query = (
    f'[out:json][timeout:90];way["ref"="32"]["highway"~"^(trunk|motorway)$"]'
    f"({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});out geom;"
)
req = urllib.request.Request(
    OVERPASS, urllib.parse.urlencode({"data": query}).encode(),
    headers={"User-Agent": "vantage-spike/0.1", "Accept": "application/json"},
)
ways = json.load(urllib.request.urlopen(req, timeout=120))["elements"]
to_ease = Transformer.from_crs(4326, 6933, always_xy=True)
lines = []
for w in ways:
    xy = [to_ease.transform(p["lon"], p["lat"]) for p in w["geometry"]]
    if len(xy) > 1:
        lines.append(LineString(xy))
strip = unary_union(lines).buffer(BUFFER_M)
print(f"{len(ways)} ways, strip area {strip.area / 1e6:.1f} km2", flush=True)

earthaccess.login(strategy="netrc")
granules = earthaccess.search_data(
    short_name="NISAR_L3_SME2_PROVISIONAL_V1",
    bounding_box=BBOX,
    temporal=("2026-06-01", "2026-11-14"),
    count=300,
)
# Keep the highest version suffix per (date, track, frame).
best = {}
for g in granules:
    name = g["meta"]["native-id"]
    m = re.search(r"SME2_\d+_(\d{3})_([AD])_(\d{3})_.*?_(\d{8})T(\d{6})_.*_(\d{3})$", name)
    key = (m.group(4), m.group(1), m.group(3))
    if key not in best or m.group(6) > best[key][1]:
        best[key] = (g, m.group(6), m)
print(f"{len(granules)} granules, {len(best)} unique passes", flush=True)

files = earthaccess.open([v[0] for v in best.values()])
rows = []
for (key, (g, ver, m)), fh in zip(best.items(), files):
    date, track, frame = key
    try:
        with h5py.File(fh) as h:
            grid = h["science/LSAR/SME2/grids"]
            x = grid["xCoordinates"][:]
            y = grid["yCoordinates"][:]
            minx, miny, maxx, maxy = strip.bounds
            cols = np.where((x >= minx) & (x <= maxx))[0]
            rws = np.where((y >= miny) & (y <= maxy))[0]
            if len(cols) == 0 or len(rws) == 0:
                rows.append(dict(date=date, track=track, frame=frame, direction=m.group(2),
                                 time=m.group(5), n_strip=0, n_valid=0, n_rec=0,
                                 sm_all="", sm_rec="", note="no overlap"))
                continue
            c0, c1, r0, r1 = cols[0], cols[-1] + 1, rws[0], rws[-1] + 1
            sm = grid["soilMoisture"][r0:r1, c0:c1]
            q = grid["retrievalQualityFlag"][r0:r1, c0:c1]
            xx, yy = np.meshgrid(x[c0:c1], y[r0:r1])
            inside = shapely.contains_xy(strip, xx, yy)
            valid = inside & (sm != FILL) & np.isfinite(sm)
            rec = valid & (q == 0)
            rows.append(dict(
                date=date, track=track, frame=frame, direction=m.group(2), time=m.group(5),
                n_strip=int(inside.sum()), n_valid=int(valid.sum()), n_rec=int(rec.sum()),
                sm_all=f"{sm[valid].mean():.4f}" if valid.any() else "",
                sm_rec=f"{sm[rec].mean():.4f}" if rec.any() else "", note=""))
    except Exception as e:  # keep going; a failed granule is reported, not hidden
        rows.append(dict(date=date, track=track, frame=frame, direction=m.group(2),
                         time=m.group(5), n_strip=0, n_valid=0, n_rec=0,
                         sm_all="", sm_rec="", note=f"error: {e}"[:120]))
    print(rows[-1], flush=True)

rows.sort(key=lambda r: (r["track"], r["frame"], r["date"]))
with open(out / "sme2_strip.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("done", len(rows))
