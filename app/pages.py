from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_db
from app.models import Symbol, User, WatchlistItem

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_current_user_optional(request: Request, db=Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter_by(id=user_id).first()


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

    return templates.TemplateResponse(
        request, "dashboard.html", {"user": user, "watchlist": watchlist}
    )