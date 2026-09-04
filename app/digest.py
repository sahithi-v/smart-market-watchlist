from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_

from app.auth import get_current_user
from app.db import get_db
from app.digest_core import assemble_digest
from app.models import Event, PriceTick, Symbol, User, UserSettings, UserSymbolCursor, WatchlistItem
from app.signals.presets import DEFAULT_SENSITIVITY, resolve_min_sigma

router = APIRouter(prefix="/api", tags=["digest"])


def get_watchlist_symbol_ids(db, user_id: int) -> set[int]:
    return {w.symbol_id for w in db.query(WatchlistItem).filter_by(user_id=user_id).all()}


def get_user_min_sigma(db, user_id: int) -> float:
    row = db.query(UserSettings).filter_by(user_id=user_id).first()
    sensitivity = row.sensitivity if row else DEFAULT_SENSITIVITY
    override = float(row.min_sigma) if row and row.min_sigma is not None else None
    return resolve_min_sigma(sensitivity, override)
def get_unseen_events(db, user_id: int) -> list[dict]:
    """watchlist -> cursor -> events newer than that symbol's cursor.
    No filtering/scoring here — assemble_digest does that on plain dicts."""
    rows = (
        db.query(Event, Symbol, WatchlistItem)
        .join(Symbol, Symbol.id == Event.symbol_id)
        .join(WatchlistItem, WatchlistItem.symbol_id == Symbol.id)
        .join(
            UserSymbolCursor,
            and_(
                UserSymbolCursor.symbol_id == Symbol.id,
                UserSymbolCursor.user_id == WatchlistItem.user_id,
            ),
        )
        .filter(WatchlistItem.user_id == user_id)
        .filter(Event.ts > UserSymbolCursor.last_seen_event_ts)
        .all()
    )
    return [
        {
            "event_id": event.id, "symbol_id": symbol.id, "ticker": symbol.ticker,
            "name": symbol.name, "detector": event.detector, "ts": event.ts,
            "sigma": float(event.sigma), "payload": event.payload, "pinned": item.pinned,
        }
        for event, symbol, item in rows
    ]


def get_latest_prices(db, symbol_ids: set[int]) -> dict[int, int]:
    prices = {}
    for sid in symbol_ids:
        tick = db.query(PriceTick).filter_by(symbol_id=sid).order_by(PriceTick.ts.desc()).first()
        if tick:
            prices[sid] = tick.ltp_paise
    return prices
def build_digest(db, user: User, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)

    watchlist_ids = get_watchlist_symbol_ids(db, user.id)
    if not watchlist_ids:
        return {"items": [], "other_count": 0, "empty_reason": "no_watchlist"}

    min_sigma = get_user_min_sigma(db, user.id)
    raw_events = get_unseen_events(db, user.id)
    latest_prices = get_latest_prices(db, {e["symbol_id"] for e in raw_events})

    return assemble_digest(raw_events, min_sigma=min_sigma, now=now, latest_prices=latest_prices)


@router.get("/digest")
def digest(user: User = Depends(get_current_user), db=Depends(get_db)):
    return build_digest(db, user)
