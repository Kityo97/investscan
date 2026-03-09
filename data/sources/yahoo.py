"""
Yahoo Finance adatgyűjtő – yfinance wrapper
"""
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
import time
import logging

logger = logging.getLogger(__name__)


def fetch_price_history(symbol: str, period: str = "2y") -> pd.DataFrame:
    """OHLCV adatok letöltése. period: 1y, 2y, 5y, max"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, auto_adjust=True)
        if df.empty:
            logger.warning(f"Nincs ár adat: {symbol}")
            return pd.DataFrame()
        df.index = df.index.date
        df.index.name = "date"
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df["adj_close"] = df["close"]
        return df.dropna()
    except Exception as e:
        logger.error(f"Yahoo price hiba {symbol}: {e}")
        return pd.DataFrame()


def fetch_fundamentals(symbol: str) -> dict:
    """Alapvető fundamentális adatok yfinance-ből"""
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}

        def safe(key, default=None):
            v = info.get(key, default)
            return v if v not in [None, "N/A", ""] else default

        # EPS növekedés becslése
        eps_curr = safe("trailingEps")
        eps_fwd  = safe("forwardEps")
        eps_growth = None
        if eps_curr and eps_fwd and eps_curr != 0:
            eps_growth = (eps_fwd - eps_curr) / abs(eps_curr)

        return {
            "name":           safe("longName") or safe("shortName") or symbol,
            "exchange":       safe("exchange"),
            "sector":         safe("sector"),
            "industry":       safe("industry"),
            "market_cap":     safe("marketCap"),
            "pe_ratio":       safe("trailingPE"),
            "forward_pe":     safe("forwardPE"),
            "peg_ratio":      safe("pegRatio"),
            "pb_ratio":       safe("priceToBook"),
            "ps_ratio":       safe("priceToSalesTrailing12Months"),
            "ev_ebitda":      safe("enterpriseToEbitda"),
            "roe":            safe("returnOnEquity"),
            "roa":            safe("returnOnAssets"),
            "debt_equity":    safe("debtToEquity"),
            "current_ratio":  safe("currentRatio"),
            "gross_margin":   safe("grossMargins"),
            "eps":            eps_curr,
            "eps_growth_yoy": eps_growth,
            "revenue_growth": safe("revenueGrowth"),
            "div_yield":      safe("dividendYield"),
            "beta":           safe("beta"),
            "fcf_yield":      _calc_fcf_yield(t, safe("marketCap")),
        }
    except Exception as e:
        logger.error(f"Yahoo fundamentals hiba {symbol}: {e}")
        return {}


def _calc_fcf_yield(ticker_obj, market_cap):
    try:
        cf = ticker_obj.cashflow
        if cf is None or cf.empty:
            return None
        # Free Cash Flow = Operating CF - CapEx
        op_cf = cf.loc["Operating Cash Flow"].iloc[0] if "Operating Cash Flow" in cf.index else None
        capex = cf.loc["Capital Expenditure"].iloc[0] if "Capital Expenditure" in cf.index else 0
        if op_cf and market_cap and market_cap > 0:
            fcf = op_cf - abs(capex)
            return fcf / market_cap
        return None
    except:
        return None


def fetch_ticker_info(symbol: str) -> dict:
    """Rövid meta infó (név, szektor, tőzsde)"""
    try:
        info = yf.Ticker(symbol).info or {}
        return {
            "name":     info.get("longName") or info.get("shortName") or symbol,
            "exchange": info.get("exchange", ""),
            "sector":   info.get("sector", ""),
            "industry": info.get("industry", ""),
        }
    except:
        return {"name": symbol, "exchange": "", "sector": "", "industry": ""}


def fetch_analyst_ratings(symbol: str) -> dict:
    """Analyst ajánlások összesítése"""
    try:
        t = yf.Ticker(symbol)
        recs = t.recommendations
        if recs is None or recs.empty:
            return {}
        latest = recs.tail(10)
        counts = {}
        for col in ["strongBuy", "buy", "hold", "sell", "strongSell"]:
            if col in latest.columns:
                counts[col] = int(latest[col].sum())
        return counts
    except:
        return {}


def fetch_earnings_calendar(symbol: str) -> dict:
    """Következő gyorsjelentés dátuma"""
    try:
        info = yf.Ticker(symbol).info or {}
        return {
            "next_earnings": info.get("earningsTimestamp"),
            "eps_estimate":  info.get("epsForward"),
        }
    except:
        return {}
