from datetime import datetime, timezone, timedelta
from app.digest_core import assemble_digest


def _e(event_id, symbol_id, ticker, detector, ts, sigma, return_pct=None, pinned=False):
    return {
        "event_id": event_id, "symbol_id": symbol_id, "ticker": ticker, "name": ticker + " Ltd",
        "detector": detector, "ts": ts, "sigma": sigma,
        "payload": {"return_pct": return_pct if return_pct is not None else sigma},
        "pinned": pinned,
    }


NOW = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)


def test_empty_raw_events_is_quiet():
    result = assemble_digest([], min_sigma=2.0, now=NOW, latest_prices={})
    assert result["items"] == [] and result["empty_reason"] == "quiet"


def test_below_threshold_filtered_out():
    events = [_e(1, 1, "INFY", "SIGMA_MOVE", NOW, 1.6)]
    result = assemble_digest(events, min_sigma=2.0, now=NOW, latest_prices={})
    assert result["items"] == [] and result["empty_reason"] is None


def test_cooldown_collapse_applied_before_ranking():
    events = [
        _e(1, 1, "INFY", "SIGMA_MOVE", NOW, 1.6),
        _e(2, 1, "INFY", "SIGMA_MOVE", NOW + timedelta(minutes=20), 2.9),
    ]
    result = assemble_digest(events, min_sigma=1.5, now=NOW, latest_prices={})
    assert len(result["items"]) == 1 and result["items"][0]["sigma"] == 2.9


def test_higher_score_ranks_first():
    events = [_e(1, 1, "INFY", "SIGMA_MOVE", NOW, 2.0), _e(2, 2, "TCS", "SIGMA_MOVE", NOW, 4.0)]
    result = assemble_digest(events, min_sigma=1.5, now=NOW, latest_prices={})
    assert result["items"][0]["ticker"] == "TCS"


def test_caps_at_five_and_counts_the_rest():
    events = [_e(i, i, f"SYM{i}", "SIGMA_MOVE", NOW, 2.0 + i * 0.1) for i in range(7)]
    result = assemble_digest(events, min_sigma=1.5, now=NOW, latest_prices={})
    assert len(result["items"]) == 5 and result["other_count"] == 2


def test_format_includes_price_and_explanation():
    events = [_e(1, 1, "INFY", "SIGMA_MOVE", NOW, 2.7, return_pct=3.1)]
    result = assemble_digest(events, min_sigma=1.5, now=NOW, latest_prices={1: 150000})
    item = result["items"][0]
    assert item["current_price_paise"] == 150000 and "3.1%" in item["explanation"]