from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import UserSymbolCursor


def mark_seen(db, user_id: int, symbol_id: int, event_ts: datetime, seen_at: datetime) -> None:
    """Advance the cursor to at least event_ts. Monotonic — never moves
    backward. GREATEST() runs inside the UPDATE itself, not in Python."""
    stmt = pg_insert(UserSymbolCursor).values(
        user_id=user_id,
        symbol_id=symbol_id,
        last_seen_event_ts=event_ts,
        last_seen_at=seen_at,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "symbol_id"],
        set_={
            "last_seen_event_ts": func.greatest(
                UserSymbolCursor.last_seen_event_ts, stmt.excluded.last_seen_event_ts
            ),
            "last_seen_at": func.greatest(
                UserSymbolCursor.last_seen_at, stmt.excluded.last_seen_at
            ),
        },
    )
    db.execute(stmt)