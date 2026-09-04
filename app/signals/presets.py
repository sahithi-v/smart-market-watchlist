"""Sensitivity presets. Config, not data — three rows that never change and
have no relationships, so they live in code, not Postgres.

Resolution order for any user: explicit override -> preset[sensitivity] -> DEFAULT.
"""

PRESETS: dict[str, dict] = {
    "low": {
        "min_sigma": 2.5,
        "volume_multiple": 3.0,
        "detectors": {"SIGMA_MOVE", "GAP"},
    },
    "balanced": {
        "min_sigma": 2.0,
        "volume_multiple": 3.0,
        "detectors": {"SIGMA_MOVE", "VOLUME_SPIKE", "RANGE_BREAK", "GAP", "REVERSAL"},
    },
    "high": {
        "min_sigma": 1.5,
        "volume_multiple": 2.0,
        "detectors": {"SIGMA_MOVE", "VOLUME_SPIKE", "RANGE_BREAK", "GAP", "REVERSAL"},
    },
}

DEFAULT_SENSITIVITY = "balanced"

EMISSION_FLOOR_SIGMA = min(p["min_sigma"] for p in PRESETS.values())
EMISSION_FLOOR_VOLUME_MULTIPLE = min(p["volume_multiple"] for p in PRESETS.values())

class SensitivityOverrideTooLow(ValueError):
    """A user's min_sigma override is below what the engine ever emits —
    that threshold could never match a stored event, so it would silently
    show nothing rather than raise, which is worse."""


def resolve_min_sigma(sensitivity: str, override: float | None) -> float:
    """Three-step fallback: override -> preset -> default.
    Raises SensitivityOverrideTooLow if override < EMISSION_FLOOR_SIGMA.
    """
    if override is not None:
        if override < EMISSION_FLOOR_SIGMA:
            raise SensitivityOverrideTooLow(
                f"min_sigma override {override} is below the emission floor "
                f"{EMISSION_FLOOR_SIGMA} — no event will ever be that faint"
            )
        return override

    preset = PRESETS.get(sensitivity, PRESETS[DEFAULT_SENSITIVITY])
    return preset["min_sigma"]