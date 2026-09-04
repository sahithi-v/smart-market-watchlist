import pandas as pd


def compute_symbol_stats(bars: pd.DataFrame) -> dict:
    """bars: columns date, close_paise, high_paise, low_paise, volume — ascending by date."""
    bars = bars.sort_values("date")
    returns = bars["close_paise"].pct_change().dropna()

    return {
        "as_of": bars["date"].iloc[-1],
        "mean_return": float(returns.tail(30).mean()),
        "stddev_return": float(returns.tail(30).std()),
        "avg_volume_20d": int(bars["volume"].tail(20).mean()),
        "high_20d": int(bars["high_paise"].tail(20).max()),
        "low_20d": int(bars["low_paise"].tail(20).min()),
    }