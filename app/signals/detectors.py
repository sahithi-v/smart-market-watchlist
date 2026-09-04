from app.signals.presets import EMISSION_FLOOR_SIGMA


def detect_sigma_move(
    current_price_paise: int,
    prev_close_paise: int,
    mean_return: float,
    stddev_return: float,
    min_sigma: float = EMISSION_FLOOR_SIGMA,
) -> dict | None:
    """Pure function: no DB, no I/O. min_sigma defaults to the system
    emission floor, not 'balanced' — every sensitivity level reads from
    the same stored event instead of triggering a re-run per user.
    """
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