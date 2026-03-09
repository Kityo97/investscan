"""
FRED (Federal Reserve Economic Data) adapter
API kulcs: https://fred.stlouisfed.org/docs/api/api_key.html  (ingyenes)
"""
import requests
import pandas as pd
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def fetch_series(series_id: str, api_key: str, start: str = None, limit: int = 120) -> pd.Series:
    """FRED idősor letöltése. Visszaad egy pd.Series date index-szel."""
    if not api_key:
        logger.warning("FRED API kulcs nincs beállítva – demo adat")
        return pd.Series(dtype=float)
    try:
        params = {
            "series_id":    series_id,
            "api_key":      api_key,
            "file_type":    "json",
            "sort_order":   "desc",
            "limit":        limit,
        }
        if start:
            params["observation_start"] = start
        r = requests.get(FRED_BASE, params=params, timeout=15)
        r.raise_for_status()
        data = r.json().get("observations", [])
        records = [(d["date"], float(d["value"])) for d in data if d["value"] != "."]
        if not records:
            return pd.Series(dtype=float)
        df = pd.DataFrame(records, columns=["date", "value"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        return df["value"]
    except Exception as e:
        logger.error(f"FRED hiba {series_id}: {e}")
        return pd.Series(dtype=float)


def fetch_yield_curve(api_key: str) -> pd.Series:
    """10Y-2Y spread – invertált = recessziós jel"""
    return fetch_series("T10Y2Y", api_key, limit=200)


def fetch_fed_rate(api_key: str) -> pd.Series:
    return fetch_series("FEDFUNDS", api_key, limit=60)


def fetch_cpi(api_key: str) -> pd.Series:
    return fetch_series("CPIAUCSL", api_key, limit=36)


def fetch_unemployment(api_key: str) -> pd.Series:
    return fetch_series("UNRATE", api_key, limit=36)


def get_macro_score(api_key: str) -> float:
    """
    Makro score számítása 0-100 skálán.
    Magasabb = kedvezőbb makro környezet részvényeknek.
    """
    score = 50.0  # neutral alapértelmezés

    try:
        # Yield curve
        yc = fetch_yield_curve(api_key)
        if not yc.empty:
            latest_yc = yc.iloc[-1]
            if latest_yc > 0.5:
                score += 15   # normál görbe
            elif latest_yc > 0:
                score += 5
            elif latest_yc > -0.5:
                score -= 10   # enyhén invertált
            else:
                score -= 20   # erősen invertált = recessziós jel

        # Fed kamatpálya – csökkenő kamat = pozitív
        fed = fetch_fed_rate(api_key)
        if len(fed) >= 3:
            trend = fed.iloc[-1] - fed.iloc[-3]
            if trend < -0.1:
                score += 10   # kamatcsökkentés
            elif trend > 0.1:
                score -= 10   # kamatemelés

    except Exception as e:
        logger.error(f"Makro score hiba: {e}")

    return max(0, min(100, score))
