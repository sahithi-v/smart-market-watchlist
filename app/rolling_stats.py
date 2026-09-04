import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import Symbol, DailyBar, SymbolStats
from app.stats import compute_symbol_stats


def run_rolling_stats():
    db = SessionLocal()
    try:
        for symbol in db.query(Symbol).all():
            bars = (
                db.query(DailyBar.date, DailyBar.close_paise, DailyBar.high_paise,
                         DailyBar.low_paise, DailyBar.volume)
                .filter(DailyBar.symbol_id == symbol.id)
                .all()
            )
            if len(bars) < 2:
                continue
            df = pd.DataFrame(bars, columns=["date", "close_paise", "high_paise", "low_paise", "volume"])
            stats = compute_symbol_stats(df)

            stmt = pg_insert(SymbolStats).values(symbol_id=symbol.id, **stats)
            stmt = stmt.on_conflict_do_update(index_elements=["symbol_id"], set_=stats)
            db.execute(stmt)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_rolling_stats()