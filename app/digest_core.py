from datetime import datetime

from app.signals.cooldown import collapse_cooldown_groups
from app.signals.scoring import score_event

MAX_DIGEST_ITEMS = 5
COOLDOWN_HOURS = 4.0


def assemble_digest(
    raw_events: list[dict],
    min_sigma: float,
    now: datetime,
    latest_prices: dict[int, int],
) -> dict:
    """Pure function: no DB. Filters by the user's resolved sensitivity
    threshold, collapses cooldown groups, scores, ranks, caps at
    MAX_DIGEST_ITEMS."""
    above_threshold = [e for e in raw_events if abs(e["sigma"]) >= min_sigma]
    collapsed = collapse_cooldown_groups(above_threshold, cooldown_hours=COOLDOWN_HOURS)

    scored = [
        {**e, "score": score_event(e["sigma"], e["ts"], now, pinned=e.get("pinned", False))}
        for e in collapsed
    ]
    scored.sort(key=lambda e: e["score"], reverse=True)

    top = scored[:MAX_DIGEST_ITEMS]
    other_count = max(0, len(scored) - len(top))
    items = [_format_item(e, latest_prices.get(e["symbol_id"])) for e in top]
    empty_reason = "quiet" if not raw_events else None

    return {"items": items, "other_count": other_count, "empty_reason": empty_reason}


def _format_item(e: dict, current_price_paise: int | None) -> dict:
    return_pct = e["payload"].get("return_pct")
    explanation = f"Moved {return_pct:+.1f}% ({e['sigma']:+.1f}\u03c3 vs its 30-day volatility)."
    return {
        "event_id": e["event_id"], "ticker": e["ticker"], "name": e["name"],
        "detector": e["detector"], "sigma": round(e["sigma"], 2),
        "current_price_paise": current_price_paise, "explanation": explanation,
        "ts": e["ts"].isoformat(),
    }