from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Quote:
    ticker: str
    ltp_paise: int
    volume: int
    ts: datetime       # exchange timestamp, timezone-aware
    source: str         # e.g. "simulated", "yfinance"


class MarketDataProvider(Protocol):
    def fetch_quotes(self, tickers: list[str]) -> list[Quote]: ...