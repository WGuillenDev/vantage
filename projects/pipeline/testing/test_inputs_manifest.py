from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline.inputs_manifest import InputsError, manifest, run

ZONE = SimpleNamespace(id="zone-a", population_raster="work/pop/raster.tif")
FILES = {
  "configs/zone-a.toml": b"name = 'A'\n",
  "work/zone-a/osm/roads.osm": b"<osm/>",
  "work/zone-a/osm/features.osm": b"<osm/>",
  "work/zone-a/osm/extract_date.txt": b"2026-11-15\n",
  "work/zone-a/imerg/cells.csv": b"date,cell_lon\n",
  "work/zone-a/imerg/source.json": b"{}\n",
  "work/pop/raster.tif": b"\x00\x01binary",
  "output/zone-a/graph.json": b"{}\n",
  "output/zone-a/scenarios.json": b"{}\n",
  "output/zone-a/rain.csv": b"date,precip_mm\n",
}


@pytest.fixture
def base(tmp_path: Path) -> Path:
  for name, data in FILES.items():
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_bytes(data)
  return tmp_path


def test_the_manifest_lists_every_input_and_output(base: Path):
  result = manifest(ZONE, base)
  assert result["zone"] == "zone-a"
  assert set(result["inputs"]) | set(result["outputs"]) == set(FILES)
  assert result["inputs"]["work/pop/raster.tif"]["bytes"] == len(FILES["work/pop/raster.tif"])


def test_the_same_text_has_one_hash_with_crlf_or_lf(base: Path):
  before = manifest(ZONE, base)["outputs"]["output/zone-a/rain.csv"]
  (base / "output/zone-a/rain.csv").write_bytes(b"date,precip_mm\r\n")
  assert manifest(ZONE, base)["outputs"]["output/zone-a/rain.csv"] == before


def test_a_missing_file_is_a_clean_error_naming_it(base: Path):
  (base / "work/zone-a/osm/roads.osm").unlink()
  with pytest.raises(InputsError, match="roads.osm"):
    manifest(ZONE, base)


def test_check_passes_on_what_was_written_and_names_a_changed_file(base: Path, tmp_path: Path):
  reports = tmp_path / "reports"
  run(ZONE, base, reports)
  assert "match" in run(ZONE, base, reports, check=True)
  (base / "work/zone-a/imerg/cells.csv").write_bytes(b"date,cell_lon\n2026-01-01,-84.35\n")
  with pytest.raises(InputsError, match="work/zone-a/imerg/cells.csv"):
    run(ZONE, base, reports, check=True)


def test_check_without_a_manifest_says_how_to_create_it(base: Path, tmp_path: Path):
  with pytest.raises(InputsError, match="make inputs"):
    run(ZONE, base, tmp_path / "none", check=True)
