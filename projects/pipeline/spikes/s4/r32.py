import json, sys, urllib.request, urllib.parse
q = """[out:json][timeout:120];
area["ISO3166-1"="CR"][admin_level=2]->.cr;
way["highway"]["ref"~"(^|;)32($|;)"](area.cr);
out tags geom;"""
req = urllib.request.Request("https://overpass-api.de/api/interpreter",
    data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "spike-client/0.1"})
d = json.load(urllib.request.urlopen(req, timeout=180))
ways = d["elements"]
json.dump(d, open(sys.argv[1], "w"))
lons = [p["lon"] for w in ways for p in w["geometry"]]; lats = [p["lat"] for w in ways for p in w["geometry"]]
print("ways", len(ways), "bbox", min(lons), min(lats), max(lons), max(lats))
from collections import Counter
print(Counter(w["tags"].get("highway") for w in ways))
print(Counter(w["tags"].get("name") for w in ways).most_common(12))
