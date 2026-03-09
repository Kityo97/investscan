"""
Adatbázis modellek és inicializálás – SQLite / SQLAlchemy
"""
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    Date, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from config import DB_URL

Base = declarative_base()
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


# ─────────────────────────────────────────────
class Ticker(Base):
    __tablename__ = "tickers"
    id          = Column(Integer, primary_key=True)
    symbol      = Column(String(20), unique=True, nullable=False)
    name        = Column(String(200))
    exchange    = Column(String(50))
    sector      = Column(String(100))
    industry    = Column(String(100))
    asset_type  = Column(String(20), default="stock")  # stock / etf / commodity
    market      = Column(String(10), default="US")     # US / EU
    active      = Column(Boolean, default=True)
    added_at    = Column(DateTime, default=datetime.utcnow)

    prices       = relationship("Price",       back_populates="ticker", cascade="all, delete")
    fundamentals = relationship("Fundamental", back_populates="ticker", cascade="all, delete")
    technicals   = relationship("Technical",   back_populates="ticker", cascade="all, delete")
    scores       = relationship("Score",       back_populates="ticker", cascade="all, delete")


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("ticker_id", "date"),)
    id        = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date      = Column(Date, nullable=False)
    open      = Column(Float)
    high      = Column(Float)
    low       = Column(Float)
    close     = Column(Float)
    volume    = Column(Float)
    adj_close = Column(Float)
    ticker    = relationship("Ticker", back_populates="prices")


class Fundamental(Base):
    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("ticker_id", "date"),)
    id             = Column(Integer, primary_key=True)
    ticker_id      = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date           = Column(Date, nullable=False)
    pe_ratio       = Column(Float)
    forward_pe     = Column(Float)
    peg_ratio      = Column(Float)
    pb_ratio       = Column(Float)
    ps_ratio       = Column(Float)
    ev_ebitda      = Column(Float)
    roe            = Column(Float)
    roa            = Column(Float)
    debt_equity    = Column(Float)
    current_ratio  = Column(Float)
    fcf_yield      = Column(Float)
    eps            = Column(Float)
    eps_growth_yoy = Column(Float)
    revenue_growth = Column(Float)
    gross_margin   = Column(Float)
    div_yield      = Column(Float)
    div_growth_5y  = Column(Float)
    market_cap     = Column(Float)
    beta           = Column(Float)
    ticker         = relationship("Ticker", back_populates="fundamentals")


class Technical(Base):
    __tablename__ = "technicals"
    __table_args__ = (UniqueConstraint("ticker_id", "date"),)
    id           = Column(Integer, primary_key=True)
    ticker_id    = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date         = Column(Date, nullable=False)
    rsi_14       = Column(Float)
    macd         = Column(Float)
    macd_signal  = Column(Float)
    macd_hist    = Column(Float)
    ma_20        = Column(Float)
    ma_50        = Column(Float)
    ma_200       = Column(Float)
    bb_upper     = Column(Float)
    bb_middle    = Column(Float)
    bb_lower     = Column(Float)
    volume_avg20 = Column(Float)
    atr_14       = Column(Float)
    ticker       = relationship("Ticker", back_populates="technicals")


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("ticker_id", "date", "profile"),)
    id                  = Column(Integer, primary_key=True)
    ticker_id           = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date                = Column(Date, nullable=False)
    profile             = Column(String(20))
    fundamental_score   = Column(Float)
    technical_score     = Column(Float)
    macro_score         = Column(Float)
    composite_score     = Column(Float)
    signal              = Column(String(20))  # BUY / HOLD / WATCH / AVOID
    ticker              = relationship("Ticker", back_populates="scores")


class MacroData(Base):
    __tablename__ = "macro_data"
    __table_args__ = (UniqueConstraint("series_id", "date"),)
    id        = Column(Integer, primary_key=True)
    series_id = Column(String(50), nullable=False)
    name      = Column(String(100))
    date      = Column(Date, nullable=False)
    value     = Column(Float)


class Watchlist(Base):
    __tablename__ = "watchlist"
    id         = Column(Integer, primary_key=True)
    symbol     = Column(String(20), nullable=False, unique=True)
    name       = Column(String(200))
    buy_price  = Column(Float)
    target     = Column(Float)
    stop_loss  = Column(Float)
    notes      = Column(Text)
    alert_score = Column(Float)
    added_at   = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Táblák létrehozása ha nem léteznek"""
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
