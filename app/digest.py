from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth import get_current_user
from app.db import get_db
from app.digest_core import assemble_digest
from app.models import Event, PriceTick, Symbol, User, UserEventState, UserSettings, UserSymbolCursor, WatchlistItem
from app.signals.affinity import compute_affinity
from app.signals.presets import DEFAULT_SENSITIVITY, resolve_thresholds

router = APIRouter(prefix="/api", tags=["digest"])


def get_watchlist_symbol_ids(db, user_id: int) -> set[int]:
    return {w.symbol_id for w in db.query(WatchlistItem).filter_by(user_id=user_id).all()}


def get_user_thresholds(db, user_id: int) -> tuple[dict[str, float], set[str]]:
    row = db.query(UserSettings).filter_by(user_id=user_id).first()
    sensitivity = row.sensitivity if row else DEFAULT_SENSITIVITY
    override = float(row.min_sigma) if row and row.min_sigma is not None else None
    detectors_override = row.detectors_enabled if row and row.detectors_enabled else None
    return resolve_thresholds(sensitivity, override, detectors_override)


def get_detector_affinities(db, user_id: int) -> dict[str, float]:
    """One query, all detectors at once."""
    rows = (
        db.query(
            Event.detector,
            func.count(UserEventState.event_id).label("shown_count"),
            func.count(UserEventState.dismissed_at).label("dismissed_count"),
        )
        .join(UserEventState, UserEventState.event_id == Event.id)
        .filter(UserEventState.user_id == user_id, UserEventState.shown_at.isnot(None))
        .group_by(Event.detector)
        .all()
    )
    return {detector: compute_affinity(shown, dismissed) for detector, shown, dismissed in rows}


def get_unseen_events(db, user_id: int) -> list[dict]:
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
        .outerjoin(
            UserEventState,
            and_(
                UserEventState.event_id == Event.id,
                UserEventState.user_id == user_id,
            ),
        )
        .filter(WatchlistItem.user_id == user_id)
        .filter(Event.ts > UserSymbolCursor.last_seen_event_ts)
        .filter(UserEventState.dismissed_at.is_(None))
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


def record_shown(db, user_id: int, event_ids: list[int]) -> None:
    """First-shown-wins — never overwrites an existing dismissed_at."""
    now = datetime.now(timezone.utc)
    for event_id in event_ids:
        stmt = pg_insert(UserEventState).values(
            user_id=user_id, event_id=event_id, shown_at=now,
        ).on_conflict_do_nothing(index_elements=["user_id", "event_id"])
        db.execute(stmt)


def build_digest(db, user: User, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)

    watchlist_ids = get_watchlist_symbol_ids(db, user.id)
    if not watchlist_ids:
        return {"items": [], "other_count": 0, "empty_reason": "no_watchlist"}

    thresholds, enabled_detectors = get_user_thresholds(db, user.id)
    raw_events = get_unseen_events(db, user.id)
    latest_prices = get_latest_prices(db, {e["symbol_id"] for e in raw_events})
    affinities = get_detector_affinities(db, user.id)

    result = assemble_digest(raw_events, thresholds, enabled_detectors, now, latest_prices, affinities)

    if result["items"]:
        record_shown(db, user.id, [item["event_id"] for item in result["items"]])
        db.commit()

    return result


@router.get("/digest")
def digest(user: User = Depends(get_current_user), db=Depends(get_db)):
    return build_digest(db, user)