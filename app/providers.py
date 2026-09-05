from dataclasses import dataclass
import random
import yfinance as yf
from datetime import datetime, timezone, timedelta
from typing import Protocol


@dataclass(frozen=True)
class Quote:
    ticker: str
    ltp_paise: int
    volume: int
    ts: datetime
    source: str


class MarketDataProvider(Protocol):
    def fetch_quotes(self, tickers: list[str]) -> list[Quote]: ...


class SimulatedProvider:
    DEMO_SESSION_TICKS = 20

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


IST = timezone(timedelta(hours=5, minutes=30))


def is_market_open(now_utc: datetime) -> bool:
    """NSE regular session: 9:15-15:30 IST, Mon-Fri. Public holidays are
    NOT modeled — a named simplification; on a holiday we'd still attempt
    real data, which just returns a stale close, tolerated the same way
    any other closed-market case already is."""
    ist_now = now_utc.astimezone(IST)
    if ist_now.weekday() >= 5:
        return False
    market_open = ist_now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = ist_now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= ist_now <= market_close


class MarketHoursProvider:
    """Outside NSE trading hours, a 'successful' real-time fetch is just
    a repeated stale last-close — indistinguishable from a genuine flat
    price to our sigma detectors, and misleading to label 'live'. Skip
    the real provider entirely and go straight to simulated, rather than
    relying on CircuitBreakerProvider's failure-count logic, which a
    successful-but-stale fetch never trips."""

    def __init__(self, market_hours_provider, off_hours_provider):
        self._open_provider = market_hours_provider
        self._closed_provider = off_hours_provider

    def fetch_quotes(self, tickers: list[str]) -> list[Quote]:
        now = datetime.now(timezone.utc)
        if is_market_open(now):
            return self._open_provider.fetch_quotes(tickers)
        return self._closed_provider.fetch_quotes(tickers)