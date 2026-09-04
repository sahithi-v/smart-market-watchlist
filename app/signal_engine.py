from app.db import SessionLocal
from app.events import persist_event
from app.ingest import build_symbol_context
from app.models import PriceTick, Symbol
from app.signals.detectors import detect_sigma_move, detect_volume_spike


def run_signal_engine():
    db = SessionLocal()
    try:
        context = build_symbol_context(db)

        for symbol in db.query(Symbol).all():
            ctx = context.get(symbol.ticker)
            if ctx is None:
                continue

            latest_tick = (
                db.query(PriceTick)
                .filter_by(symbol_id=symbol.id)
                .order_by(PriceTick.ts.desc())
                .first()
            )
            if latest_tick is None:
                continue

            sigma_result = detect_sigma_move(
                current_price_paise=latest_tick.ltp_paise,
                prev_close_paise=ctx["last_close_paise"],
                mean_return=ctx["mean_return"],
                stddev_return=ctx["daily_stddev"],
            )
            if sigma_result is not None:
                persist_event(db, symbol.id, symbol.ticker, sigma_result, latest_tick.ts)

            volume_result = detect_volume_spike(
                current_volume=latest_tick.volume,
                avg_volume_20d=ctx["avg_volume_20d"],
            )
            if volume_result is not None:
                persist_event(db, symbol.id, symbol.ticker, volume_result, latest_tick.ts)

        db.commit()
    finally:
        db.close()