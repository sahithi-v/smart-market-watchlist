from datetime import datetime, timezone, timedelta
from app.signals.cooldown import collapse_cooldown_groups


def _e(symbol_id, detector, ts, sigma):
    return {"symbol_id": symbol_id, "detector": detector, "ts": ts, "sigma": sigma}


def test_small_move_then_big_move_within_window_keeps_the_bigger_one():
    t0 = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    events = [_e(1, "SIGMA_MOVE", t0, 1.6), _e(1, "SIGMA_MOVE", t0 + timedelta(minutes=20), 2.9)]
    result = collapse_cooldown_groups(events, cooldown_hours=4.0)
    assert len(result) == 1
    assert result[0]["sigma"] == 2.9


def test_events_outside_window_stay_separate():
    t0 = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    events = [_e(1, "SIGMA_MOVE", t0, 2.0), _e(1, "SIGMA_MOVE", t0 + timedelta(hours=5), 2.1)]
    assert len(collapse_cooldown_groups(events, cooldown_hours=4.0)) == 2


def test_different_detectors_never_collapse_together():
    t0 = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    events = [_e(1, "SIGMA_MOVE", t0, 2.0), _e(1, "VOLUME_SPIKE", t0, 2.0)]
    assert len(collapse_cooldown_groups(events, cooldown_hours=4.0)) == 2


def test_different_symbols_never_collapse_together():
    t0 = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    events = [_e(1, "SIGMA_MOVE", t0, 2.0), _e(2, "SIGMA_MOVE", t0, 2.0)]
    assert len(collapse_cooldown_groups(events, cooldown_hours=4.0)) == 2


def test_empty_input():
    assert collapse_cooldown_groups([]) == []