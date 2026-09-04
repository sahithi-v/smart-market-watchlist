DECISIONS.md entry: pool_pre_ping=True + pool_recycle=300 on the SQLAlchemy engine — Neon (serverless Postgres) silently drops idle connections on scale-down; without this, requests would intermittently fail with stale-connection errors.

DECISIONS.md entry: All timestamp columns use TIMESTAMPTZ (DateTime(timezone=True)), never naive TIMESTAMP — cursor and event-recency comparisons must be timezone-safe.

DECISIONS.md entry: symbol_stats is a single-row-per-symbol snapshot (symbol_id as PK), overwritten each rolling-stats run — distinct from price_ticks, which is append-only history with a composite key.

DECISIONS.md entry: events.payload and detectors_enabled use JSONB for detector-specific variable shape, not fixed nullable columns. detector is a plain String validated by a Python Enum, not a Postgres ENUM type — avoids ALTER TYPE friction for a small evolving set.

DECISIONS.md entry: Alembic pulls DATABASE_URL from Settings/.env at runtime rather than storing it in alembic.ini — keeps the real credential out of a file that's normally safe to commit.

DECISIONS.md entry: Sync SQLAlchemy + psycopg2, not async — FastAPI's threadpool gives concurrency for free at this scale; async DB access is unjustified complexity here.

DECISIONS.md entry: user_event_state tracks shown_at in addition to dismissed_at — detector affinity (dismissed/shown ratio) is unmeasurable without knowing the denominator of times an alert was actually surfaced.

DECISIONS.md entry: Reserved a circuit_pct column on symbols for a future circuit-proximity detector (India-specific price-band halt mechanic) — column added now at zero cost, detector logic deferred to Phase 2 with the rest of the signal engine.
DECISIONS.md entry: MarketDataProvider is a Protocol, not an ABC — structural typing lets SimulatedProvider/YFinanceProvider satisfy the interface with zero coupling to each other.

DECISIONS.md entry: SimulatedProvider uses a per-ticker seeded RNG (seed:ticker) so the price path is fully reproducible across runs but independent per symbol — no shared global RNG state.

DECISIONS.md entry: symbol_stats writes use ON CONFLICT DO UPDATE, not DO NOTHING — it's a snapshot table meant to be overwritten each run, unlike the append-only price_ticks/daily_bars.

DECISIONS.md entry: symbol_stats writes use ON CONFLICT DO UPDATE, not DO NOTHING — it's a snapshot table meant to be overwritten each run, unlike the append-only price_ticks/daily_bars.

DECISIONS.md entry: Railway over Vercel — APScheduler needs one long-running process; Vercel's serverless model tears down between requests and can't host an in-process scheduler.

DECISIONS.md entry: MarketDataProvider is a Protocol, not an ABC — structural typing lets SimulatedProvider/YFinanceProvider satisfy the interface with zero coupling to each other.

DECISIONS.md entry: SimulatedProvider uses a per-ticker seeded RNG (seed:ticker) so the price path is fully reproducible across runs but independent per symbol — no shared global RNG state.

DECISIONS.md entry: Ingest uses Postgres INSERT ... ON CONFLICT DO NOTHING on (symbol_id, ts), not a pre-check SELECT — one atomic statement per row, no race between check and insert under concurrent ingest runs.

DECISIONS.md entry: Volatility baselines are computed from backfilled real daily bars, not from ticks accumulated during the demo — separating the slow baseline timescale from the fast live-move timescale keeps z-scores statistically meaningful from first run.

DECISIONS.md entry: symbol_stats writes use ON CONFLICT DO UPDATE, not DO NOTHING — it's a snapshot table meant to be overwritten each run, unlike the append-only price_ticks/daily_bars.

DECISIONS.md entry: Deploy config (Railway start command) is pinned in a committed railway.json, not left as dashboard-only state — reproducible from a clean clone, not dependent on manual settings surviving a project recreation.

DECISIONS.md entry: YFinanceProvider is primary, SimulatedProvider is the circuit-breaker fallback — opposite of the original plan's "simulated-by-default" — chosen deliberately for demo authenticity, with the fallback seeded from each symbol's real last close and real daily σ so a failover is still statistically realistic, not arbitrary. Circuit opens after 3 consecutive full-batch failures, resets after 60s.

DECISIONS.md entry: Symbol list was manually checked against recent corporate actions before seeding — TATAMOTORS excluded after discovering NSE renamed it to TMPV following its Oct 2025 demerger, replaced with ICICIBANK.

DECISIONS.md entry: MarketDataProvider is a Protocol, not an ABC — structural typing lets SimulatedProvider/YFinanceProvider satisfy the interface with zero coupling to each other.

DECISIONS.md entry: SimulatedProvider uses a per-ticker seeded RNG (seed:ticker) so the price path is fully reproducible across runs but independent per symbol — no shared global RNG state.

DECISIONS.md entry: symbol_stats writes use ON CONFLICT DO UPDATE, not DO NOTHING — it's a snapshot table meant to be overwritten each run, unlike the append-only price_ticks/daily_bars.

DECISIONS.md entry: Railway over Vercel — APScheduler needs one long-running process; Vercel's serverless model tears down between requests and can't host an in-process scheduler.

DECISIONS.md entry: Ingest uses Postgres INSERT ... ON CONFLICT DO NOTHING on (symbol_id, ts), not a pre-check SELECT — one atomic statement per row, no race between check and insert under concurrent ingest runs.

DECISIONS.md entry: Volatility baselines are computed from backfilled real daily bars, not from ticks accumulated during the demo — separating the slow baseline timescale from the fast live-move timescale keeps z-scores statistically meaningful from first run.

DECISIONS.md entry: Deploy config (Railway start command) is pinned in a committed railway.json, not left as dashboard-only state — reproducible from a clean clone, not dependent on manual settings surviving a project recreation.

DECISIONS.md entry: YFinanceProvider is primary, SimulatedProvider is the circuit-breaker fallback — opposite of the original plan's "simulated-by-default" — chosen deliberately for demo authenticity, with the fallback seeded from each symbol's real last close and real daily σ so a failover is still statistically realistic, not arbitrary. Circuit opens after 3 consecutive full-batch failures, resets after 60s.

DECISIONS.md entry: Symbol list was manually checked against recent corporate actions before seeding — TATAMOTORS excluded after discovering NSE renamed it to TMPV following its Oct 2025 demerger, replaced with ICICIBANK.

DECISIONS.md entry: Detectors take only primitives (paise ints, floats), never ORM rows — keeps them unit-testable with plain numbers and decoupled from the DB layer.

DECISIONS.md entry: Every detector emits at the system floor — the loosest min_sigma/volume_multiple across all sensitivity presets — and stores its real measured value on the event. Per-user sensitivity filters at digest read time, not at emission, so "compute events once per symbol" stays true even though presets differ per user.

DECISIONS.md entry: Cooldown/suppression is a read-time concern, not an emission-time one. Every qualifying event is stored; the digest query collapses events sharing (symbol, detector) within the cooldown window down to the highest-magnitude one. Emission-time cooldown would let an early small move suppress a later larger one for every user who reads after it.

DECISIONS.md entry: Sensitivity resolution (user override -> preset -> default) is one function, resolve_min_sigma(), called both when validating a settings write and when scoring a digest read — so the two can't drift apart. Overrides below the emission floor are rejected outright rather than silently accepted and shown nothing.