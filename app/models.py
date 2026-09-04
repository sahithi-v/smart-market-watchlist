from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey, Boolean, Integer, UniqueConstraint, BigInteger, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Date
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    circuit_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "symbol_id", name="uq_user_symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"))
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    snoozed_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

class PriceTick(Base):
    __tablename__ = "price_ticks"

    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    ltp_paise: Mapped[int] = mapped_column(BigInteger)
    volume: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(20))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
class SymbolStats(Base):
    __tablename__ = "symbol_stats"

    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mean_return: Mapped[float] = mapped_column(Numeric(10, 6))
    stddev_return: Mapped[float] = mapped_column(Numeric(10, 6))
    avg_volume_20d: Mapped[int] = mapped_column(BigInteger)
    high_20d: Mapped[int] = mapped_column(BigInteger)
    low_20d: Mapped[int] = mapped_column(BigInteger)

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), index=True)
    detector: Mapped[str] = mapped_column(String(30))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sigma: Mapped[float] = mapped_column(Numeric(10, 4))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(120), unique=True)


class UserEventState(Base):
    __tablename__ = "user_event_state"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), primary_key=True)
    shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class UserSymbolCursor(Base):
    __tablename__ = "user_symbol_cursor"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), primary_key=True)
    last_seen_event_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    sensitivity: Mapped[str] = mapped_column(String(20), default="balanced")
    min_sigma: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    detectors_enabled: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())




class DailyBar(Base):
    __tablename__ = "daily_bars"

    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), primary_key=True)
    date: Mapped[Date] = mapped_column(Date, primary_key=True)
    open_paise: Mapped[int] = mapped_column(BigInteger)
    high_paise: Mapped[int] = mapped_column(BigInteger)
    low_paise: Mapped[int] = mapped_column(BigInteger)
    close_paise: Mapped[int] = mapped_column(BigInteger)
    volume: Mapped[int] = mapped_column(BigInteger)