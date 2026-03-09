# 📈 InvestScan – Befektetési Figyelő Dashboard

Személyre szabott részvény- és befektetési figyelő alkalmazás Python/Streamlit alapon.

## 🚀 Gyors indítás

### 1. Telepítés
```bash
pip install -r requirements.txt
```

### 2. API kulcsok beállítása
```bash
cp .env.example .env
# Szerkeszd a .env fájlt a kulcsaiddal
```

> **A Yahoo Finance (yfinance) ingyenes és API kulcs nélkül is működik!**
> Az FMP, Alpha Vantage és FRED kulcsok opcionálisak.

### 3. Indítás
```bash
streamlit run app.py
```

## 📋 Funkciók

| Oldal | Funkció |
|-------|---------|
| 🏠 Főoldal | Befektetői személyiségtest (8 kérdés → 4 profil) |
| 📊 Dashboard | Napi top pick-ek score alapján, szektor heatmap |
| 📈 Részvény | Interaktív candlestick chart, technikai indikátorok, fundamentumok |
| 🔍 Screener | Szűrő P/E, RSI, Score alapján – CSV export |
| 🌍 Makro | Fed kamatok, infláció, yield curve, VIX, szektor ETF-ek |
| ⭐ Watchlist | Saját lista, P&L követés, célár, stop loss |
| ⚙️ Adatkezelés | Adatgyűjtés indítása, API státusz, DB kezelés |

## 🏗️ Architektúra

```
Yahoo Finance → yfinance adapter
     ↓
SQLite adatbázis (prices, fundamentals, technicals, scores)
     ↓
Elemző motor (RSI, MACD, MA, Bollinger, Scoring)
     ↓
Streamlit Dashboard
```

## 📊 Befektetői profilok

| Profil | Leírás | Scoring súlyok |
|--------|---------|----------------|
| 🛡️ Konzervatív | Osztalék, stabil FCF | Fund 60%, Tech 20%, Makro 20% |
| ⚖️ Kiegyensúlyozott | GARP stratégia | Fund 50%, Tech 30%, Makro 20% |
| 🚀 Növekedési | EPS/Revenue növekedés | Fund 40%, Tech 40%, Makro 20% |
| ⚡ Aktív/Technikai | Momentum, rövid táv | Tech 70%, Fund 20%, Makro 10% |

## 🔑 Ingyenes API-k

- **Yahoo Finance** – yfinance, korlátlan
- **Financial Modeling Prep** – [fmp.com](https://financialmodelingprep.com) – 250 req/nap ingyen
- **Alpha Vantage** – [alphavantage.co](https://www.alphavantage.co) – 25 req/nap ingyen
- **FRED** – [stlouisfed.org](https://fred.stlouisfed.org) – teljesen ingyenes

## ⚠️ Jogi nyilatkozat

Az InvestScan kizárólag tájékoztatási célokat szolgál. **Nem minősül befektetési tanácsadásnak.**
A múltbeli teljesítmény nem garantálja a jövőbeli hozamokat. Befektetés előtt konzultálj pénzügyi szakértővel.
