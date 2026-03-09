"""
Screener logika – ticker szűrés kritériumok alapján
"""
import pandas as pd
from data.db import get_session, Ticker, Fundamental, Technical, Score
from datetime import date


def get_screener_data(profile: str = "balanced", min_score: float = 0) -> pd.DataFrame:
    """
    Visszaad egy DataFrame-et az összes tickerről a legfrissebb
    fundamentum, technikai és score adatokkal.
    """
    session = get_session()
    try:
        tickers = session.query(Ticker).filter_by(active=True).all()
        rows = []
        for t in tickers:
            fund = (session.query(Fundamental)
                    .filter_by(ticker_id=t.id)
                    .order_by(Fundamental.date.desc())
                    .first())
            tech = (session.query(Technical)
                    .filter_by(ticker_id=t.id)
                    .order_by(Technical.date.desc())
                    .first())
            score = (session.query(Score)
                     .filter_by(ticker_id=t.id, profile=profile)
                     .order_by(Score.date.desc())
                     .first())

            row = {
                "symbol":   t.symbol,
                "name":     t.name or t.symbol,
                "sector":   t.sector or "",
                "exchange": t.exchange or "",
            }
            if fund:
                row.update({
                    "pe_ratio":    fund.pe_ratio,
                    "peg_ratio":   fund.peg_ratio,
                    "roe":         round(fund.roe * 100, 1) if fund.roe else None,
                    "eps_growth":  round(fund.eps_growth_yoy * 100, 1) if fund.eps_growth_yoy else None,
                    "debt_equity": round(fund.debt_equity / 100, 2) if fund.debt_equity and fund.debt_equity > 10 else fund.debt_equity,
                    "div_yield":   round(fund.div_yield * 100, 2) if fund.div_yield and fund.div_yield < 1 else fund.div_yield,
                    "market_cap":  fund.market_cap,
                    "beta":        fund.beta,
                })
            if tech:
                row.update({
                    "rsi_14": round(tech.rsi_14, 1) if tech.rsi_14 else None,
                    "ma_50":  tech.ma_50,
                    "ma_200": tech.ma_200,
                    "golden_cross": (tech.ma_50 > tech.ma_200) if tech.ma_50 and tech.ma_200 else None,
                })
            if score:
                row.update({
                    "fundamental_score": score.fundamental_score,
                    "technical_score":   score.technical_score,
                    "composite_score":   score.composite_score,
                    "signal":            score.signal,
                })
            rows.append(row)
        df = pd.DataFrame(rows)
        if "composite_score" in df.columns:
            df = df[df["composite_score"] >= min_score]
            df = df.sort_values("composite_score", ascending=False)
        return df
    finally:
        session.close()


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Dinamikus szűrők alkalmazása DataFrame-re"""
    result = df.copy()
    for col, (lo, hi) in filters.items():
        if col in result.columns:
            if lo is not None:
                result = result[result[col].fillna(-999) >= lo]
            if hi is not None:
                result = result[result[col].fillna(9999) <= hi]
    return result
