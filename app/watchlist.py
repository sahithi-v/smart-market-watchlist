from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth import get_current_user
from app.db import get_db
from app.models import Symbol, User, UserSymbolCursor, WatchlistItem

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddToWatchlistRequest(BaseModel):
    ticker: str


class WatchlistItemOut(BaseModel):
    id: int
    ticker: str
    name: str
    added_at: datetime
    pinned: bool
    position: int


@router.post("", response_model=WatchlistItemOut, status_code=201)
def add_to_watchlist(
    payload: AddToWatchlistRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    symbol = db.query(Symbol).filter_by(ticker=payload.ticker.upper()).first()
    if symbol is None:
        raise HTTPException(status_code=404, detail=f"Unknown ticker: {payload.ticker}")

    next_position = (
        db.query(func.coalesce(func.max(WatchlistItem.position), 0))
        .filter_by(user_id=user.id)
        .scalar()
    ) + 1
    now = datetime.now(timezone.utc)

    stmt = (
        pg_insert(WatchlistItem)
        .values(user_id=user.id, symbol_id=symbol.id, position=next_position)
        .on_conflict_do_nothing(index_elements=["user_id", "symbol_id"])
        .returning(
            WatchlistItem.id, WatchlistItem.added_at,
            WatchlistItem.pinned, WatchlistItem.position,
        )
    )
    result = db.execute(stmt).first()
    if result is None:
        raise HTTPException(status_code=400, detail="Already on watchlist")

    # Cursor starts at "now", not the symbol's history — added mid-session
    # must not surface last week's events on the first digest.
    cursor_stmt = pg_insert(UserSymbolCursor).values(
        user_id=user.id, symbol_id=symbol.id, last_seen_event_ts=now, last_seen_at=now,
    ).on_conflict_do_nothing(index_elements=["user_id", "symbol_id"])
    db.execute(cursor_stmt)

    db.commit()

    return WatchlistItemOut(
        id=result.id, ticker=symbol.ticker, name=symbol.name,
        added_at=result.added_at, pinned=result.pinned, position=result.position,
    )