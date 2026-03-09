"""
Napi adatgyűjtő – betölti az összes aktív ticker adatát az adatbázisba
Futtatás: python collector.py  (vagy APScheduler hívja)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging
from datetime import date, timedelta
import pandas as pd
from sqlalchemy.exc import IntegrityError

from data.db import get_session, init_db, Ticker, Price, Fundamental, Technical, Score
from data.sources.yahoo import fetch_price_history, fetch_fundamentals
from engine.indicators import compute_technicals
from engine.scoring import compute_scores
from config import PROFILE_WEIGHTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def upsert_prices(session, ticker_id: int, df: pd.DataFrame):
    """Ár adatok mentése – duplikátumok kihagyása"""
    for dt, row in df.iterrows():
        existing = session.query(Price).filter_by(ticker_id=ticker_id, date=dt).first()
        if existing:
            continue
        p = Price(
            ticker_id=ticker_id, date=dt,
            open=row.get("open"), high=row.get("high"),
            low=row.get("low"), close=row.get("close"),
            volume=row.get("volume"), adj_close=row.get("adj_close"),
        )
        session.add(p)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()


def upsert_fundamentals(session, ticker_id: int, data: dict):
    today = date.today()
    existing = session.query(Fundamental).filter_by(ticker_id=ticker_id, date=today).first()
    if existing:
        return
    f = Fundamental(ticker_id=ticker_id, date=today, **{
        k: v for k, v in data.items()
        if k in Fundamental.__table__.columns.keys() and k not in ("id", "ticker_id", "date")
    })
    session.add(f)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()


def upsert_technicals(session, ticker_id: int, df_tech: pd.DataFrame):
    today = date.today()
    if df_tech.empty:
        return
    row = df_tech.iloc[-1]
    existing = session.query(Technical).filter_by(ticker_id=ticker_id, date=today).first()
    if existing:
        return
    t = Technical(
        ticker_id=ticker_id, date=today,
        rsi_14=row.get("rsi_14"), macd=row.get("macd"),
        macd_signal=row.get("macd_signal"), macd_hist=row.get("macd_hist"),
        ma_20=row.get("ma_20"), ma_50=row.get("ma_50"), ma_200=row.get("ma_200"),
        bb_upper=row.get("bb_upper"), bb_middle=row.get("bb_middle"), bb_lower=row.get("bb_lower"),
        volume_avg20=row.get("volume_avg20"), atr_14=row.get("atr_14"),
    )
    session.add(t)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()


def collect_ticker(symbol: str, session):
    logger.info(f"  → {symbol}")
    db_ticker = session.query(Ticker).filter_by(symbol=symbol).first()

    # Fundamentumok
    fund_data = fetch_fundamentals(symbol)
    if not fund_data:
        logger.warning(f"    Nincs fundamentum adat: {symbol}")
        return

    # Ticker meta frissítése / létrehozása
    if not db_ticker:
        db_ticker = Ticker(
            symbol=symbol,
            name=fund_data.get("name", symbol),
            exchange=fund_data.get("exchange", ""),
            sector=fund_data.get("sector", ""),
            industry=fund_data.get("industry", ""),
        )
        session.add(db_ticker)
        session.flush()
    else:
        db_ticker.name     = fund_data.get("name", db_ticker.name) or db_ticker.name
        db_ticker.sector   = fund_data.get("sector", db_ticker.sector) or db_ticker.sector
        db_ticker.industry = fund_data.get("industry", db_ticker.industry) or db_ticker.industry
        session.commit()

    # Árak
    price_df = fetch_price_history(symbol, period="2y")
    if not price_df.empty:
        upsert_prices(session, db_ticker.id, price_df)

    # Fundamentumok mentése
    upsert_fundamentals(session, db_ticker.id, fund_data)

    # Technikai indikátorok
    if not price_df.empty:
        tech_df = compute_technicals(price_df)
        upsert_technicals(session, db_ticker.id, tech_df)

    # Score számítás minden profilhoz
    if not price_df.empty:
        fund_row = session.query(Fundamental).filter_by(ticker_id=db_ticker.id).order_by(Fundamental.date.desc()).first()
        tech_row = session.query(Technical).filter_by(ticker_id=db_ticker.id).order_by(Technical.date.desc()).first()
        scores = compute_scores(fund_row, tech_row, macro_score=50.0)
        today = date.today()
        for profile, weights in PROFILE_WEIGHTS.items():
            existing = session.query(Score).filter_by(ticker_id=db_ticker.id, date=today, profile=profile).first()
            if existing:
                continue
            fs = scores.get("fundamental", 50)
            ts = scores.get("technical", 50)
            ms = scores.get("macro", 50)
            composite = fs * weights["fundamental"] + ts * weights["technical"] + ms * weights["macro"]
            signal = "BUY" if composite >= 70 else "WATCH" if composite >= 55 else "HOLD" if composite >= 40 else "AVOID"
            s = Score(
                ticker_id=db_ticker.id, date=today, profile=profile,
                fundamental_score=round(fs, 1),
                technical_score=round(ts, 1),
                macro_score=round(ms, 1),
                composite_score=round(composite, 1),
                signal=signal,
            )
            session.add(s)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()

    logger.info(f"    ✓ {symbol} kész")


def run_collection(symbols: list):
    init_db()
    session = get_session()
    logger.info(f"Adatgyűjtés indul – {len(symbols)} ticker")
    for sym in symbols:
        try:
            collect_ticker(sym.upper().strip(), session)
        except Exception as e:
            logger.error(f"Hiba {sym}: {e}")
    session.close()
    logger.info("Adatgyűjtés befejezve ✓")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", help="Ticker szimbólumok")
    parser.add_argument("--file", help="Szimbólumok fájlból (soronként)")
    args = parser.parse_args()

    symbols = []
    if args.tickers:
        symbols = args.tickers
    elif args.file:
        with open(args.file) as f:
            symbols = [l.strip() for l in f if l.strip()]
    else:
        from config import DEMO_TICKERS
        symbols = DEMO_TICKERS

    run_collection(symbols)
