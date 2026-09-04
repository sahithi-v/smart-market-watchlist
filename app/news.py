import httpx
from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import Symbol, User

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/{ticker}")
def get_news(ticker: str, user: User = Depends(get_current_user), db=Depends(get_db)):
    if not settings.news_api_key:
        return {"headlines": [], "unavailable": True}

    symbol = db.query(Symbol).filter_by(ticker=ticker.upper()).first()
    if symbol is None:
        raise HTTPException(status_code=404, detail="Unknown ticker")

    try:
        resp = httpx.get(
            "https://newsapi.org/v2/everything",
            params={
                "qInTitle": symbol.name,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 5,
                "apiKey": settings.news_api_key,
            },
            timeout=5.0,
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except (httpx.HTTPError, httpx.TimeoutException):
        return {"headlines": [], "unavailable": True}

    headlines = [
        {"title": a["title"], "url": a["url"], "source": a["source"]["name"]}
        for a in articles[:5]
    ]
    return {"headlines": headlines, "unavailable": False}