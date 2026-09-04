from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth import get_current_user
from app.db import get_db
from app.models import Event, User, UserEventState
from app.signals.dedupe import build_dedupe_key

router = APIRouter(prefix="/api/events", tags=["events"])


def persist_event(db, symbol_id: int, ticker: str, detector_result: dict, ts: datetime) -> None:
    dedupe_key = build_dedupe_key(ticker, detector_result["detector"], ts)
    stmt = pg_insert(Event).values(
        symbol_id=symbol_id,
        detector=detector_result["detector"],
        ts=ts,
        sigma=detector_result["sigma"],
        payload=detector_result,
        dedupe_key=dedupe_key,
    ).on_conflict_do_nothing(index_elements=["dedupe_key"])
    db.execute(stmt)


@router.post("/{event_id}/dismiss", status_code=204)
def dismiss_event(event_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    if db.query(Event).filter_by(id=event_id).first() is None:
        raise HTTPException(status_code=404, detail="Event not found")

    now = datetime.now(timezone.utc)
    stmt = pg_insert(UserEventState).values(
        user_id=user.id, event_id=event_id, shown_at=now, dismissed_at=now,
    ).on_conflict_do_update(
        index_elements=["user_id", "event_id"],
        set_={"dismissed_at": now},
    )
    db.execute(stmt)
    db.commit()