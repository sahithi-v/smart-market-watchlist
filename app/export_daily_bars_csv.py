import csv
from pathlib import Path

from app.db import SessionLocal
from app.models import DailyBar, Symbol

OUT_PATH = Path(__file__).parent.parent / "data" / "daily_bars_seed.csv"


def export():
    db = SessionLocal()
    try:
        OUT_PATH.parent.mkdir(exist_ok=True)
        rows = (
            db.query(Symbol.ticker, DailyBar.date, DailyBar.open_paise,
                     DailyBar.high_paise, DailyBar.low_paise,
                     DailyBar.close_paise, DailyBar.volume)
            .join(DailyBar, DailyBar.symbol_id == Symbol.id)
            .order_by(Symbol.ticker, DailyBar.date)
            .all()
        )
        with open(OUT_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"])
            for ticker, date, o, h, l, c, v in rows:
                writer.writerow([ticker, date, o / 100, h / 100, l / 100, c / 100, v])
    finally:
        db.close()


if __name__ == "__main__":
    export()