from datetime import datetime

from app.signals.cooldown import collapse_cooldown_groups
from app.signals.scoring import score_event

MAX_DIGEST_ITEMS = 5
COOLDOWN_HOURS = 4.0


def assemble_digest(
    raw_events: list[dict],
    thresholds: dict[str, float],
    enabled_detectors: set[str],
    now: datetime,
    latest_prices: dict[int, int],
    affinities: dict[str, float] | None = None,
) -> dict:
    """Pure function: no DB. Filters by the user's enabled detectors AND
    each detector's own resolved threshold, collapses cooldown groups,
    scores (using per-detector affinity if provided), ranks, caps."""
    affinities = affinities or {}
    above_threshold = [
        e for e in raw_events
        if e["detector"] in enabled_detectors
        and abs(e["sigma"]) >= thresholds.get(e["detector"], float("inf"))
    ]
    collapsed = collapse_cooldown_groups(above_threshold, cooldown_hours=COOLDOWN_HOURS)

    scored = [
        {**e, "score": score_event(
            e["sigma"], e["ts"], now,
            pinned=e.get("pinned", False),
            detector_affinity=affinities.get(e["detector"], 1.0),
        )}
        for e in collapsed
    ]
    scored.sort(key=lambda e: e["score"], reverse=True)

    top = scored[:MAX_DIGEST_ITEMS]
    other_count = max(0, len(scored) - len(top))
    items = [_format_item(e, latest_prices.get(e["symbol_id"])) for e in top]
    empty_reason = "quiet" if not raw_events else None

    return {"items": items, "other_count": other_count, "empty_reason": empty_reason}


def _explain(e: dict) -> str:
    payload = e["payload"]
    if e["detector"] == "SIGMA_MOVE":
        return_pct = payload.get("return_pct", 0.0)
        return f"Moved {return_pct:+.1f}% ({e['sigma']:+.1f}\u03c3 vs its 30-day volatility)."
    if e["detector"] == "VOLUME_SPIKE":
        multiple = payload.get("volume_multiple", e["sigma"])
        return f"Trading at {multiple:.1f}\u00d7 its 20-day average volume."
    return f"{e['detector']} triggered."


def _format_item(e: dict, current_price_paise: int | None) -> dict:
    return {
        "event_id": e["event_id"], "ticker": e["ticker"], "name": e["name"],
        "detector": e["detector"], "sigma": round(e["sigma"], 2),
        "current_price_paise": current_price_paise, "explanation": _explain(e),
        "ts": e["ts"].isoformat(),
    }