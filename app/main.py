from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from app.ingest import run_ingest

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_ingest, IntervalTrigger(seconds=15), id="ingest", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Smart Market Watchlist", lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"ok": True}