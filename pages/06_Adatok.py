"""
Adatkezelés – Adatgyűjtés indítása, DB állapot, scheduler
"""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.db import get_session, init_db, Ticker, Price, Score, Fundamental, Technical
from data.collector import run_collection, collect_ticker
from config import DEMO_TICKERS, PROFILE_WEIGHTS
from datetime import date, datetime

st.set_page_config(page_title="Adatkezelés – InvestScan", page_icon="⚙️", layout="wide")

st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#F0F4F8;}
[data-testid="stSidebar"]{background:#1E3A5F;}
[data-testid="stSidebar"] *{color:#ECF0F1!important;}
.page-header{background:linear-gradient(135deg,#1E3A5F 0%,#2E6DA4 100%);
  color:white;padding:20px 24px;border-radius:12px;margin-bottom:20px;}
.page-header h1{color:white!important;margin:0;}
.page-header p{color:#BDC3C7;margin:4px 0 0 0;}
.metric-card{background:white;border-radius:12px;padding:16px;
  box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:4px solid #2E6DA4;margin-bottom:8px;}
.card-title{font-size:.78em;color:#7F8C8D;text-transform:uppercase;}
.card-value{font-size:1.7em;font-weight:bold;color:#1E3A5F;}
</style>""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h1>⚙️ Adatkezelés</h1>
  <p>Adatgyűjtés indítása, adatbázis állapot, API beállítások</p>
</div>
""", unsafe_allow_html=True)

init_db()

# ── DB állapot ────────────────────────────────────────────────
st.markdown("### 📊 Adatbázis állapot")

session = get_session()
n_tickers   = session.query(Ticker).filter_by(active=True).count()
n_prices    = session.query(Price).count()
n_scores    = session.query(Score).count()
n_fund      = session.query(Fundamental).count()
n_tech      = session.query(Technical).count()
last_score  = session.query(Score).order_by(Score.date.desc()).first()
session.close()

c1, c2, c3, c4, c5 = st.columns(5)
stats = [
    ("Aktív tickerek", n_tickers, c1),
    ("Ár rekordok",    n_prices,  c2),
    ("Score rekordok", n_scores,  c3),
    ("Fundamentumok",  n_fund,    c4),
    ("Technicai rek.", n_tech,    c5),
]
for label, val, col in stats:
    with col:
        st.markdown(f"""<div class="metric-card">
          <div class="card-title">{label}</div>
          <div class="card-value">{val:,}</div>
        </div>""", unsafe_allow_html=True)

if last_score:
    st.info(f"📅 Legutóbbi score frissítés: **{last_score.date}**")
else:
    st.warning("⚠️ Még nincsenek score adatok. Indítsd el az adatgyűjtést!")

st.markdown("---")

# ── Adatgyűjtés ──────────────────────────────────────────────
st.markdown("### 🔄 Adatgyűjtés indítása")

session = get_session()
all_tickers = [t.symbol for t in session.query(Ticker).filter_by(active=True).all()]
session.close()

col_opt, col_run = st.columns([2, 1])
with col_opt:
    if all_tickers:
        selected = st.multiselect(
            "Tickerek kiválasztása (üres = összes)",
            options=all_tickers,
            default=[],
        )
        run_symbols = selected if selected else all_tickers
        st.caption(f"→ {len(run_symbols)} ticker lesz feldolgozva")
    else:
        st.warning("Nincsenek tickerek. Add hozzá őket a Screener oldalon!")
        run_symbols = []

    # Demo tickerek gyors hozzáadása
    if st.checkbox("Demo tickerek hozzáadása (15 US blue chip)"):
        session = get_session()
        added = 0
        for sym in DEMO_TICKERS:
            if not session.query(Ticker).filter_by(symbol=sym).first():
                session.add(Ticker(symbol=sym, name=sym, market="US", asset_type="stock"))
                added += 1
        session.commit()
        session.close()
        if added > 0:
            st.success(f"✅ {added} demo ticker hozzáadva!")
            st.rerun()

with col_run:
    st.markdown("<br>", unsafe_allow_html=True)
    collect_all = st.button("🚀 Adatgyűjtés most", type="primary",
                            disabled=len(run_symbols) == 0,
                            use_container_width=True,
                            help="Letölti az áradatokat, fundamentumokat, kiszámolja a score-okat")

if collect_all and run_symbols:
    progress_bar = st.progress(0, text="Adatgyűjtés folyamatban...")
    status_text  = st.empty()
    log_container = st.container()

    for i, sym in enumerate(run_symbols):
        status_text.markdown(f"⏳ Feldolgozás: **{sym}** ({i+1}/{len(run_symbols)})")
        try:
            session = get_session()
            collect_ticker(sym, session)
            session.close()
            with log_container:
                st.success(f"✅ {sym}")
        except Exception as e:
            with log_container:
                st.error(f"❌ {sym}: {e}")
        progress_bar.progress((i + 1) / len(run_symbols),
                              text=f"Feldolgozva: {i+1}/{len(run_symbols)}")

    status_text.markdown("🎉 **Adatgyűjtés befejezve!**")
    progress_bar.progress(1.0)
    st.balloons()
    st.rerun()

st.markdown("---")

# ── Egy ticker gyors frissítése ──────────────────────────────
st.markdown("### ⚡ Egyedi ticker gyors frissítése")
col_q1, col_q2 = st.columns([2, 1])
with col_q1:
    quick_sym = st.text_input("Szimbólum", placeholder="pl. AAPL").upper().strip()
with col_q2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Frissítés", disabled=not quick_sym):
        if quick_sym:
            with st.spinner(f"Feldolgozás: {quick_sym}..."):
                try:
                    session = get_session()
                    collect_ticker(quick_sym, session)
                    session.close()
                    st.success(f"✅ {quick_sym} frissítve!")
                except Exception as e:
                    st.error(f"❌ Hiba: {e}")

st.markdown("---")

# ── API kulcsok státusza ──────────────────────────────────────
st.markdown("### 🔑 API kulcsok beállítása")
st.info("""Hozz létre egy `.env` fájlt a projekt gyökérkönyvtárában a következő tartalommal:
```
FMP_API_KEY=ide_a_kulcsod
ALPHA_VANTAGE_KEY=ide_a_kulcsod  
FRED_API_KEY=ide_a_kulcsod
```
""")

from config import FMP_API_KEY, ALPHA_VANTAGE_KEY, FRED_API_KEY

api_status = [
    ("Yahoo Finance (yfinance)", "✅ Ingyenes, mindig elérhető", "#27AE60"),
    ("Financial Modeling Prep",  "✅ Beállítva" if FMP_API_KEY != "demo" else "⚠️ Demo kulcs (korlátozott)", "#27AE60" if FMP_API_KEY != "demo" else "#F39C12"),
    ("Alpha Vantage",            "✅ Beállítva" if ALPHA_VANTAGE_KEY != "demo" else "⚠️ Demo kulcs", "#27AE60" if ALPHA_VANTAGE_KEY != "demo" else "#F39C12"),
    ("FRED (Fed adatok)",        "✅ Beállítva" if FRED_API_KEY else "❌ Nincs beállítva (makro oldal korlátozott)", "#27AE60" if FRED_API_KEY else "#E74C3C"),
]

for name, status, color in api_status:
    st.markdown(f"""<div style="background:white;border-radius:8px;padding:10px 16px;
      margin:4px 0;box-shadow:0 1px 4px rgba(0,0,0,.06);border-left:4px solid {color}">
      <strong>{name}</strong> &nbsp;→&nbsp; <span style="color:{color}">{status}</span>
    </div>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 📥 DB reset (vészhelyzet)")
with st.expander("⚠️ Adatbázis törlése"):
    st.warning("Ez törli az összes letöltött adatot! (A ticker lista megmarad)")
    if st.button("🗑️ Score és ár adatok törlése", type="secondary"):
        session = get_session()
        session.query(Score).delete()
        session.query(Price).delete()
        session.query(Fundamental).delete()
        session.query(Technical).delete()
        session.commit()
        session.close()
        st.success("✅ Adatok törölve. Az adatgyűjtés újra futtatható.")
        st.rerun()
