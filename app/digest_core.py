from datetime import datetime
from app.signals.cooldown import collapse_cooldown_groups
from app.signals.scoring import score_breakdown

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
        {**e, **score_breakdown(
            e["sigma"], e["ts"], now,
            pinned=e.get("pinned", False),
            detector_affinity=affinities.get(e["detector"], 1.0),
        )}
        for e in collapsed
    ]
    scored.sort(key=lambda e: e["score"], reverse=True)
    top = scored[:MAX_DIGEST_ITEMS]
    other_count = max(0, len(scored) - len(top))

    # Naive comparison: same candidate pool, sorted by raw magnitude alone,
    # no recency/pin/affinity weighting — this is the "obvious" approach
    # the drawer contrasts against.
    naive_order = sorted(collapsed, key=lambda e: abs(e["sigma"]), reverse=True)
    naive_rank = {e["event_id"]: i + 1 for i, e in enumerate(naive_order)}

    items = [_format_item(e, latest_prices.get(e["symbol_id"]), naive_rank.get(e["event_id"])) for e in top]
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


def _format_item(e: dict, current_price_paise: int | None, naive_rank: int | None) -> dict:
    return {
        "event_id": e["event_id"], "ticker": e["ticker"], "name": e["name"],
        "pinned": e.get("pinned", False),
        "detector": e["detector"], "sigma": round(e["sigma"], 2),
        "current_price_paise": current_price_paise, "explanation": _explain(e),
        "ts": e["ts"].isoformat(),
        "score": round(e["score"], 3),
        "breakdown": {
            "magnitude": round(e["magnitude"], 3),
            "recency_decay": round(e["recency_decay"], 3),
            "pin_weight": e["pin_weight"],
            "affinity": round(e["affinity"], 3),
        },
        "naive_rank": naive_rank,
    }