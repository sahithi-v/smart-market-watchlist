from datetime import datetime, timezone


def build_dedupe_key(ticker: str, detector: str, ts: datetime) -> str:
    """Minute-bucketed dedupe key, e.g. 'INFY:SIGMA_MOVE:2026-09-04T11:15'."""
    if ts.tzinfo is None:
        raise ValueError("ts must be timezone-aware — see DECISIONS.md on TIMESTAMPTZ")

    bucket = ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    return f"{ticker}:{detector}:{bucket}"