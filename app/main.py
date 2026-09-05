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
from app.signal_engine import run_signal_engine
from app.digest import router as digest_router
from app.events import router as events_router
from app.pages import router as pages_router
from app.user_settings import router as user_settings_router
from app.news import router as news_router
from fastapi.staticfiles import StaticFiles
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_ingest, IntervalTrigger(seconds=15), id="ingest", replace_existing=True)
    scheduler.add_job(run_rolling_stats, IntervalTrigger(hours=1), id="rolling_stats", replace_existing=True, next_run_time=datetime.now())
    scheduler.add_job(run_signal_engine, IntervalTrigger(seconds=30), id="signal_engine", replace_existing=True, next_run_time=datetime.now())
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Smart Market Watchlist", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(digest_router)
app.include_router(events_router)
app.include_router(pages_router)
app.include_router(user_settings_router)
app.include_router(news_router)

@app.get("/api/health")
def health():
    return {"ok": True}