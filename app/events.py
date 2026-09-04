from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import Event
from app.signals.dedupe import build_dedupe_key


def persist_event(db, symbol_id: int, ticker: str, detector_result: dict, ts: datetime) -> None:
    """Insert one event row. Caller commits — same pattern as run_ingest,
    one commit per batch, not per row."""
    dedupe_key = build_dedupe_key(ticker, detector_result["detector"], ts)
    stmt = pg_insert(Event).values(
        symbol_id=symbol_id,
        detector=detector_result["detector"],
        ts=ts,
        sigma=detector_result["sigma"],
        payload=detector_result,
        dedupe_key=dedupe_key,
    ).on_conflict_do_nothing(index_elements=["dedupe_key"])
    db.execute(stmt)