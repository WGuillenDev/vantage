---
slice: area-config
---

# area-config: spec

> Reads and validates the per-zone configuration that every other pipeline stage takes its zone parameters from (task E3).

## Intent

VANTAGE is designed for any corridor with an OSM road network, and Ruta 32 is only the demonstration case (D4, D8). For that to be true in code, everything that is specific to a zone must live in one config file per zone and nowhere else: the area, the referral hospitals, the speed per road class, the population raster and the rain period. The app is meant to show several zones, so each zone also needs a stable id that names its output folder. Without this slice each stage would hard-code its own copy of those values.

## Scope

Owns:

- The config format: one TOML file per zone in `projects/pipeline/configs/<id>.toml`.
- Loading and validating a config, and choosing the zone to run (`--area <id>`).
- Resolving a zone's output folder, `projects/pipeline/output/<id>/`.
- Producing the zone record (`id`, `name`, `bbox`, `validated`) that `pipeline-run` writes into `areas.json` (and `name` and `bbox` into `meta.json → area`).
- Committing `configs/ruta-32.toml`, the demonstration zone.

Non-goals:

- Building the graph, choosing which OSM features count as hospitals, computing population or rain. The config only names the inputs; `road-graph`, `population-data` and `rain-context` use them.
- Writing `areas.json`, `meta.json` or the `make` targets. That is `pipeline-run`.
- A default zone: the Makefile may pick `ruta-32` for convenience, but the loader never falls back to one.
- Choosing a second zone or filling its values. Never invented (see Deferred).
- Checking that a hospital id exists in OSM or that a raster file exists. Those fail in the stage that uses them.

## Contract

Config file, one per zone. The file name without `.toml` is the zone id (`configs/ruta-32.toml` is zone `ruta-32`):

```toml
name = "Ruta 32 (San José–Limón)"     # shown in the UI
validated = true                      # true only if results were checked by hand
bbox = [-84.30, 9.80, -82.95, 10.45]  # [w, s, e, n]; the only area (network, rain, population)

[hospitals]
referral = ["way/1168011056"]         # OSM ids of the referral hospitals (list not final)

[speed_model_kmh]                     # one speed per OSM road class, with a cited source
trunk = 60

[closure]
roads = ["Ruta 32"]                   # `road` values studied as closure units (the corridor)
alternates = [                        # routes shown as alternates; may be empty; cite the source next to the list
  { name = "Ruta 126", vehicles = "light" },
  { name = "Ruta 10", vehicles = "freight" },
]

[detection_limits]                    # optional; the negative S2 radar result, only for the zone it was measured on
min_detectable_area_ha = 1
min_delta_db = 5
note = "GCOV 10 m: a change smaller than about 1 ha is not detectable (SPIKING.md S2)"

[population]
raster = "work/worldpop/cri_ppp_2020.tif"   # path under the pipeline folder; never committed
url = "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/CRI/cri_ppp_2020.tif"   # where `make worldpop` fetches it

[rain]
start = "2026-01-01"
end = "2026-11-13"
```

Values above only show the shape. Real values are not final (see Deferred).

| Topic | Rule |
|---|---|
| Required keys | `name`, `validated`, `bbox`, `hospitals.referral` (at least one id), `speed_model_kmh` (at least one class, each speed greater than 0), `closure.roads` (at least one road name), `closure.alternates` (may be an empty list; each entry has a non-empty `name` and `vehicles` of `light` or `freight`), `population.raster`, `population.url`, `rain.start`, `rain.end`. No key has a default. |
| Zone id | The file name without `.toml`: lowercase letters, digits and single hyphens. |
| `bbox` | Four numbers `[w, s, e, n]` with `w < e`, `s < n`, longitude in [-180, 180] and latitude in [-90, 90]. |
| Dates | `YYYY-MM-DD`, with `start` not after `end`. |
| Speeds | Each a finite number greater than 0; each road class name non-empty. |
| Optional table | `detection_limits` (`min_detectable_area_ha` and `min_delta_db` finite and above 0, non-empty `note`); when absent the zone makes no radar claim. |
| Unknown keys | Rejected. |
| Repeated values | `hospitals.referral`, `closure.roads` and the `name` of each `closure.alternates` entry have no repeats. |
| File | UTF-8 TOML, with or without a byte-order mark. The loader only finds files whose name is a valid zone id, with exactly that spelling. |
| Errors | In English; they name the config file and the key. A failed load stops the run before any output is written. |

## Invariants

- INV-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  When a valid config is loaded, the zone it yields has the file's id (its name without `.toml`) and the same `name`, `validated`, `bbox`, referral hospital ids, speed model, raster path and rain period as the file.
- INV-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  If a required key is missing or empty, then the loader exits non-zero with an English error naming the file and the key, and writes no output.
- INV-03 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  If a config contains a key the format does not define, then the loader exits non-zero with an English error naming the key.
- INV-04 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  If a value is invalid (a zone id that is not lowercase words joined by hyphens, a `bbox` that is not four numbers with `w < e`, `s < n`, valid longitudes and latitudes, a date that is not `YYYY-MM-DD` or a `start` after `end`, or a speed that is not a finite number above 0, or an empty road class name), then the loader exits non-zero with an English error naming the key.
- INV-07 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  If `--area` names an id with no file in `configs/` (a file whose name differs only by case does not count), then the loader exits non-zero with an English error that lists the available ids. Only files that can be loaded are listed: a name that is not a valid zone id, or a folder named `*.toml`, is not.
- INV-10 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  When a zone is loaded, its output folder is `output/<id>/`.

- INV-11 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  If `hospitals.referral`, `closure.roads` or the `name` of the `closure.alternates` entries contain the same value twice, then the loader exits non-zero with an English error naming the key.
- INV-12 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  When a config file starts with a UTF-8 byte-order mark or uses CRLF line endings, then the loader reads it as it would the same file without them.
- INV-13 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  If the config file cannot be read or is not valid UTF-8 TOML, then the loader exits non-zero with an English error naming the file, and never raises an unhandled exception.

## Deferred / Open questions

Testing gaps: none. All claims run `projects/pipeline/testing/test_area_config.py`; `test_area_config_adversarial.py` adds boundary cases found by `breaker`.

- **Referral hospital ids (Ian):** the list for Ruta 32 (Calderón Guardia, México, San Juan de Dios) is not confirmed, and only Calderón Guardia has an id seen in spike S4 (`way/1168011056`). `ruta-32.toml` carries the three ids looked up in OSM on 2026-11-15 (México `way/25400008`, San Juan de Dios `way/24857117`) as a provisional list until Ian confirms; Tony Facio (`way/1451665976`) and Guápiles (`way/326924912`) are not included. The loader stops on an empty list by INV-02.
- **`unclassified` speed (Ian):** needs a value with a cited source before the real run (the 14 Nov extract has too few tagged edges for a median).
- **Population raster delivery (decided in `population-data`):** `population.raster` is the local path and `population.url` is where `make worldpop` fetches it from (S7: a 31.5 MB HTTPS file). The raster is never committed.
- **Second zone:** which zone, if any, joins Ruta 32 is not chosen, and its hospitals, speeds and raster are not prepared. A zone with `validated: false` is allowed by this contract; the label it gets in the UI is `zone-picker`.
- **Referral criterion outside Costa Rica:** the idea of a "referral hospital" may not carry over to another country; not tested (`approach.md`).
- **`validated` for Ruta 32:** ACC-01 sets `validated: true`, but no result has been checked by hand yet. Revisit before the real run so the label does not overclaim.
- **Rain end date:** `ruta-32.toml` pins `rain.end` for reproducibility, so it must be advanced by hand before a new run; a "latest available" option is not specified.
- **Docs out of sync:** `context/structure.md` §4 shows an `[area]` table with `bbox` and `referral_hospitals`; this spec's flat layout supersedes it. A person updates the doc.
- **Road class names:** the loader only requires a non-empty name; it does not check the name is an OSM `highway` class. A typo surfaces in `road-graph`, which uses the speeds.

## Acceptance criteria

- ACC-01 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  Given `configs/ruta-32.toml`, when the loader runs with `--area ruta-32`, then it yields a zone with id `ruta-32`, `validated: true` and its output folder `output/ruta-32/`.
- ACC-02 [test: uv run --project projects/pipeline pytest projects/pipeline/testing/test_area_config.py]
  Given a copy of `ruta-32.toml` saved as `other-zone.toml` with a different `name` and `bbox`, when the loader runs with `--area other-zone`, then the zone carries the new values and no source file was changed.
