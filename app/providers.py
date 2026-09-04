from dataclasses import dataclass
import yfinance as yf
from datetime import datetime
from typing import Protocol
import random 
from datetime import datetime, timezone

@dataclass(frozen=True)
class Quote:
    ticker: str
    ltp_paise: int
    volume: int
    ts: datetime       # exchange timestamp, timezone-aware
    source: str         # e.g. "simulated", "yfinance"


class MarketDataProvider(Protocol):
    def fetch_quotes(self, tickers: list[str]) -> list[Quote]: ...



class SimulatedProvider:
    DEMO_SESSION_TICKS = 20  # ~5 min of ticks treated as one visible demo "arc"

    def __init__(self, seed: int = 42, seed_data: dict[str, dict] | None = None):
        self._seed = seed
        self._seed_data = seed_data or {}
        self._rngs: dict[str, random.Random] = {}
        self._last_price: dict[str, int] = {}
        self._last_volume: dict[str, int] = {}
        self._tick_std: dict[str, float] = {}

    def _rng_for(self, ticker: str) -> random.Random:
        if ticker not in self._rngs:
            rng = random.Random(f"{self._seed}:{ticker}")
            self._rngs[ticker] = rng
            real = self._seed_data.get(ticker)
            if real:
                self._last_price[ticker] = real["last_close_paise"]
                self._tick_std[ticker] = real["daily_stddev"] / (self.DEMO_SESSION_TICKS ** 0.5)
            else:
                self._last_price[ticker] = rng.randint(10_000, 500_000)
                self._tick_std[ticker] = 0.004
            self._last_volume[ticker] = rng.randint(50_000, 500_000)
        return self._rngs[ticker]

    def fetch_quotes(self, tickers: list[str]) -> list[Quote]:
        now = datetime.now(timezone.utc)
        quotes = []
        for ticker in tickers:
            rng = self._rng_for(ticker)
            ret = rng.gauss(0, self._tick_std[ticker])
            price = max(100, int(self._last_price[ticker] * (1 + ret)))
            vol = max(1, int(self._last_volume[ticker] * rng.uniform(0.7, 1.4)))
            self._last_price[ticker] = price
            self._last_volume[ticker] = vol
            quotes.append(Quote(ticker, price, vol, now, "simulated"))
        return quotes
from datetime import timedelta


class YFinanceProvider:
    """Real live quotes. Skips individual failed tickers; raises only if all fail."""

    def fetch_quotes(self, tickers: list[str]) -> list[Quote]:
        now = datetime.now(timezone.utc)
        quotes = []
        for ticker in tickers:
            try:
                info = yf.Ticker(f"{ticker}.NS").fast_info
                quotes.append(Quote(ticker, round(info["lastPrice"] * 100),
                                     int(info["lastVolume"]), now, "yfinance"))
            except Exception:
                continue
        if not quotes:
            raise RuntimeError("YFinanceProvider: no quotes for any ticker")
        return quotes


class CircuitBreakerProvider:
    def __init__(self, primary, fallback, failure_threshold: int = 3, reset_seconds: int = 60):
        self._primary = primary
        self._fallback = fallback
        self._threshold = failure_threshold
        self._reset_seconds = reset_seconds
        self._consecutive_failures = 0
        self._open_until: datetime | None = None

    def fetch_quotes(self, tickers: list[str]) -> list[Quote]:
        now = datetime.now(timezone.utc)
        if self._open_until and now < self._open_until:
            return self._fallback.fetch_quotes(tickers)
        try:
            quotes = self._primary.fetch_quotes(tickers)
            self._consecutive_failures = 0
            self._open_until = None
            return quotes
        except Exception as e:
            self._consecutive_failures += 1
            print(f"Primary provider failed ({e}), consecutive={self._consecutive_failures}")
            if self._consecutive_failures >= self._threshold:
                self._open_until = now + timedelta(seconds=self._reset_seconds)
                print(f"Circuit open until {self._open_until}")
            return self._fallback.fetch_quotes(tickers)