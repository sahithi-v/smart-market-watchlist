import pytest
from app.signals.presets import (
    EMISSION_FLOOR_SIGMA, PRESETS, SensitivityOverrideTooLow, resolve_min_sigma,
)


def test_floor_is_loosest_preset():
    assert EMISSION_FLOOR_SIGMA == min(p["min_sigma"] for p in PRESETS.values())
    assert EMISSION_FLOOR_SIGMA == 1.5


def test_resolve_uses_preset_when_no_override():
    assert resolve_min_sigma("low", None) == 2.5
    assert resolve_min_sigma("balanced", None) == 2.0


def test_resolve_rejects_override_below_floor():
    with pytest.raises(SensitivityOverrideTooLow):
        resolve_min_sigma("high", 1.0)