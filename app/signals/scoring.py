from datetime import datetime


def score_event(
    sigma: float,
    event_ts: datetime,
    now: datetime,
    pinned: bool = False,
    detector_affinity: float = 1.0,
    half_life_hours: float = 4.0,
) -> float:
    """Pure function. Higher score = more attention-worthy.
    recency_decay: exponential half-life, not a hard cutoff.
    user_weight: pinned symbols get a flat 1.5x boost.
    detector_affinity: defaults to 1.0 (your doc's cold-start value) until
    the dismiss endpoint + affinity query exist to compute a real one.
    """
    age_hours = (now - event_ts).total_seconds() / 3600
    recency_decay = 0.5 ** (age_hours / half_life_hours)
    user_weight = 1.5 if pinned else 1.0
    return abs(sigma) * recency_decay * user_weight * detector_affinity