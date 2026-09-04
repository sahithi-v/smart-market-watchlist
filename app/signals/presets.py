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
    """A user's min_sigma override is below what the engine ever emits."""


def resolve_min_sigma(sensitivity: str, override: float | None) -> float:
    """Three-step fallback: override -> preset -> default."""
    if override is not None:
        if override < EMISSION_FLOOR_SIGMA:
            raise SensitivityOverrideTooLow(
                f"min_sigma override {override} is below the emission floor "
                f"{EMISSION_FLOOR_SIGMA} — no event will ever be that faint"
            )
        return override
    preset = PRESETS.get(sensitivity, PRESETS[DEFAULT_SENSITIVITY])
    return preset["min_sigma"]


def resolve_thresholds(
    sensitivity: str, min_sigma_override: float | None, detectors_override: list[str] | None
) -> tuple[dict[str, float], set[str]]:
    """Returns (per-detector magnitude thresholds, enabled detector set).
    One min_sigma number can't threshold both a sigma-based detector and a
    volume-multiple detector — different units. Maps each detector to the
    right field from the resolved preset."""
    min_sigma = resolve_min_sigma(sensitivity, min_sigma_override)
    preset = PRESETS.get(sensitivity, PRESETS[DEFAULT_SENSITIVITY])

    thresholds = {
        "SIGMA_MOVE": min_sigma,
        "GAP": min_sigma,
        "REVERSAL": min_sigma,
        "RANGE_BREAK": min_sigma,
        "VOLUME_SPIKE": preset["volume_multiple"],
    }
    enabled = set(detectors_override) if detectors_override is not None else set(preset["detectors"])

    return thresholds, enabled