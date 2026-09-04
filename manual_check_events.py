"""One-off manual check — not part of the pytest suite. Run once, then
either delete this or leave it as a debug tool; either is fine."""
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import Symbol, Event
from app.events import persist_event

db = SessionLocal()
try:
    symbol = db.query(Symbol).first()
    if symbol is None:
        raise SystemExit("No symbols found — run app/seed.py first.")

    result = {"detector": "SIGMA_MOVE", "sigma": 2.7, "return_pct": 3.1}
    ts = datetime.now(timezone.utc)

    persist_event(db, symbol.id, symbol.ticker, result, ts)
    db.commit()
    row = db.query(Event).order_by(Event.id.desc()).first()
    print("Inserted:", row.id, row.detector, row.sigma, row.dedupe_key)

    persist_event(db, symbol.id, symbol.ticker, result, ts)  # same ts again
    db.commit()
    count = db.query(Event).filter_by(dedupe_key=row.dedupe_key).count()
    print("Row count after duplicate attempt:", count, "(expect 1)")
finally:
    db.close()