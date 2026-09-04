from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import Symbol, PriceTick, SymbolStats, DailyBar
from app.providers import SimulatedProvider, YFinanceProvider, CircuitBreakerProvider

_provider = None


def build_symbol_context(db) -> dict[str, dict]:
    """Real last close, mean return, and daily volatility per symbol.
    Used to seed the fallback provider AND as detector input in the
    signal engine — same underlying data, one query loop, not two."""
    context = {}
    for symbol in db.query(Symbol).all():
        stats = db.query(SymbolStats).filter_by(symbol_id=symbol.id).first()
        last_bar = (
            db.query(DailyBar).filter_by(symbol_id=symbol.id)
            .order_by(DailyBar.date.desc()).first()
        )
        if stats and last_bar:
            context[symbol.ticker] = {
                "last_close_paise": last_bar.close_paise,
                "mean_return": float(stats.mean_return),
                "daily_stddev": float(stats.stddev_return),
            }
    return context


def get_provider(db):
    global _provider
    if _provider is None:
        seed_data = build_seed_data(db)
        _provider = CircuitBreakerProvider(
            primary=YFinanceProvider(),
            fallback=SimulatedProvider(seed_data=seed_data),
        )
    return _provider


def run_ingest():
    db = SessionLocal()
    try:
        provider = get_provider(db)
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