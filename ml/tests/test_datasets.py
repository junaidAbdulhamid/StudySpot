"""Integration-level guarantees: cross-location isolation, chronological split leakage,
privacy, forecast-target alignment, and on-disk dataset versioning/reproducibility."""

import pandas as pd
import pytest
from conftest import config as make_config
from ml.src.config import PipelineConfig
from ml.src.datasets import build_dataset, build_frame, validate_dataset
from ml.src.snapshot import write_snapshot
from ml.src.synthetic import generate_history

PRIVATE_COLUMNS = {
    "email",
    "display_name",
    "avatar_url",
    "auth_provider_id",
    "user_id",
    "reporter_user_id",
    "access_token",
    "raw_gps_history",
}


@pytest.fixture(scope="module")
def two_location_history():
    raw, _, _ = generate_history(start="2026-09-01T00:00:00Z", days=2, locations=2, seed=7)
    return raw


@pytest.fixture(scope="module")
def built(two_location_history):
    cfg = make_config(start="2026-09-01T06:00:00Z", end="2026-09-01T18:00:00Z")
    return build_frame(two_location_history, cfg)


def test_build_frame_produces_a_validated_frame(built):
    frame, report = built
    assert len(frame) > 0
    assert report["rows"] == len(frame)


def test_dataset_contains_no_private_columns(built):
    frame, _ = built
    assert not PRIVATE_COLUMNS & set(frame.columns)


def test_chronological_splits_never_overlap(built):
    frame, _ = built
    splits = {
        name: frame[frame.split == name].timestamp for name in ("train", "validation", "test")
    }
    if len(splits["train"]) and len(splits["validation"]):
        assert splits["train"].max() < splits["validation"].min()
    if len(splits["validation"]) and len(splits["test"]):
        assert splits["validation"].max() < splits["test"].min()


def test_forecast_target_timestamp_is_exact_not_nearest(built):
    frame, _ = built
    for horizon in (15, 30, 60, 120):
        assert (
            frame[f"target_{horizon}m_timestamp"] == frame.timestamp + pd.Timedelta(minutes=horizon)
        ).all()


def test_cross_location_isolation(two_location_history):
    cfg = make_config(start="2026-09-01T06:00:00Z", end="2026-09-01T18:00:00Z")
    baseline, _ = build_frame(two_location_history, cfg)
    locations = sorted(baseline.location_id.unique())
    assert len(locations) == 2
    target, other = locations[0], locations[1]

    tampered = dict(two_location_history)
    for name, frame in tampered.items():
        if "location_id" in frame.columns:
            df = frame.copy()
            numeric = df.select_dtypes("number").columns.difference(
                ["total_seats", "occupied_seats"]
            )
            df.loc[df.location_id == other, numeric] = 0
            tampered[name] = df
    mutated, _ = build_frame(tampered, cfg)

    baseline_rows = baseline[baseline.location_id == target].reset_index(drop=True)
    mutated_rows = mutated[mutated.location_id == target].reset_index(drop=True)
    pd.testing.assert_frame_equal(baseline_rows, mutated_rows)


def test_build_dataset_is_immutable_and_replayable(tmp_path, two_location_history):
    snapshot = tmp_path / "raw" / "v1"
    write_snapshot(snapshot, two_location_history, {"synthetic": True})
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("{}")
    cfg = PipelineConfig.from_file(
        cfg_path, start="2026-09-01T06:00:00Z", end="2026-09-01T18:00:00Z"
    )
    destination, _ = build_dataset(
        snapshot, tmp_path / "processed", "v1", cfg, allow_synthetic=True
    )

    with pytest.raises(FileExistsError):
        build_dataset(snapshot, tmp_path / "processed", "v1", cfg, allow_synthetic=True)

    frame, manifest, checks = validate_dataset(destination, replay=True)
    assert checks["source_replay"] == "passed"
    assert manifest["synthetic"] is True
    assert len(frame) == manifest["rows"]


def test_synthetic_dataset_requires_explicit_opt_in(tmp_path, two_location_history):
    snapshot = tmp_path / "raw"
    write_snapshot(snapshot, two_location_history, {"synthetic": True})
    cfg = PipelineConfig(start="2026-09-01T06:00:00Z", end="2026-09-01T18:00:00Z")
    with pytest.raises(ValueError, match="synthetic"):
        build_dataset(snapshot, tmp_path / "processed", "v2", cfg, allow_synthetic=False)
