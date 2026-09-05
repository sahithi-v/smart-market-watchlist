"""One-off backfill: fetch real historical daily bars via yfinance for
every symbol in the DB, so build_symbol_context() has real seed data for
ALL watchlist-addable symbols, not just the ones with a manually loaded
CSV. Real data only — no fabricated numbers. Safe to re-run: existing
rows are skipped via ON CONFLICT DO NOTHING."""
import math
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db import SessionLocal
from app.models import Symbol, DailyBar


def run():
    db = SessionLocal()
    try:
        symbols = db.query(Symbol).all()
        for symbol in symbols:
            print(f"Backfilling {symbol.ticker}...")
            try:
                hist = yf.Ticker(f"{symbol.ticker}.NS").history(period="200d")
            except Exception as e:
                print(f"  skipped ({e})")
                continue
            if hist.empty:
                print("  no data returned")
                continue
            skipped_rows = 0
            for date, row in hist.iterrows():
                if any(math.isnan(row[col]) for col in ["Open", "High", "Low", "Close", "Volume"]):
                    skipped_rows += 1
                    continue
                stmt = pg_insert(DailyBar).values(
                    symbol_id=symbol.id,
                    date=date.date(),
                    open_paise=round(row["Open"] * 100),
                    high_paise=round(row["High"] * 100),
                    low_paise=round(row["Low"] * 100),
                    close_paise=round(row["Close"] * 100),
                    volume=int(row["Volume"]),
                ).on_conflict_do_nothing(index_elements=["symbol_id", "date"])
                db.execute(stmt)
            db.commit()
            print(f"  done: {len(hist) - skipped_rows} bars ({skipped_rows} skipped for bad data)")
    finally:
        db.close()


if __name__ == "__main__":
    run()