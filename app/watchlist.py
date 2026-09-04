from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, update, delete
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


class WatchlistListItemOut(BaseModel):
    id: int
    ticker: str
    name: str
    pinned: bool
    position: int
    version: int


class PinRequest(BaseModel):
    pinned: bool
    version: int


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


@router.get("", response_model=list[WatchlistListItemOut])
def list_watchlist(user: User = Depends(get_current_user), db=Depends(get_db)):
    rows = (
        db.query(WatchlistItem, Symbol)
        .join(Symbol, Symbol.id == WatchlistItem.symbol_id)
        .filter(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.pinned.desc(), WatchlistItem.position.asc())
        .all()
    )
    return [
        WatchlistListItemOut(
            id=w.id, ticker=s.ticker, name=s.name,
            pinned=w.pinned, position=w.position, version=w.version,
        )
        for w, s in rows
    ]


@router.patch("/{item_id}", response_model=WatchlistListItemOut)
def toggle_pin(
    item_id: int,
    payload: PinRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    stmt = (
        update(WatchlistItem)
        .where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user.id,
            WatchlistItem.version == payload.version,
        )
        .values(pinned=payload.pinned, version=WatchlistItem.version + 1)
        .returning(WatchlistItem.id, WatchlistItem.pinned,
                   WatchlistItem.position, WatchlistItem.version)
    )
    result = db.execute(stmt).first()
    if result is None:
        exists = db.query(WatchlistItem).filter_by(id=item_id, user_id=user.id).first()
        if exists is None:
            raise HTTPException(status_code=404, detail="Not found")
        raise HTTPException(status_code=409, detail="Item was changed elsewhere, refresh and retry")

    db.commit()
    s = (
        db.query(Symbol)
        .join(WatchlistItem, WatchlistItem.symbol_id == Symbol.id)
        .filter(WatchlistItem.id == item_id)
        .first()
    )
    return WatchlistListItemOut(
        id=result.id, ticker=s.ticker, name=s.name,
        pinned=result.pinned, position=result.position, version=result.version,
    )


@router.delete("/{item_id}", status_code=204)
def remove_from_watchlist(
    item_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    item = db.query(WatchlistItem).filter_by(id=item_id, user_id=user.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")

    db.execute(
        delete(UserSymbolCursor).where(
            UserSymbolCursor.user_id == user.id,
            UserSymbolCursor.symbol_id == item.symbol_id,
        )
    )
    db.delete(item)
    db.commit()