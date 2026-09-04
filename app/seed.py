from app.db import SessionLocal
from app.models import Symbol

SEED_SYMBOLS = [
    ("INFY", "Infosys Ltd", "NSE"),
    ("TCS", "Tata Consultancy Services", "NSE"),
    ("HDFCBANK", "HDFC Bank Ltd", "NSE"),
    ("RELIANCE", "Reliance Industries", "NSE"),
    ("TATAMOTORS", "Tata Motors Ltd", "NSE"),
]


def seed():
    db = SessionLocal()
    try:
        for ticker, name, exchange in SEED_SYMBOLS:
            if not db.query(Symbol).filter_by(ticker=ticker).first():
                db.add(Symbol(ticker=ticker, name=name, exchange=exchange))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()