from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func

from app.db import get_db
from app.digest import build_digest
from app.models import Symbol, User, WatchlistItem, PriceTick, UserSettings
from app.signals.presets import PRESETS, DEFAULT_SENSITIVITY

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_user_optional(request: Request, db=Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter_by(id=user_id).first()


def _time_ago(ts_iso: str, now: datetime) -> str:
    ts = datetime.fromisoformat(ts_iso)
    delta_min = int((now - ts).total_seconds() // 60)
    if delta_min < 1:
        return "just now"
    if delta_min < 60:
        return f"{delta_min}m ago"
    delta_hr = delta_min // 60
    if delta_hr < 24:
        return f"{delta_hr}h ago"
    return f"{delta_hr // 24}d ago"


def _format_digest_items(items: list[dict], now: datetime) -> list[dict]:
    formatted = []
    for item in items:
        price = item["current_price_paise"]
        formatted.append({
            **item,
            "price_display": f"₹{price / 100:,.2f}" if price is not None else "—",
            "time_ago": _time_ago(item["ts"], now),
        })
    return formatted


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@router.get("/dashboard")
def dashboard_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
    db=Depends(get_db),
):
    if user is None:
        return RedirectResponse(url="/login")

    watchlist_rows = (
        db.query(WatchlistItem, Symbol)
        .join(Symbol, Symbol.id == WatchlistItem.symbol_id)
        .filter(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.pinned.desc(), WatchlistItem.position.asc())
        .all()
    )
    watchlist = [
        {"id": w.id, "ticker": s.ticker, "name": s.name,
         "pinned": w.pinned, "version": w.version}
        for w, s in watchlist_rows
    ]

    now = datetime.now(timezone.utc)
    digest_result = build_digest(db, user, now)
    digest_items = _format_digest_items(digest_result["items"], now)

    latest_tick_ts = (
        db.query(func.max(PriceTick.ts))
        .join(WatchlistItem, WatchlistItem.symbol_id == PriceTick.symbol_id)
        .filter(WatchlistItem.user_id == user.id)
        .scalar()
    )
    data_freshness = _time_ago(latest_tick_ts.isoformat(), now) if latest_tick_ts else None

    return templates.TemplateResponse(
        request, "dashboard.html",
        {
            "user": user, "watchlist": watchlist,
            "digest_items": digest_items,
            "other_count": digest_result["other_count"],
            "empty_reason": digest_result["empty_reason"],
            "data_freshness": data_freshness,
        },
    )


@router.get("/settings")
def settings_page(
    request: Request,
    user: User = Depends(get_current_user_optional),
    db=Depends(get_db),
):
    if user is None:
        return RedirectResponse(url="/login")

    row = db.query(UserSettings).filter_by(user_id=user.id).first()
    current = row.sensitivity if row else DEFAULT_SENSITIVITY

    return templates.TemplateResponse(
        request, "settings.html",
        {"user": user, "current_sensitivity": current, "presets": PRESETS},
    )