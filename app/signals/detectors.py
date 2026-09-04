from app.signals.presets import EMISSION_FLOOR_SIGMA, EMISSION_FLOOR_VOLUME_MULTIPLE


def detect_sigma_move(
    current_price_paise: int,
    prev_close_paise: int,
    mean_return: float,
    stddev_return: float,
    min_sigma: float = EMISSION_FLOOR_SIGMA,
) -> dict | None:
    """Pure function: no DB, no I/O. min_sigma defaults to the system
    emission floor, not 'balanced' — every sensitivity reads the same event."""
    if prev_close_paise <= 0 or not stddev_return:
        return None

    today_return = (current_price_paise - prev_close_paise) / prev_close_paise
    z = (today_return - mean_return) / stddev_return

    if abs(z) < min_sigma:
        return None

    return {
        "detector": "SIGMA_MOVE",
        "sigma": round(z, 4),
        "return_pct": round(today_return * 100, 2),
    }


def detect_volume_spike(
    current_volume: int,
    avg_volume_20d: float,
    min_multiple: float = EMISSION_FLOOR_VOLUME_MULTIPLE,
) -> dict | None:
    """Pure function: no DB, no I/O. Fires when today's volume-so-far is
    an unusual multiple of this symbol's own 20-day average — real traded
    volume, not a proxy for what caused it.

    events.sigma is NOT NULL and shared across detector types — this
    stores the volume multiple in it too, so cooldown/scoring (which just
    need "how big was this") work identically regardless of detector.
    Not perfectly commensurable with a statistical sigma — a real
    simplification, worth naming if asked, not hidden.
    """
    if not avg_volume_20d or avg_volume_20d <= 0:
        return None

    multiple = current_volume / avg_volume_20d
    if multiple < min_multiple:
        return None

    return {
        "detector": "VOLUME_SPIKE",
        "sigma": round(multiple, 4),
        "volume_multiple": round(multiple, 2),
    }