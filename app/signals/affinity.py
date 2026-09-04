def compute_affinity(shown_count: int, dismissed_count: int, min_signals: int = 5) -> float:
    """Pure function: no DB. Cold start: defaults to 1.0 until at least
    min_signals events of this detector have been shown — not enough data
    to trust a ratio from 1-2 signals. Once past cold start, clamped to
    [0.3, 1.0] — a user who dismisses everything of a type still gets
    some through; zero would be indistinguishable from a bug to them.
    """
    if shown_count < min_signals:
        return 1.0
    raw = 1.0 - (dismissed_count / shown_count)
    return max(0.3, min(1.0, raw))