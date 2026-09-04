from app.db import SessionLocal
from app.models import Symbol

SEED_SYMBOLS = [
    ("INFY", "Infosys Ltd", "NSE"),
    ("TCS", "Tata Consultancy Services", "NSE"),
    ("HDFCBANK", "HDFC Bank Ltd", "NSE"),
    ("RELIANCE", "Reliance Industries", "NSE"),
    ("ICICIBANK", "ICICI Bank Ltd", "NSE"),
    ("SBIN", "State Bank of India", "NSE"),
    ("ITC", "ITC Ltd", "NSE"),
    ("BHARTIARTL", "Bharti Airtel Ltd", "NSE"),
    ("KOTAKBANK", "Kotak Mahindra Bank Ltd", "NSE"),
    ("LT", "Larsen & Toubro Ltd", "NSE"),
    ("AXISBANK", "Axis Bank Ltd", "NSE"),
    ("MARUTI", "Maruti Suzuki India Ltd", "NSE"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries", "NSE"),
    ("WIPRO", "Wipro Ltd", "NSE"),
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