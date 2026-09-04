from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from app.rolling_stats import run_rolling_stats
from datetime import datetime
from app.ingest import run_ingest
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.auth import router as auth_router
from app.watchlist import router as watchlist_router
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_ingest, IntervalTrigger(seconds=15), id="ingest", replace_existing=True)
    scheduler.add_job(run_rolling_stats, IntervalTrigger(hours=1), id="rolling_stats", replace_existing=True, next_run_time=datetime.now())
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Smart Market Watchlist", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.include_router(auth_router)
app.include_router(watchlist_router)


@app.get("/api/health")
def health():
    return {"ok": True}