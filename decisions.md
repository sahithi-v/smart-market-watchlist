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
DECISIONS.md entry: Railway over Vercel — APScheduler needs one long-running process; Vercel's serverless model tears down between requests and can't host an in-process scheduler.
DECISIONS.md entry: Ingest uses Postgres INSERT ... ON CONFLICT DO NOTHING on (symbol_id, ts), not a pre-check SELECT — one atomic statement per row, no race between check and insert under concurrent ingest runs.
DECISIONS.md entry: Volatility baselines are computed from backfilled real daily bars, not from ticks accumulated during the demo — separating the slow baseline timescale from the fast live-move timescale keeps z-scores statistically meaningful from first run.
DECISIONS.md entry: Deploy config (Railway start command) is pinned in a committed railway.json, not left as dashboard-only state — reproducible from a clean clone, not dependent on manual settings surviving a project recreation.
DECISIONS.md entry: YFinanceProvider is primary, SimulatedProvider is the circuit-breaker fallback — opposite of the original plan's "simulated-by-default" — chosen deliberately for demo authenticity, with the fallback seeded from each symbol's real last close and real daily σ so a failover is still statistically realistic, not arbitrary. Circuit opens after 3 consecutive full-batch failures, resets after 60s.
DECISIONS.md entry: Symbol list was manually checked against recent corporate actions before seeding — TATAMOTORS excluded after discovering NSE renamed it to TMPV following its Oct 2025 demerger, replaced with ICICIBANK.
DECISIONS.md entry: Detectors take only primitives (paise ints, floats), never ORM rows — keeps them unit-testable with plain numbers and decoupled from the DB layer.
DECISIONS.md entry: Every detector emits at the system floor — the loosest min_sigma/volume_multiple across all sensitivity presets — and stores its real measured value on the event. Per-user sensitivity filters at digest read time, not at emission, so "compute events once per symbol" stays true even though presets differ per user.
DECISIONS.md entry: Sensitivity resolution (user override -> preset -> default) is one function, resolve_min_sigma(), called both when validating a settings write and when scoring a digest read — so the two can't drift apart. Overrides below the emission floor are rejected outright rather than silently accepted and shown nothing.
DECISIONS.md entry: resolve_thresholds() maps each detector to the correct field from the resolved preset (min_sigma for SIGMA_MOVE/GAP/REVERSAL/RANGE_BREAK, volume_multiple for VOLUME_SPIKE) rather than using one number for all detectors — a sigma-based detector and a volume-multiple detector are different units; one threshold can't correctly gate both.
DECISIONS.md entry: events.sigma is a NOT NULL column shared across all detector types — VOLUME_SPIKE stores its volume multiple in it too, not a true sigma, so cooldown collapse and scoring (which only need "how big was this") work identically regardless of detector without a schema change per detector. Not perfectly commensurable across detector types — a real simplification, named here rather than hidden.
DECISIONS.md entry: Cooldown/suppression is a read-time concern, not an emission-time one. Every qualifying event is stored; the digest query collapses events sharing (symbol, detector) within the cooldown window down to the highest-magnitude one. Emission-time cooldown would let an early small move suppress a later larger one for every user who reads after it.
DECISIONS.md entry: Cooldown window is 4 hours, matching the recency-decay half-life used in scoring — one number, reused, not two unrelated magic constants to justify separately.
DECISIONS.md entry: user_symbol_cursor advances via GREATEST() computed inside the UPDATE itself, not read-then-compare-then-write in Python — two devices marking the same symbol seen concurrently can't race each other into a cursor moving backward.
DECISIONS.md entry: Cursor is seeded at the moment a symbol is added to a watchlist (added_at), not left null — a symbol added mid-session must not surface a week of backlog on its first digest. Removing a watchlist item also deletes its cursor row, so a later re-add reseeds cleanly instead of inheriting a stale cursor.
DECISIONS.md entry: Priority score and every "why am I seeing this" explanation use only real computed signals (price move, volume, recency, pin, affinity) — no news or earnings data source exists or is planned, and fabricating causal explanations for price moves was rejected as a trust risk to a fintech evaluator, not simply left out of scope.
DECISIONS.md entry: Detector affinity ("dismiss to learn") defaults to 1.0 until at least 5 signals of that detector have been shown to the user — not enough data to trust a ratio computed from 1-2 signals. Past that, clamped to [0.3, 1.0]: a user who dismisses every instance of a detector still gets some of it through, since a detector silenced to zero would be indistinguishable from a bug.
DECISIONS.md entry: GET /api/digest has a deliberate side effect — it records shown_at for whatever it returns, via ON CONFLICT DO NOTHING so an event already marked shown (or dismissed) is never touched again. This is the denominator affinity is computed from; without recording impressions, "dismissed / shown" has no shown to divide by.
DECISIONS.md entry: bcrypt called directly, not via passlib — passlib is unmaintained and breaks on bcrypt>=4.1; one fewer dependency layer, same well-audited primitive.
DECISIONS.md entry: Sessions use Starlette's signed-cookie SessionMiddleware, not a DB-backed session table — no server-side session storage or extra table, consistent with the "no Redis unless you finish early" stance.
DECISIONS.md entry: Considered JWT over signed-cookie sessions; rejected — JWT solves cross-origin/stateless problems this same-origin server-rendered app doesn't have, and doesn't fix revocation without a blocklist, which reintroduces server-side state anyway.
DECISIONS.md entry: Session cookie uses Starlette's default SameSite=Lax, blocking the cookie on cross-site non-GET requests — closes the standard CSRF vector as long as all state-changing routes stay POST/PATCH/DELETE, never GET. No separate CSRF token needed at this scope.
DECISIONS.md entry: Login returns the same generic "Invalid email or password" for both a wrong password and a nonexistent email — a distinct message for each would let an attacker enumerate which emails have accounts.
DECISIONS.md entry: Real multi-user auth (signup/login/password), not a single demo user — the product's whole thesis is personalization (per-user cursor, sensitivity, affinity), which can't be demonstrated with one user. A no-password demo-switcher was considered and rejected in favor of real signup, at the cost of ~1 hour against the budget.
DECISIONS.md entry: Adding a symbol to a watchlist is one atomic INSERT ... ON CONFLICT DO NOTHING ... RETURNING, not a check-then-insert — same race-free pattern as ingest.py, applied consistently rather than reinvented per endpoint.
DECISIONS.md entry: Watchlist pin/update uses one atomic UPDATE ... WHERE version = :expected, not a read-compare-write in Python — closes the "conflicting data" requirement from the brief for real, not just via a schema column that nothing reads.
DECISIONS.md entry: Three-font system (Fraunces/Public Sans/IBM Plex Mono) with each font restricted to one job — avoids the single-font AI-generated look and gives numeric data real column alignment via tabular figures.

DECISIONS.md entry: Palette avoids pure black/white and saturated red/green — muted moss green as primary accent, oxblood (not alarm red) for attention states, brass restricted to pinned items only so it stays a luxury accent, not decoration.

DECISIONS.md entry: Page-rendering routes (return HTML via Jinja2) live in a separate app/pages.py router from the JSON API routers — keeps the API surface and the server-rendered UI surface from mixing in one file.

DECISIONS.md entry: Jinja2Templates.TemplateResponse called with request as the first positional arg (TemplateResponse(request, name, context)), not the older TemplateResponse(name, {"request": request}) form — required by the installed Starlette version; the old signature raised TypeError: unhashable type: 'dict' because Jinja tried to use the context dict as a template-name cache key.

DECISIONS.md entry: Confirmed via pip show starlette — installed version requires TemplateResponse(request, name, context); fixed the call signature in app/pages.py accordingly.

DECISIONS.md entry: Login/signup forms use HTMX's hx-on::after-request to redirect on success rather than swapping response HTML — auth endpoints return JSON (untouched, already tested), so the frontend reacts to status code instead of expecting an HTML fragment back.

DECISIONS.md entry: Tab toggle between login/signup forms uses plain inline JS (a few lines, not a framework) — client-only UI state (which form is visible) is out of scope for HTMX's server-communication model; using HTMX here would add complexity for no benefit.
DECISIONS.md entry: Verified full signup flow end-to-end against live Neon DB via browser — form → /api/auth/signup → bcrypt hash → DB insert → session cookie → redirect to /dashboard. Confirms Phase 3 auth wiring, not just Phase 1/2 unit tests.

DECISIONS.md entry: Page routes use a separate get_current_user_optional dependency that returns None (not an exception) when unauthenticated, so the route itself decides to RedirectResponse to /login — kept distinct from the API's get_current_user, which correctly raises 401 JSON for API callers.

DECISIONS.md entry: All auth forms use hx-swap="none" — without it, HTMX's default behavior briefly dumps the raw JSON response into the form's HTML before our hx-on::after-request redirect fires, causing a visible flash of unstyled JSON. hx-swap="none" disables DOM swapping entirely so the response is only used by our custom handler.

DECISIONS.md entry: hx-swap="none" added to both auth forms — closes the JSON-flash bug where HTMX's default swap briefly rendered raw response text before the custom redirect handler fired.

DECISIONS.md entry: Dashboard page route (/dashboard) queries the DB directly and server-renders the initial digest/watchlist HTML — reuses existing Phase 1/2 Python functions (assemble_digest, watchlist queries) rather than duplicating them as a second JSON-consuming path. HTMX handles only

DECISIONS.md entry: SECRET_KEY env var was missing on Railway (only existed in local .env, correctly gitignored) — caused a startup crash via pydantic-settings validation, taking the whole live app down. Fixed by setting SECRET_KEY directly in Railway's Variables tab. Local .env and deployed environment variables are separate stores by design; nothing auto-syncs between them.

DECISIONS.md entry: Added GET /api/watchlist — was missing despite being described as built in an earlier DECISIONS.md entry; joins WatchlistItem → Symbol, ordered pinned-first then by position, matching the sidebar's intended visual grouping.

DECISIONS.md entry: Verified POST /api/watchlist end-to-end against live Neon DB via authenticated session — real insert, real cursor row, real position auto-increment logic.

DECISIONS.md entry: Verified optimistic locking end-to-end — PATCH with correct version succeeds and increments version; PATCH with stale version correctly rejected with 409, proving the WHERE version=:expected guard actually prevents concurrent overwrites, not just a schema column nobody enforces.

DECISIONS.md entry: Watchlist pin/remove buttons use plain JS fetch() against the existing JSON API (not a second HTML-returning endpoint) — avoids duplicating tested PATCH/DELETE logic just to satisfy HTMX's HTML-swap expectation; DOM update (remove row / re-sort/reorder pinned) handled manually in a small JS function, same pattern already used for auth-response handling.

DECISIONS.md entry: Watchlist row markup exists in two places (Jinja initial render + JS renderItemHtml for post-pin refresh) — accepted duplication; alternative was adding HTML-fragment endpoints that would duplicate already-tested JSON logic instead.

DECISIONS.md entry: DELETE returning 404 is treated as success in the UI (row removed from DOM regardless) — a 404 here means the end state the user wants was already true, likely from a second tab; surfacing it as an error would be misleading.

DECISIONS.md entry: Digest item formatting (paise→₹ conversion, relative "Xm/Xh ago" timestamps) happens in the page route (Python), not in Jinja — keeps template display-only and formatting logic independently testable, consistent with digest_core.py already being a pure, separately-tested function.

DECISIONS.md entry: Naive-comparison ranking (the "how would this look under the obvious approach" toggle) sorts by abs(sigma) rather than raw % price change — VOLUME_SPIKE events have no price-change field, and sigma is already the app's documented cross-detector magnitude proxy. Reuses an existing named simplification rather than introducing a new one.

DECISIONS.md entry: Switched dashboard outer layout from flexbox to CSS Grid specifically to support the drawer's push-transition — grid-template-columns toggled via JS between 272px 1fr 0px (closed) and 272px 1fr 360px (open), single property animates smoothly, no manual width math needed for the three-column proportions

DECISIONS.md entry: Settings page exposes only the sensitivity preset radio (low/balanced/high), not the min_sigma/detectors_enabled override columns — those exist in the schema and are already read by resolve_thresholds(), but the architecture doc explicitly scoped the Settings UI to "keep this small"; overrides remain a real, usable-but-unexposed capability, not dead schema.

DECISIONS.md entry: Verified /api/news/{ticker} against live NewsAPI.org — real headline returned for RELIANCE, confirming key validity and endpoint wiring before frontend integration.

DECISIONS.md entry: Added a global "Prices as of Xm ago" indicator on the dashboard, distinct from each digest card's own event timestamp — directly answers the brief's "how do you handle stale data" requirement by surfacing data freshness explicitly, not just implicitly through per-event timestamps.

DECISIONS.md entry: get_unseen_events was missing a filter on UserEventState.dismissed_at — dismissed events had no mechanism preventing them from reappearing in future digests indefinitely. Fixed with a left join excluding rows where dismissed_at is set; this was a real correctness gap, found while wiring the frontend dismiss button, not by inspection alone.

DECISIONS.md entry: Added MarketHoursProvider, checking NSE hours (9:15–15:30 IST, Mon–Fri, fixed UTC+5:30 offset — IST has no DST, so no zoneinfo/tzdata dependency needed) — routes directly to SimulatedProvider outside those hours, since a successful-but-stale real fetch never trips the existing failure-count circuit breaker. Public holidays are not modeled — a named simplification; a closed-market holiday still attempts real data, tolerated the same way any other stale close already is.

DECISIONS.md entry: app/backfill_daily_bars.py fetches real historical daily bars via yfinance for every symbol in the DB, not just the 5 manually seeded earlier — extends real seed data to the full watchlist-addable universe without fabricating anything.

DECISIONS.md entry: Digest cards show a small "Simulated" tag when the latest price tick's source is "simulated" — reuses existing ingest data, no new tracking, keeps real vs. synthetic data honestly distinguishable rather than hidden.