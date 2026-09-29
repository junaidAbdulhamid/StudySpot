from ml.src.snapshot import ALLOWED, check_source_columns
from ml.src.synthetic import generate_history

REAL_OCCUPANCY_SOURCES = {"seed", "manual", "crowd_report", "model", "derived", "sensor"}


def test_generated_snapshot_matches_the_allowed_schema():
    frames, metadata, truth = generate_history(days=1, locations=2, seed=1)
    assert set(frames) == set(ALLOWED)
    check_source_columns(frames)  # raises on any unexpected/missing column
    assert metadata["synthetic"] is True
    assert "true_occupancy" not in set().union(*[f.columns for f in frames.values()])


def test_generated_sources_use_real_enum_values():
    frames, _, _ = generate_history(days=1, locations=1, seed=1)
    assert set(frames["estimates"].source.unique()) <= REAL_OCCUPANCY_SOURCES
    assert set(frames["observations"].source.unique()) <= REAL_OCCUPANCY_SOURCES
    assert set(frames["locations"].noise_level.unique()) <= {"quiet", "moderate", "social"}


def test_generator_is_deterministic_for_a_given_seed():
    first, _, _ = generate_history(days=1, locations=2, seed=99)
    second, _, _ = generate_history(days=1, locations=2, seed=99)
    for name in first:
        assert first[name].equals(second[name])
