from datetime import datetime, timezone
import pytest
from app.signals.dedupe import build_dedupe_key


def test_same_minute_collapses_to_same_key():
    a = datetime(2026, 9, 4, 11, 15, 3, tzinfo=timezone.utc)
    b = datetime(2026, 9, 4, 11, 15, 58, tzinfo=timezone.utc)
    assert build_dedupe_key("INFY", "SIGMA_MOVE", a) == build_dedupe_key("INFY", "SIGMA_MOVE", b)


def test_different_minute_differs():
    a = datetime(2026, 9, 4, 11, 15, 59, tzinfo=timezone.utc)
    b = datetime(2026, 9, 4, 11, 16, 0, tzinfo=timezone.utc)
    assert build_dedupe_key("INFY", "SIGMA_MOVE", a) != build_dedupe_key("INFY", "SIGMA_MOVE", b)


def test_naive_datetime_raises():
    with pytest.raises(ValueError):
        build_dedupe_key("INFY", "SIGMA_MOVE", datetime(2026, 9, 4, 11, 15))