# Decisions

Every non-obvious call made while building this, and why — written as the
project was built, not reconstructed afterward.

## Infrastructure & deployment

- **Railway over Vercel.** APScheduler needs one long-running process to
  hold its schedule state. Vercel's serverless model tears down between
  requests and can't host an in-process scheduler.
- **`pool_pre_ping=True` + `pool_recycle=300`** on the SQLAlchemy engine —
  Neon (serverless Postgres) silently drops idle connections on
  scale-down. Without this, requests would intermittently fail with
  stale-connection errors.
- **All timestamps are `TIMESTAMPTZ`**, never naive. Cursor and
  event-recency comparisons have to be timezone-safe or they silently
  produce wrong ages.
- **Alembic pulls `DATABASE_URL` from `.env` at runtime**, not stored in
  `alembic.ini` — keeps the real credential out of a file that's normally
  safe to commit.
- **`railway.json` is committed**, not left as dashboard-only config —
  reproducible from a clean clone, not dependent on manual Railway
  settings surviving a project recreation.
- **`SECRET_KEY` was missing on Railway** at one point (only existed in
  the local `.env`) and crashed the whole live app on startup. Fixed by
  setting it directly in Railway's Variables tab. Local `.env` and
  deployed env vars are separate stores — nothing syncs automatically
  between them.

## Data model & ingest

- **`symbol_stats` is a single-row-per-symbol snapshot** (symbol_id as
  PK), overwritten on every rolling-stats run — distinct from
  `price_ticks` and `daily_bars`, which are append-only history. Snapshot
  writes use `ON CONFLICT DO UPDATE`; append-only writes use
  `ON CONFLICT DO NOTHING`.
- **`events.payload` and `detectors_enabled` are JSONB**, not fixed
  nullable columns — detector-specific shape varies. `detector` is a
  plain `String` validated by a Python Enum, not a Postgres ENUM, to
  avoid `ALTER TYPE` friction for a small, evolving set.
- **`events.sigma` is shared across all detector types** — `VOLUME_SPIKE`
  stores its volume multiple in the same column, not a true sigma. This
  keeps cooldown collapse and scoring detector-agnostic (they only need
  "how big was this") without a schema change per detector. Not perfectly
  commensurable across types — a real simplification, named here rather
  than hidden.
- **`MarketDataProvider` is a `Protocol`, not an ABC** — structural
  typing lets `SimulatedProvider`/`YFinanceProvider` satisfy the
  interface with zero coupling to each other.
- **`SimulatedProvider` uses a per-ticker seeded RNG** (`seed:ticker`),
  so price paths are reproducible across runs but independent per
  symbol — no shared global RNG state.
- **Found and fixed a real production bug**: the volume-tick multiplier
  was `uniform(0.7, 1.4)`, which averages 1.05, not 1.0 — a genuine
  upward drift bias. Compounded over thousands of ticks (the process
  runs continuously for hours), this produced statistically impossible
  readings — volume multiples in the hundreds of thousands. Fixed the
  bias to a symmetric `uniform(0.8, 1.2)` and added a hard clamp on both
  price (±25% of the real seeded value) and volume (0.2×–8×) as a
  second, independent safety bound, so a future subtly-biased RNG choice
  can't reproduce this failure mode.
- **`YFinanceProvider` is primary, `SimulatedProvider` is the
  circuit-breaker fallback** — the opposite of the original plan's
  "simulated by default," chosen for demo authenticity. The fallback is
  seeded from each symbol's real last close and real daily σ, so a
  failover is still statistically realistic, not arbitrary. Circuit
  opens after 3 consecutive full-batch failures, resets after 60s.
- **Added `MarketHoursProvider`** on top of the circuit breaker — a
  successful-but-stale real fetch outside NSE hours (9:15–15:30 IST,
  Mon–Fri) never trips a failure-count circuit breaker, since it isn't
  an error. Outside those hours, routes straight to simulated data
  instead. Fixed UTC+5:30 offset, no `zoneinfo` dependency needed since
  IST has no DST. Public holidays aren't modeled — a named
  simplification, tolerated the same way any other stale close already
  is.
- **`app/backfill_daily_bars.py`** fetches real historical daily bars via
  yfinance for every symbol in the DB, not just the 5 originally seeded
  via CSV — extends real seed data to the full watchlist-addable
  universe without fabricating anything. Skips rows with NaN OHLCV
  values (yfinance occasionally returns placeholder rows for
  holidays/gaps) rather than crashing the whole backfill.
- **Detectors take only primitives** (paise ints, floats), never ORM
  rows — keeps them unit-testable with plain numbers, decoupled from the
  DB layer.
- **Symbol list was manually checked against recent corporate actions**
  before seeding — TATAMOTORS excluded after discovering NSE renamed it
  to TMPV following its Oct 2025 demerger, replaced with ICICIBANK.

## Signal engine & scoring

- **Every detector emits at the system floor** — the loosest
  `min_sigma`/`volume_multiple` across all sensitivity presets — and
  stores its real measured value on the event. Per-user sensitivity
  filters at digest read time, not emission, so "compute once per
  symbol" holds even though presets differ per user.
- **Sensitivity resolution is one function**, `resolve_min_sigma()`,
  called both when validating a settings write and when scoring a
  digest read — so the two can't drift apart. Overrides below the
  emission floor are rejected outright, not silently accepted and shown
  nothing.
- **`resolve_thresholds()` maps each detector to the right preset field**
  (`min_sigma` for σ-based detectors, `volume_multiple` for
  VOLUME_SPIKE) — one number can't correctly threshold two different
  units.
- **Cooldown collapse is a read-time concern**, not emission-time. Every
  qualifying event is stored; the digest query collapses events sharing
  (symbol, detector) within the cooldown window down to the
  highest-magnitude one. Emission-time cooldown would let an early small
  move suppress a later, larger one for every user who reads after it.
- **Cooldown window is 4 hours** — the same number as the recency-decay
  half-life used in scoring. One constant, reused, not two unrelated
  magic numbers to justify separately.
- **`user_symbol_cursor` advances via `GREATEST()` inside the `UPDATE`
  itself**, not read-then-compare-then-write in Python — two devices
  marking the same symbol seen concurrently can't race the cursor
  backward.
- **Cursor is seeded at the moment a symbol is added** (`added_at`), not
  left null — a symbol added mid-session must not surface a week of
  backlog on its first digest. Removing a watchlist item also deletes
  its cursor row, so a re-add reseeds cleanly instead of inheriting a
  stale one.
- **`get_unseen_events` was missing a filter on `dismissed_at`** — a real
  correctness gap found while wiring the frontend dismiss button, not by
  inspection. Dismissed events had no mechanism preventing them from
  reappearing in every future digest indefinitely. Fixed with a left
  join excluding rows where `dismissed_at` is set.
- **`empty_reason` checked the raw candidate-event count, not the final
  filtered count** — another real bug, found via live testing on a
  fresh account. A user whose sensitivity threshold filtered out every
  candidate event saw a genuinely blank digest pane with no explanation,
  since `empty_reason` incorrectly stayed `None`. Fixed to check the
  final `items` list instead.
- **Priority score and every "why am I seeing this" explanation use only
  real computed signals** — price move, volume, recency, pin, affinity.
  No news or earnings data feeds the score. Fabricating causal
  explanations for price moves was rejected as a trust risk to a
  fintech evaluator, not simply left out of scope.
- **Detector affinity ("dismiss to learn") defaults to 1.0** until at
  least 5 signals of that detector have been shown — not enough data to
  trust a ratio from 1–2 signals. Past that, clamped to [0.3, 1.0]: a
  user who dismisses every instance still gets some of it through, since
  a detector silenced to zero would be indistinguishable from a bug.
- **`GET /api/digest` has a deliberate side effect** — it records
  `shown_at` for whatever it returns, via `ON CONFLICT DO NOTHING` so an
  already-shown-or-dismissed event is never touched again. This is the
  denominator affinity is computed from; without recording impressions,
  "dismissed / shown" has no shown to divide by.
- **Naive-comparison ranking sorts by `abs(sigma)`**, not raw % price
  change — VOLUME_SPIKE events have no price-change field, and sigma is
  already the app's cross-detector magnitude proxy. Reuses an existing
  named simplification rather than introducing a new one.
- **`idempotency_keys` stays schema-only, unused.** Every write endpoint
  already gets real idempotency for free through natural unique
  constraints (`ON CONFLICT DO NOTHING`/`DO UPDATE` on
  `(user_id, symbol_id)`, `(user_id, event_id)`, `dedupe_key`) — a
  generic key-based mechanism would be complexity without a problem to
  solve. One honest caveat: a retried request can get a different
  status code than the original (400 instead of 201, 404 instead of
  204) even though the underlying data never duplicates or corrupts. A
  true idempotency cache would replay the exact original response; this
  doesn't. Reserved for a future endpoint that actually lacks a natural
  conflict key.

## Auth & security

- **Real multi-user auth**, not a single demo user — the product's whole
  thesis is personalization (per-user cursor, sensitivity, affinity),
  which can't be demonstrated with one account. A no-password
  demo-switcher was considered and rejected in favor of real signup, at
  a cost of roughly an hour against the budget.
- **bcrypt called directly, not via passlib** — passlib is unmaintained
  and breaks on bcrypt>=4.1. One fewer dependency layer, same
  well-audited primitive.
- **Sessions use Starlette's signed-cookie `SessionMiddleware`**, not a
  DB-backed session table — no server-side session storage or extra
  table.
- **JWT was considered and rejected** — it solves cross-origin/stateless
  problems this same-origin, server-rendered app doesn't have, and
  doesn't fix revocation without a blocklist, which reintroduces
  server-side state anyway.
- **Session cookie uses `SameSite=Lax`**, blocking it on cross-site
  non-GET requests — closes the standard CSRF vector as long as every
  state-changing route stays POST/PATCH/DELETE, never GET. No separate
  CSRF token needed at this scope.
- **Login returns the same generic "Invalid email or password"** for
  both a wrong password and a nonexistent email — a distinct message
  for each would let an attacker enumerate which emails have accounts.

## Watchlist API

- **Adding a symbol is one atomic
  `INSERT ... ON CONFLICT DO NOTHING ... RETURNING`**, not a
  check-then-insert — same race-free pattern as ingest, applied
  consistently rather than reinvented per endpoint.
- **Pin/unpin uses one atomic `UPDATE ... WHERE version = :expected`**,
  not a read-compare-write in Python — real optimistic locking, verified
  end-to-end: correct version succeeds and increments; stale version is
  correctly rejected with 409, proving the guard actually prevents
  concurrent overwrites rather than being a schema column nobody
  enforces.
- **`GET /api/watchlist` was missing** despite being described as built
  in an earlier pass — added it, joining `WatchlistItem` → `Symbol`,
  ordered pinned-first then by position, matching the sidebar's intended
  grouping.
- **DELETE returning 404 is treated as success in the UI** — a 404 here
  means the row was already gone (likely a second tab), and the end
  state the user wants is already true. Surfacing it as an error would
  be misleading.
- **Watchlist pin/remove buttons use plain `fetch()`** against the
  existing JSON API, not a second HTML-returning endpoint for HTMX's
  sake — avoids duplicating tested PATCH/DELETE logic. DOM updates (row
  removal, re-sort on pin) are handled manually in a small JS function,
  same pattern as the auth-response handler.
- **Watchlist row markup exists in two places** (Jinja for initial
  render, a JS template string for post-pin refresh) — an accepted
  duplication. The alternative was adding HTML-fragment endpoints that
  would duplicate already-tested JSON logic instead.

## Frontend architecture

- **Page-rendering routes live in their own `app/pages.py` router**,
  separate from the JSON API routers — keeps the API surface and the
  server-rendered UI surface from mixing in one file.
- **Dashboard route queries the DB directly and server-renders the
  initial digest/watchlist HTML**, reusing existing pure functions
  (`assemble_digest`, watchlist queries) rather than duplicating them as
  a second JSON-consuming path. HTMX/JS only handle post-load updates
  against the same, untouched JSON API.
- **Digest item formatting (paise→₹, relative "Xm ago") happens in
  Python**, in the route, not in Jinja — keeps templates display-only
  and formatting independently testable, consistent with
  `digest_core.py` already being a pure, separately-tested function.
- **Switched the outer dashboard layout from flexbox to CSS Grid**
  specifically to support the drawer's push-transition —
  `grid-template-columns` toggled via JS between `272px 1fr 0px`
  (closed) and `272px 1fr 360px` (open). One property animates
  smoothly; no manual width math for the three-column proportions.
- **Settings exposes only the sensitivity preset**, not the
  `min_sigma`/`detectors_enabled` overrides — those exist in the schema
  and are already read by `resolve_thresholds()`, but the original plan
  explicitly scoped the Settings UI to stay small. The overrides remain
  a real, usable-but-unexposed capability, not dead schema.
- **Three-font system** (Fraunces for display, Public Sans for UI, IBM
  Plex Mono for every number) — each font restricted to one job, partly
  to avoid a flat, single-font look, partly because numeric data gets
  real column alignment from tabular figures this way.
- **Palette avoids pure black/white and saturated red/green** — a muted
  moss green as the primary accent, oxblood instead of alarm red for
  attention states, brass restricted to pinned items only so it reads
  as a deliberate accent, not decoration.
- **Login/signup use `hx-on::after-request` to redirect on success**,
  not HTMX's default HTML swap — the auth endpoints return JSON, so the
  frontend reacts to the status code instead of expecting an HTML
  fragment. Found and fixed a real bug here: without `hx-swap="none"`,
  HTMX's default swap briefly rendered the raw JSON response before the
  redirect fired — a visible flash of unstyled text on every login.
- **Tab toggling (login/signup, All/Important) uses a few lines of
  plain JS**, not HTMX — client-only UI state is outside HTMX's
  server-communication model, and reaching for it here would add
  complexity for no benefit.
- **The Jinja2 `TemplateResponse` call needed `request` as the first
  positional argument**, not the older
  `TemplateResponse(name, {"request": request})` form — the installed
  Starlette version requires the newer signature; the old one raised
  `TypeError: unhashable type: 'dict'` because Jinja tried to use the
  context dict as a cache key.
- **Added a global "Prices as of Xm ago" indicator**, distinct from
  each card's own event timestamp — a direct, explicit answer to "how
  do you handle stale data," rather than leaving it implicit in
  per-event timestamps.
- **Digest cards show a small "Simulated" tag** when the latest price
  tick's source is `"simulated"` — reuses data already captured on
  ingest, keeps real vs. synthetic data honestly distinguishable
  instead of hidden.
- **User menu (avatar → name/email/logout) calls the existing,
  already-tested `POST /api/auth/logout`** — no new backend endpoint.
  Affinity explanations shown in the "Your patterns" widget are
  computed server-side in Python, not duplicated in JS, so there's one
  place the cold-start and floor logic can be read and verified.