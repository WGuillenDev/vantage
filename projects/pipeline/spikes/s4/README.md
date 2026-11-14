# Spike S4: road network and impact metric

Exploration scripts behind the S4 card in `SPIKING.md`. They are evidence, not pipeline code: nothing here is imported by `source/` or run by the tests. Downloads go to a folder **outside the repo** (`<DL>` below); never commit them.

Run every command from the repo root. Spike-only assumptions are written at the top of each script.

| Script | What it measured | Command |
|---|---|---|
| `r32.py` | Ruta 32 in OSM (`ref=32`): ways, classes, extent | `uv run --no-project --python 3.12 --with osmnx python -I projects/pipeline/spikes/s4/r32.py <DL>/r32.json` |
| `spike.py` | Graph size and components, hospitals and places by tag, `maxspeed` medians, one Ruta 32 cut, San José→Guápiles time. Areas `corridor` `[-84.10, 9.90, -83.72, 10.25]` and `regional` `[-84.30, 9.80, -83.40, 10.45]` | `uv run --no-project --python 3.12 --with osmnx --with matplotlib python -I projects/pipeline/spikes/s4/spike.py <DL> <corridor\|regional> <cut_west> <cut_east>` |
| `size.py` | Estimated `graph.json` size for a bbox | `uv run --no-project --python 3.12 --with osmnx python -I projects/pipeline/spikes/s4/size.py <DL> -84.10 9.90 -83.72 10.25` |
| `g1_measure.py` | G1 measurement: 495 test segments on the network up to Limón | see below |
| `review_isolated.py` | Hand review of the 18 communities isolated by the Guápiles–Siquirres cut | see below |

Cuts used in the card: park `-83.98 -83.92`, Guápiles–Siquirres `-83.70 -83.55`. Without the two cut arguments, `spike.py` uses the park cut.

The last two reuse `road_graph.build` (P3), so they run on branch `feat/road-graph` after `make osm` has downloaded the extract into `projects/pipeline/work/osm/`:

```bash
uv run --project projects/pipeline python -I projects/pipeline/spikes/s4/g1_measure.py projects/pipeline/work/osm <OUT>
uv run --project projects/pipeline python -I projects/pipeline/spikes/s4/review_isolated.py projects/pipeline/work/osm <OUT>
```

Overpass returns live data, so a later download can give slightly different counts than the 14 Nov 2026 runs recorded in the card.
