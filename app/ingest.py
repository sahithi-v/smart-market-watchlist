from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import Symbol, PriceTick
from app.providers import SimulatedProvider

provider = SimulatedProvider()


def run_ingest():
    db = SessionLocal()
    try:
        symbols = db.query(Symbol).all()
        ticker_to_id = {s.ticker: s.id for s in symbols}
        quotes = provider.fetch_quotes(list(ticker_to_id.keys()))

        for q in quotes:
            stmt = pg_insert(PriceTick).values(
                symbol_id=ticker_to_id[q.ticker],
                ts=q.ts,
                ltp_paise=q.ltp_paise,
                volume=q.volume,
                source=q.source,
            ).on_conflict_do_nothing(index_elements=["symbol_id", "ts"])
            db.execute(stmt)

        db.commit()
    finally:
        db.close()