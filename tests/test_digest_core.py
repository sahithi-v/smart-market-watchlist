from datetime import datetime, timezone, timedelta
from app.digest_core import assemble_digest

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
SIGMA_THRESHOLDS = {"SIGMA_MOVE": 1.5, "VOLUME_SPIKE": 2.0}
ALL_DETECTORS = {"SIGMA_MOVE", "VOLUME_SPIKE"}


def _sigma_e(event_id, symbol_id, ticker, ts, sigma, return_pct=None, pinned=False):
    return {
        "event_id": event_id, "symbol_id": symbol_id, "ticker": ticker, "name": ticker + " Ltd",
        "detector": "SIGMA_MOVE", "ts": ts, "sigma": sigma,
        "payload": {"return_pct": return_pct if return_pct is not None else sigma},
        "pinned": pinned,
    }


def _vol_e(event_id, symbol_id, ticker, ts, multiple, pinned=False):
    return {
        "event_id": event_id, "symbol_id": symbol_id, "ticker": ticker, "name": ticker + " Ltd",
        "detector": "VOLUME_SPIKE", "ts": ts, "sigma": multiple,
        "payload": {"volume_multiple": multiple}, "pinned": pinned,
    }


def test_empty_raw_events_is_quiet():
    result = assemble_digest([], SIGMA_THRESHOLDS, ALL_DETECTORS, NOW, {})
    assert result["items"] == [] and result["empty_reason"] == "quiet"


def test_below_threshold_filtered_out():
    events = [_sigma_e(1, 1, "INFY", NOW, 1.2)]
    result = assemble_digest(events, SIGMA_THRESHOLDS, ALL_DETECTORS, NOW, {})
    assert result["items"] == [] and result["empty_reason"] is None


def test_disabled_detector_excluded_even_if_magnitude_qualifies():
    events = [_vol_e(1, 1, "INFY", NOW, 3.0)]
    result = assemble_digest(events, SIGMA_THRESHOLDS, {"SIGMA_MOVE"}, NOW, {})
    assert result["items"] == []


def test_volume_spike_gets_its_own_explanation():
    events = [_vol_e(1, 1, "INFY", NOW, 3.4)]
    result = assemble_digest(events, SIGMA_THRESHOLDS, ALL_DETECTORS, NOW, {})
    assert "average volume" in result["items"][0]["explanation"]


def test_sigma_and_volume_events_both_rank_together():
    events = [_sigma_e(1, 1, "INFY", NOW, 2.0), _vol_e(2, 2, "TCS", NOW, 4.0)]
    result = assemble_digest(events, SIGMA_THRESHOLDS, ALL_DETECTORS, NOW, {})
    assert result["items"][0]["ticker"] == "TCS"


def test_caps_at_five_and_counts_the_rest():
    events = [_sigma_e(i, i, f"SYM{i}", NOW, 2.0 + i * 0.1) for i in range(7)]
    result = assemble_digest(events, SIGMA_THRESHOLDS, ALL_DETECTORS, NOW, {})
    assert len(result["items"]) == 5 and result["other_count"] == 2
def test_low_affinity_detector_ranks_below_high_affinity_one():
    events = [_sigma_e(1, 1, "INFY", NOW, 2.0), _vol_e(2, 2, "TCS", NOW, 2.0)]
    result = assemble_digest(
        events, SIGMA_THRESHOLDS, ALL_DETECTORS, NOW, {},
        affinities={"SIGMA_MOVE": 1.0, "VOLUME_SPIKE": 0.3},
    )
    assert result["items"][0]["ticker"] == "INFY"