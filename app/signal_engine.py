from app.db import SessionLocal
from app.events import persist_event
from app.ingest import build_symbol_context
from app.models import PriceTick, Symbol
from app.signals.detectors import detect_sigma_move


def run_signal_engine():
    """Runs on a schedule. For each symbol with a baseline, checks the
    latest tick against it and persists an event if it qualifies. No
    cooldown here — every qualifying event is stored; suppression happens
    at digest read time."""
    db = SessionLocal()
    try:
        context = build_symbol_context(db)

        for symbol in db.query(Symbol).all():
            ctx = context.get(symbol.ticker)
            if ctx is None:
                continue  # too new — no symbol_stats/daily_bars baseline yet

            latest_tick = (
                db.query(PriceTick)
                .filter_by(symbol_id=symbol.id)
                .order_by(PriceTick.ts.desc())
                .first()
            )
            if latest_tick is None:
                continue

            result = detect_sigma_move(
                current_price_paise=latest_tick.ltp_paise,
                prev_close_paise=ctx["last_close_paise"],
                mean_return=ctx["mean_return"],
                stddev_return=ctx["daily_stddev"],
            )
            if result is not None:
                persist_event(db, symbol.id, symbol.ticker, result, latest_tick.ts)

        db.commit()
    finally:
        db.close()