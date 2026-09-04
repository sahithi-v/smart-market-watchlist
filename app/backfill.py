import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models import DailyBar

def fetch_daily_bars(ticker: str, period: str = "6mo"):
    hist = yf.download(f"{ticker}.NS", period=period, interval="1d", progress=False)
    hist.columns = hist.columns.get_level_values(0)  # drop the ticker sub-level
    return hist




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