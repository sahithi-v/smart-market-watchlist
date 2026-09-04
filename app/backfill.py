from pathlib import Path

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import DailyBar

CSV_PATH = Path(__file__).parent.parent / "data" / "daily_bars_seed.csv"


def fetch_daily_bars(ticker: str, period: str = "6mo"):
    try:
        hist = yf.download(f"{ticker}.NS", period=period, interval="1d", progress=False)
        if hist.empty:
            raise ValueError("empty response")
        hist.columns = hist.columns.get_level_values(0)
        return hist
    except Exception as e:
        print(f"{ticker}: yfinance failed ({e}), falling back to CSV")
        df = pd.read_csv(CSV_PATH, parse_dates=["Date"])
        df = df[df["Ticker"] == ticker].set_index("Date")
        return df[["Open", "High", "Low", "Close", "Volume"]]
    
def write_daily_bars(db, symbol_id: int, hist):
    for date, row in hist.iterrows():
        stmt = pg_insert(DailyBar).values(
            symbol_id=symbol_id,
            date=date.date(),
            open_paise=round(row["Open"] * 100),
            high_paise=round(row["High"] * 100),
            low_paise=round(row["Low"] * 100),
            close_paise=round(row["Close"] * 100),
            volume=int(row["Volume"]),
        ).on_conflict_do_nothing(index_elements=["symbol_id", "date"])
        db.execute(stmt)