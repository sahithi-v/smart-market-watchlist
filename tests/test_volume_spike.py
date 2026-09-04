import pytest
from app.signals.detectors import detect_volume_spike


def test_fires_above_floor():
    result = detect_volume_spike(current_volume=50_000, avg_volume_20d=20_000)
    assert result["volume_multiple"] == pytest.approx(2.5)


def test_silent_below_floor():
    assert detect_volume_spike(current_volume=25_000, avg_volume_20d=20_000) is None


def test_guards_zero_avg_volume():
    assert detect_volume_spike(current_volume=50_000, avg_volume_20d=0) is None