import pytest
from app.signals.detectors import detect_sigma_move


def test_fires_above_floor():
    result = detect_sigma_move(104_00, 100_00, mean_return=0.0, stddev_return=0.01)
    assert result["sigma"] == pytest.approx(4.0)


def test_silent_below_floor():
    assert detect_sigma_move(100_50, 100_00, mean_return=0.0, stddev_return=0.01) is None


def test_default_uses_floor_not_balanced():
    result = detect_sigma_move(101_60, 100_00, mean_return=0.0, stddev_return=0.01)
    assert result is not None


def test_guards_zero_stddev():
    assert detect_sigma_move(110_00, 100_00, mean_return=0.0, stddev_return=0.0) is None


def test_guards_bad_prev_close():
    assert detect_sigma_move(110_00, 0, mean_return=0.0, stddev_return=0.01) is None