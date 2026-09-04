from datetime import datetime


def score_breakdown(
    sigma: float,
    event_ts: datetime,
    now: datetime,
    pinned: bool = False,
    detector_affinity: float = 1.0,
    half_life_hours: float = 4.0,
) -> dict:
    """Single source of truth for the score and every multiplier that
    produces it. Used both to compute the final score and to power the
    'Why This Is Here' breakdown in the UI, so the two can never drift
    apart from each other."""
    age_hours = (now - event_ts).total_seconds() / 3600
    recency_decay = 0.5 ** (age_hours / half_life_hours)
    pin_weight = 1.5 if pinned else 1.0
    score = abs(sigma) * recency_decay * pin_weight * detector_affinity
    return {
        "magnitude": abs(sigma), "recency_decay": recency_decay,
        "pin_weight": pin_weight, "affinity": detector_affinity, "score": score,
    }


def score_event(
    sigma: float,
    event_ts: datetime,
    now: datetime,
    pinned: bool = False,
    detector_affinity: float = 1.0,
    half_life_hours: float = 4.0,
) -> float:
    """Pure function. Higher score = more attention-worthy.
    Thin wrapper around score_breakdown() — unchanged signature/return
    type, so existing callers and tests are unaffected."""
    return score_breakdown(
        sigma, event_ts, now, pinned, detector_affinity, half_life_hours
    )["score"]