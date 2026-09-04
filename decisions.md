DECISIONS.md entry: pool_pre_ping=True + pool_recycle=300 on the SQLAlchemy engine — Neon (serverless Postgres) silently drops idle connections on scale-down; without this, requests would intermittently fail with stale-connection errors.

DECISIONS.md entry: All timestamp columns use TIMESTAMPTZ (DateTime(timezone=True)), never naive TIMESTAMP — cursor and event-recency comparisons must be timezone-safe.

DECISIONS.md entry: symbol_stats is a single-row-per-symbol snapshot (symbol_id as PK), overwritten each rolling-stats run — distinct from price_ticks, which is append-only history with a composite key.

DECISIONS.md entry: events.payload and detectors_enabled use JSONB for detector-specific variable shape, not fixed nullable columns. detector is a plain String validated by a Python Enum, not a Postgres ENUM type — avoids ALTER TYPE friction for a small evolving set.

DECISIONS.md entry: Alembic pulls DATABASE_URL from Settings/.env at runtime rather than storing it in alembic.ini — keeps the real credential out of a file that's normally safe to commit.

DECISIONS.md entry: Sync SQLAlchemy + psycopg2, not async — FastAPI's threadpool gives concurrency for free at this scale; async DB access is unjustified complexity here.

DECISIONS.md entry: user_event_state tracks shown_at in addition to dismissed_at — detector affinity (dismissed/shown ratio) is unmeasurable without knowing the denominator of times an alert was actually surfaced.

DECISIONS.md entry: Reserved a circuit_pct column on symbols for a future circuit-proximity detector (India-specific price-band halt mechanic) — column added now at zero cost, detector logic deferred to Phase 2 with the rest of the signal engine.