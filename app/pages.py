from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_db
from app.models import User

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
def dashboard_page(request: Request, user: User = Depends(get_current_user_optional)):
    if user is None:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})