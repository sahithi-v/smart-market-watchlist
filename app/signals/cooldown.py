from collections import defaultdict
from datetime import timedelta


def collapse_cooldown_groups(events: list[dict], cooldown_hours: float = 4.0) -> list[dict]:
    """Pure function. Groups events sharing (symbol_id, detector), sorted
    by ts, into non-overlapping cooldown-hour windows — each anchored to
    its first event — and keeps only the highest-magnitude event per
    window. Read-time suppression: every qualifying event is stored, this
    just decides which ones a digest shows.
    """
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for e in events:
        by_key[(e["symbol_id"], e["detector"])].append(e)

    window = timedelta(hours=cooldown_hours)
    collapsed = []

    for group in by_key.values():
        group.sort(key=lambda e: e["ts"])
        current_window: list[dict] = []
        anchor_ts = None

        for e in group:
            if anchor_ts is None or e["ts"] - anchor_ts > window:
                if current_window:
                    collapsed.append(max(current_window, key=lambda x: abs(x["sigma"])))
                current_window = [e]
                anchor_ts = e["ts"]
            else:
                current_window.append(e)

        if current_window:
            collapsed.append(max(current_window, key=lambda x: abs(x["sigma"])))

    return collapsed