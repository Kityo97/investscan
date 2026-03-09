"""
Technikai indikátorok számítása pandas-ta segítségével
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False
    logger.warning("pandas-ta nem elérhető, kézi számítás fut")


def compute_technicals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bemenet: OHLCV DataFrame (date index)
    Kimenet: DataFrame technikai indikátorokkal
    """
    if df.empty or len(df) < 20:
        return pd.DataFrame()

    result = df.copy()

    try:
        if HAS_PANDAS_TA:
            result.ta.rsi(length=14, append=True)
            result.ta.macd(fast=12, slow=26, signal=9, append=True)
            result.ta.sma(length=20, append=True)
            result.ta.sma(length=50, append=True)
            result.ta.sma(length=200, append=True)
            result.ta.bbands(length=20, std=2, append=True)
            result.ta.atr(length=14, append=True)

            rename_map = {}
            for col in result.columns:
                cl = col.upper()
                if "RSI_14" in cl:         rename_map[col] = "rsi_14"
                elif "MACD_12_26_9" == cl: rename_map[col] = "macd"
                elif "MACDS_12_26_9" == cl:rename_map[col] = "macd_signal"
                elif "MACDH_12_26_9" == cl:rename_map[col] = "macd_hist"
                elif "SMA_20" == cl:       rename_map[col] = "ma_20"
                elif "SMA_50" == cl:       rename_map[col] = "ma_50"
                elif "SMA_200" == cl:      rename_map[col] = "ma_200"
                elif "BBU_20_2.0" == cl:   rename_map[col] = "bb_upper"
                elif "BBM_20_2.0" == cl:   rename_map[col] = "bb_middle"
                elif "BBL_20_2.0" == cl:   rename_map[col] = "bb_lower"
                elif "ATRR_14" in cl or "ATR_14" == cl: rename_map[col] = "atr_14"
            result = result.rename(columns=rename_map)
        else:
            # Kézi számítás
            result = _manual_indicators(result)

        # Volume 20 napos átlag
        result["volume_avg20"] = result["volume"].rolling(20).mean()

        # Csak szükséges oszlopok
        keep = ["open","high","low","close","volume","adj_close",
                "rsi_14","macd","macd_signal","macd_hist",
                "ma_20","ma_50","ma_200","bb_upper","bb_middle","bb_lower",
                "volume_avg20","atr_14"]
        existing = [c for c in keep if c in result.columns]
        return result[existing]

    except Exception as e:
        logger.error(f"Technikai indikátor hiba: {e}")
        return df


def _manual_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Kézi RSI, MACD, SMA számítás pandas-ta nélkül"""
    close = df["close"]

    # RSI
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"]        = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    # Moving averages
    df["ma_20"]  = close.rolling(20).mean()
    df["ma_50"]  = close.rolling(50).mean()
    df["ma_200"] = close.rolling(200).mean()

    # Bollinger Bands
    df["bb_middle"] = close.rolling(20).mean()
    std = close.rolling(20).std()
    df["bb_upper"] = df["bb_middle"] + 2 * std
    df["bb_lower"] = df["bb_middle"] - 2 * std

    # ATR
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"]  - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    return df


def get_signals(tech_row) -> dict:
    """
    Jelzések generálása egy Technical rekordból.
    Visszaad egy dict-et: {'golden_cross': True, 'rsi_oversold': False, ...}
    """
    if tech_row is None:
        return {}

    signals = {}

    # Golden / Death Cross
    if tech_row.ma_50 and tech_row.ma_200:
        signals["golden_cross"] = tech_row.ma_50 > tech_row.ma_200
        signals["death_cross"]  = tech_row.ma_50 < tech_row.ma_200

    # RSI zónák
    if tech_row.rsi_14:
        signals["rsi_oversold"]  = tech_row.rsi_14 < 30
        signals["rsi_overbought"]= tech_row.rsi_14 > 70
        signals["rsi_bullish"]   = 45 <= tech_row.rsi_14 <= 65

    # MACD bullish
    if tech_row.macd and tech_row.macd_signal:
        signals["macd_bullish"] = tech_row.macd > tech_row.macd_signal
        signals["macd_bearish"] = tech_row.macd < tech_row.macd_signal

    return signals
