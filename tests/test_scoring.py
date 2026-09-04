from datetime import datetime, timezone, timedelta
from app.signals.scoring import score_event


def test_fresh_event_scores_higher_than_old_one():
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    assert score_event(2.0, now, now) > score_event(2.0, now - timedelta(hours=8), now)


def test_half_life_actually_halves_at_4_hours():
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    fresh = score_event(2.0, now, now)
    at_half_life = score_event(2.0, now - timedelta(hours=4), now)
    assert abs(at_half_life - fresh / 2) < 0.001


def test_pinned_scores_higher_than_unpinned():
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    assert score_event(2.0, now, now, pinned=True) == score_event(2.0, now, now, pinned=False) * 1.5


def test_negative_sigma_treated_as_magnitude():
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    assert score_event(-3.0, now, now) == score_event(3.0, now, now)


def test_affinity_scales_score_down():
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    assert score_event(2.0, now, now, detector_affinity=0.3) == score_event(2.0, now, now, detector_affinity=1.0) * 0.3