# Glean — Smart Market Watchlist

Built solo for Groww's CODE 2026 hiring challenge in 72 hours.

**Live app:** https://smart-market-watchlist-production.up.railway.app
**Repo:** https://github.com/sahithi-v/smart-market-watchlist

Sign up with any email — it's real multi-user authentication, not a demo
login. Works on desktop and mobile.

## The actual problem

A watchlist that just lists prices next to each other isn't telling you
anything. A number on its own doesn't say whether today is ordinary or
whether something real happened. So instead of a price list, this runs two
statistical detectors continuously, in the background, against every
symbol on a user's watchlist:

- A price move is flagged only if it's a genuine outlier against that
  specific stock's own 30-day volatility — a z-score, not a flat
  percentage. A 2% move in a stock that barely moves is a different event
  than a 2% move in a stock that swings every day.
- A volume spike is flagged against that stock's own 20-day average
  volume.

Both run on a schedule (ingest every 15s, detection every 30s), independent
of whether anyone is looking at the app.

## What I think is actually different here

**The drawer shows the math, and argues with itself.** Click any digest
item and it opens the full score breakdown — base magnitude, times a
recency decay, times a pin boost, times how much you personally tend to
engage with that kind of alert — and right below it, where the same item
would have ranked under a naive "just sort by raw price movement"
approach. Sometimes they agree. Sometimes they don't, and you can see
exactly why, on screen, not just as a claim in this README.

**Dismissing something changes what you see later, for real.** Keep
dismissing volume-spike alerts and the app quietly trusts that detector
less for you specifically — not by hiding it, by weighting it down. It
won't touch anything until it's seen at least 5 of that detector's alerts
for you, and it never fully mutes a detector even after constant
dismissal, since a detector gone completely silent is indistinguishable
from a bug.

**It doesn't invent anything.** No AI-written "here's probably why this
moved." No fabricated headlines. Real news, pulled from a live API, loaded
only the moment a drawer opens — never preloaded, never shown unless real.

**It's honest when data isn't live.** Outside NSE trading hours, a "live"
feed is really just repeating yesterday's close. Rather than quietly treat
that as current, the app switches to simulated movement — seeded from that
stock's real historical volatility, bounded so it can wander realistically
but never runs away — and tags anything using it as "Simulated," visibly,
on the card.

**It's responsive.** The drawer pushes open as a third column on desktop;
on a phone it becomes a full-screen overlay instead of squeezing three
columns into one small screen.

## Why Python, and why not something else

The core of this app is statistics — rolling z-scores, volatility
baselines — and Python's numeric ecosystem is built for exactly that.
Reimplementing rolling standard deviation in Java or Go would mean either
pulling in a heavier numerical library or hand-rolling math that's a
one-liner in pandas. FastAPI's Pydantic models gave real request
validation and typed contracts without Java's usual ceremony of interfaces
and DTOs — real velocity for a 72-hour build. The honest tradeoff: Python
is genuinely slower for CPU-bound work at real scale. At the scale of one
watchlist app, that tradeoff hasn't come due yet.

## Why Postgres, not a document store

The digest query is a real multi-table join chain — events to symbols to
watchlist items to per-user cursors — and pin/unpin relies on an atomic
`UPDATE ... WHERE version = :expected` for real optimistic locking. Those
are relational guarantees, not something a document database hands you for
free. Choosing NoSQL here wouldn't have been "more scalable," it would have
meant fighting the actual shape of the data.

## Why server-rendered HTML, not React

A single-page app means two sources of truth — client state and server
state — that can silently drift apart. That's exactly the kind of bug
class I didn't want to be debugging blind, under a hard deadline. Server-
rendered templates and the database are never lying to each other. The
real cost: this gives up the smoother transitions and offline behavior an
SPA would offer. A cost, not a non-issue — just one I'd rather pay here.

## Why one process, not microservices

No Kafka, no Celery, no React, no microservices. Ingest, volatility
recalculation, and signal detection all run inside the same FastAPI
process via APScheduler. Splitting this into services would mean
coordinating independent failure modes across a team of one, for a single
deployable product that doesn't yet need independent horizontal scaling of
ingest versus web serving. Building for a scale I'm not at yet is
premature, not responsible.

## Why explicit statistics, not an ML anomaly-detection library

An anomaly score can't explain itself. "2.8σ on 3.4× volume" is a sentence
someone can verify or argue with. In a product about money, an alert a
user can't interrogate is worse than an alert that was missed entirely —
trust is the actual product here, not just detection coverage.

## Deliberately out of scope

Things I considered and chose not to build, not things I ran out of time
for:

- **Multiple named watchlists.** The brief asks for "a watchlist,"
  singular. Named lists would mean real schema complexity for a feature
  nobody asked for.
- **A full seen/dismissed inbox with separate views.** My dismiss button
  already changes future ranking for real — that's the behavior the
  personalization model actually needs. A three-way filed/recoverable
  system (closer to Gmail's real model) is genuinely bigger scope, and it
  would conflate "important" (a scoring input here) with a separate
  navigational category.
- **Generic idempotency-key infrastructure.** The schema exists, but every
  write endpoint already gets real idempotency from unique constraints.
  Adding a parallel mechanism for a problem I don't have felt like
  complexity for its own sake.

## Stack

Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0 (sync) + PostgreSQL (Neon),
Jinja2 + HTMX + Tailwind CDN (server-rendered, no frontend build step),
APScheduler for in-process background jobs, yfinance for real market data
with a bounded simulated fallback, money stored as integer paise
throughout, deployed on Railway.

## Running it locally

```bash
git clone https://github.com/sahithi-v/smart-market-watchlist.git
cd smart-market-watchlist
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Create `.env` in the repo root:

```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
SECRET_KEY=any_random_string_here
NEWS_API_KEY=optional_from_newsapi.org
```

```bash
alembic upgrade head
python -m app.backfill_daily_bars
python -m uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000` — it redirects to `/login`. Background jobs
start automatically with the app.

## Tests

```bash
pytest tests/ -v
```

40 tests, all pure functions — detectors, cooldown, scoring, affinity,
presets, and full digest assembly — tested independently of the database.

## Full reasoning

Every decision above, and quite a few smaller ones, are written down in
[`DECISIONS.md`](./DECISIONS.md) as the project was built.