from app.signals.affinity import compute_affinity


def test_cold_start_below_min_signals_returns_full_affinity():
    assert compute_affinity(shown_count=3, dismissed_count=3, min_signals=5) == 1.0


def test_never_dismissed_stays_at_full_affinity():
    assert compute_affinity(shown_count=10, dismissed_count=0) == 1.0


def test_always_dismissed_clamps_at_floor_not_zero():
    assert compute_affinity(shown_count=10, dismissed_count=10) == 0.3


def test_half_dismissed_lands_between_floor_and_one():
    assert compute_affinity(shown_count=10, dismissed_count=5) == 0.5