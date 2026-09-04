from app.db import SessionLocal
from app.models import Symbol
from app.backfill import fetch_daily_bars, write_daily_bars


def backfill_all():
    db = SessionLocal()
    try:
        symbols = db.query(Symbol).all()
        for s in symbols:
            hist = fetch_daily_bars(s.ticker)
            write_daily_bars(db, s.id, hist)
            db.commit()
            print(f"{s.ticker}: {len(hist)} bars")
    finally:
        db.close()


if __name__ == "__main__":
    backfill_all()