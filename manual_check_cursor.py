"""One-off manual check — not part of the pytest suite."""
from datetime import datetime, timezone, timedelta

from app.db import SessionLocal
from app.models import Symbol, UserSymbolCursor, User
from app.cursor import mark_seen

db = SessionLocal()
try:
    user = db.query(User).first()
    symbol = db.query(Symbol).first()
    if user is None or symbol is None:
        raise SystemExit("Need at least one user and one symbol seeded first.")

    now = datetime.now(timezone.utc)
    earlier = now - timedelta(hours=1)
    later = now + timedelta(hours=1)

    mark_seen(db, user.id, symbol.id, event_ts=now, seen_at=now)
    db.commit()
    row = db.query(UserSymbolCursor).filter_by(user_id=user.id, symbol_id=symbol.id).first()
    print("After first mark:", row.last_seen_event_ts)

    mark_seen(db, user.id, symbol.id, event_ts=earlier, seen_at=now)  # older — must NOT move it back
    db.commit()
    db.refresh(row)
    print("After older mark (should be unchanged):", row.last_seen_event_ts)

    mark_seen(db, user.id, symbol.id, event_ts=later, seen_at=now)  # newer — must move it forward
    db.commit()
    db.refresh(row)
    print("After newer mark (should be later):", row.last_seen_event_ts)
finally:
    db.close()