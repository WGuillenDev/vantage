import json
import shutil
from pathlib import Path

import pytest

from pipeline.validate import validate_dir

CONTRACT = Path(__file__).resolve().parents[2] / "contract"


@pytest.fixture
def data(tmp_path: Path) -> Path:
    shutil.copytree(CONTRACT / "examples", tmp_path, dirs_exist_ok=True)
    return tmp_path


def edit(folder: Path, name: str, change) -> None:
    path = folder / name
    obj = json.loads(path.read_text(encoding="utf-8"))
    change(obj)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_examples_are_valid(data: Path):
    assert validate_dir(data) == []


def test_variant_without_before_after_is_valid(data: Path):
    shutil.copy(CONTRACT / "shared" / "no-toggle" / "meta.json", data / "meta.json")
    (data / "overlay_before.png").unlink()
    (data / "overlay_after.png").unlink()
    assert validate_dir(data) == []


def test_missing_file_is_reported(data: Path):
    (data / "graph.json").unlink()
    assert "graph.json: file is missing" in validate_dir(data)


def test_unknown_field_is_rejected(data: Path):
    edit(data, "graph.json", lambda g: g.update(extra=1))
    assert any("graph.json" in e and "extra" in e for e in validate_dir(data))


def test_passes_must_share_track(data: Path):
    edit(data, "meta.json", lambda m: m["passes"]["after"].update(track=2))
    assert any("track" in e for e in validate_dir(data))


def test_unknown_edge_in_scenario(data: Path):
    edit(data, "scenarios.json", lambda s: s["candidates"][0]["edge_ids"].append("e99"))
    assert any("unknown edge e99" in e for e in validate_dir(data))


def test_isolated_must_be_affected(data: Path):
    edit(data, "scenarios.json", lambda s: s["candidates"][0]["isolated_community_ids"].append("c5"))
    assert any("subset" in e for e in validate_dir(data))


def test_missing_overlay_file(data: Path):
    (data / "overlay_change.png").unlink()
    assert any("overlay_change.png does not exist" in e for e in validate_dir(data))


def test_rain_must_cover_period(data: Path):
    rows = (data / "rain.csv").read_text(encoding="utf-8").splitlines()
    (data / "rain.csv").write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
    assert any("must cover" in e for e in validate_dir(data))


def test_change_layer_is_optional(data: Path):
    def drop(m):
        m.pop("passes")
        m.pop("overlays")

    edit(data, "meta.json", drop)
    edit(data, "change.geojson", lambda c: c.update(features=[]))
    edit(data, "scenarios.json", lambda s: [c.update(zone_ids=[], mean_delta_db=None) for c in s["candidates"]])
    assert validate_dir(data) == []


def test_exposure_radar_evidence_is_restricted(data: Path):
    edit(data, "scenarios.json", lambda s: s["candidates"][0]["exposure"].update(radar_evidence="detected"))
    assert any("radar_evidence" in e for e in validate_dir(data))


def test_oversized_overlay_is_rejected(data: Path):
    (data / "overlay_change.png").write_bytes(b"0" * (2 * 1024 * 1024 + 1))
    assert any("is larger than" in e for e in validate_dir(data))
