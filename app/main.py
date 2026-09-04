from fastapi import FastAPI

app = FastAPI(title="Smart Market Watchlist")


@app.get("/api/health")
def health():
    return {"ok": True}