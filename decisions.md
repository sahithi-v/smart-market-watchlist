DECISIONS.md entry: pool_pre_ping=True + pool_recycle=300 on the SQLAlchemy engine — Neon (serverless Postgres) silently drops idle connections on scale-down; without this, requests would intermittently fail with stale-connection errors.

DECISIONS.md entry: All timestamp columns use TIMESTAMPTZ (DateTime(timezone=True)), never naive TIMESTAMP — cursor and event-recency comparisons must be timezone-safe.

DECISIONS.md entry: symbol_stats is a single-row-per-symbol snapshot (symbol_id as PK), overwritten each rolling-stats run — distinct from price_ticks, which is append-only history with a composite key.

DECISIONS.md entry: events.payload and detectors_enabled use JSONB for detector-specific variable shape, not fixed nullable columns. detector is a plain String validated by a Python Enum, not a Postgres ENUM type — avoids ALTER TYPE friction for a small evolving set.

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