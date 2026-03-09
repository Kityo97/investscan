"""
InvestScan – Konfiguráció
API kulcsokat a .env fájlba tedd (minta: .env.example)
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── API kulcsok ──────────────────────────────────────────────
FMP_API_KEY        = os.getenv("FMP_API_KEY", "demo")          # https://financialmodelingprep.com
ALPHA_VANTAGE_KEY  = os.getenv("ALPHA_VANTAGE_KEY", "demo")   # https://www.alphavantage.co
FRED_API_KEY       = os.getenv("FRED_API_KEY", "")            # https://fred.stlouisfed.org

# ── Adatbázis ────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "investscan.db")
DB_URL  = f"sqlite:///{DB_PATH}"

# ── Adatfrissítés ────────────────────────────────────────────
REFRESH_HOUR   = 23       # CET – kereskedés zárta után
REFRESH_MINUTE = 0

# ── Scoring súlyok profilonként ──────────────────────────────
PROFILE_WEIGHTS = {
    "conservative": {"fundamental": 0.60, "technical": 0.20, "macro": 0.20},
    "balanced":     {"fundamental": 0.50, "technical": 0.30, "macro": 0.20},
    "growth":       {"fundamental": 0.40, "technical": 0.40, "macro": 0.20},
    "active":       {"fundamental": 0.20, "technical": 0.70, "macro": 0.10},
}

PROFILE_LABELS = {
    "conservative": "🛡️ Konzervatív",
    "balanced":     "⚖️ Kiegyensúlyozott",
    "growth":       "🚀 Növekedési",
    "active":       "⚡ Aktív / Technikai",
}

# ── Demo tickers (ha a felhasználó még nem adott meg sajátot) ─
DEMO_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "JPM", "JNJ", "V",
    "ASML", "SAP", "OR", "NESN.SW", "MC.PA",
]

# ── Szektrok és ETF-ek makróhoz ──────────────────────────────
SECTOR_ETFS = {
    "Tech":       "XLK",
    "Pénzügy":    "XLF",
    "Energia":    "XLE",
    "Egészség":   "XLV",
    "Fogyasztói": "XLY",
    "Ipar":       "XLI",
    "Közmű":      "XLU",
    "Ingatlan":   "XLRE",
}

MACRO_TICKERS = {
    "S&P 500":      "^GSPC",
    "NASDAQ":       "^IXIC",
    "VIX":          "^VIX",
    "Dollárindex":  "DX-Y.NYB",
    "Arany":        "GC=F",
    "Olaj (WTI)":   "CL=F",
    "10Y US kötvény": "^TNX",
}

FRED_SERIES = {
    "Fed kamatráta":   "FEDFUNDS",
    "CPI infláció":    "CPIAUCSL",
    "10Y-2Y spread":   "T10Y2Y",
    "Munkanélküliség": "UNRATE",
}
