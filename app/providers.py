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

import random
from datetime import datetime, timezone


class SimulatedProvider:
    """Deterministic seeded random walk. Same seed -> same price path, every run."""

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._rngs: dict[str, random.Random] = {}
        self._last_price: dict[str, int] = {}
        self._last_volume: dict[str, int] = {}

    def _rng_for(self, ticker: str) -> random.Random:
        if ticker not in self._rngs:
            self._rngs[ticker] = random.Random(f"{self._seed}:{ticker}")
            self._last_price[ticker] = self._rngs[ticker].randint(10_000, 500_000)
            self._last_volume[ticker] = self._rngs[ticker].randint(50_000, 500_000)
        return self._rngs[ticker]

    def fetch_quotes(self, tickers: list[str]) -> list[Quote]:
        now = datetime.now(timezone.utc)
        quotes = []
        for ticker in tickers:
            rng = self._rng_for(ticker)
            ret = rng.gauss(0, 0.004)
            price = max(100, int(self._last_price[ticker] * (1 + ret)))
            vol = max(1, int(self._last_volume[ticker] * rng.uniform(0.7, 1.4)))
            self._last_price[ticker] = price
            self._last_volume[ticker] = vol
            quotes.append(Quote(ticker, price, vol, now, "simulated"))
        return quotes