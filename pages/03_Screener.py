"""
Screener – Manuális szűrő és ticker kezelés
"""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.db import get_session, Ticker, Score, Fundamental, Technical
from engine.scoring import score_to_signal
from config import PROFILE_LABELS, PROFILE_WEIGHTS
import yfinance as yf

st.set_page_config(page_title="Screener – InvestScan", page_icon="🔍", layout="wide")

st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#F0F4F8;}
[data-testid="stSidebar"]{background:#1E3A5F;}
[data-testid="stSidebar"] *{color:#ECF0F1!important;}
.page-header{background:linear-gradient(135deg,#1E3A5F 0%,#2E6DA4 100%);
  color:white;padding:20px 24px;border-radius:12px;margin-bottom:20px;}
.page-header h1{color:white!important;margin:0;}
.page-header p{color:#BDC3C7;margin:4px 0 0 0;}
</style>""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h1>🔍 Részvény Screener</h1>
  <p>Adj hozzá tickereket, szűrj mutatók alapján, exportálj</p>
</div>
""", unsafe_allow_html=True)

profile = st.session_state.get("profile", "balanced")


def load_all_tickers_with_scores(profile) -> pd.DataFrame:
    session = get_session()
    try:
        tickers = session.query(Ticker).filter_by(active=True).all()
        rows = []
        for t in tickers:
            fund = (session.query(Fundamental).filter_by(ticker_id=t.id)
                    .order_by(Fundamental.date.desc()).first())
            tech = (session.query(Technical).filter_by(ticker_id=t.id)
                    .order_by(Technical.date.desc()).first())
            score = (session.query(Score).filter_by(ticker_id=t.id, profile=profile)
                     .order_by(Score.date.desc()).first())

            row = {"Szimbólum": t.symbol, "Név": (t.name or t.symbol)[:30],
                   "Szektor": t.sector or "—", "Tőzsde": t.exchange or "—"}
            if fund:
                def f(v, mul=1, d=2):
                    if v is None: return None
                    val = v * mul if abs(v) < 2 and mul > 1 else v
                    return round(val, d)
                row.update({
                    "P/E":          f(fund.pe_ratio, d=1),
                    "PEG":          f(fund.peg_ratio),
                    "ROE %":        f(fund.roe, 100, 1),
                    "EPS Növ. %":   f(fund.eps_growth_yoy, 100, 1),
                    "Debt/Eq":      f(fund.debt_equity, d=2),
                    "Div. Yield %": f(fund.div_yield, 100, 2),
                    "Market Cap":   fund.market_cap,
                    "Beta":         f(fund.beta),
                })
            if tech:
                row.update({
                    "RSI":          round(tech.rsi_14, 1) if tech.rsi_14 else None,
                    "Golden Cross": "✅" if (tech.ma_50 and tech.ma_200 and tech.ma_50 > tech.ma_200) else "❌",
                })
            if score:
                sig, _ = score_to_signal(score.composite_score or 0)
                row.update({
                    "F. Score":     score.fundamental_score,
                    "T. Score":     score.technical_score,
                    "⭐ Score":     score.composite_score,
                    "Jelzés":       sig,
                })
            rows.append(row)
        df = pd.DataFrame(rows)
        if "⭐ Score" in df.columns:
            df = df.sort_values("⭐ Score", ascending=False)
        return df
    finally:
        session.close()


# ── Tabs ─────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔍 Screener", "➕ Ticker kezelés"])

# ─────────────────── TAB 1: SCREENER ────────────────────────
with tab1:
    col_f, col_main = st.columns([1, 3])

    with col_f:
        st.markdown("#### Szűrők")

        # Profil
        pl = list(PROFILE_LABELS.values())
        pk = list(PROFILE_LABELS.keys())
        idx = pk.index(profile) if profile in pk else 1
        chosen = st.selectbox("Profil", pl, index=idx)
        profile = pk[pl.index(chosen)]
        st.session_state["profile"] = profile

        st.markdown("---")
        st.markdown("**Score szűrők**")
        min_score = st.slider("Min. össz. score", 0, 90, 0)
        min_fscore = st.slider("Min. fundament. score", 0, 90, 0)

        st.markdown("**Értékelési mutatók**")
        pe_max    = st.number_input("Max P/E", value=100.0, step=5.0)
        peg_max   = st.number_input("Max PEG", value=5.0, step=0.5)
        div_min   = st.number_input("Min Div. Yield %", value=0.0, step=0.5)

        st.markdown("**Technikai**")
        rsi_min = st.slider("RSI min", 0, 100, 0)
        rsi_max = st.slider("RSI max", 0, 100, 100)
        gc_only = st.checkbox("Csak Golden Cross", value=False)

        st.markdown("**Szektor**")
        sectors_all = ["Minden"]
        df_full = load_all_tickers_with_scores(profile)
        if "Szektor" in df_full.columns:
            sectors_all += sorted(df_full["Szektor"].dropna().unique().tolist())
        sector_filter = st.selectbox("Szektor", sectors_all)

    with col_main:
        df = load_all_tickers_with_scores(profile)

        if df.empty:
            st.warning("⚠️ Nincsenek adatok. Menj az **Adatkezelés** oldalra és gyűjts adatot!")
        else:
            # Szűrések
            if "⭐ Score" in df.columns:
                df = df[df["⭐ Score"].fillna(0) >= min_score]
            if "F. Score" in df.columns:
                df = df[df["F. Score"].fillna(0) >= min_fscore]
            if "P/E" in df.columns:
                df = df[df["P/E"].fillna(999) <= pe_max]
            if "PEG" in df.columns:
                df = df[df["PEG"].fillna(999) <= peg_max]
            if "Div. Yield %" in df.columns:
                df = df[df["Div. Yield %"].fillna(0) >= div_min]
            if "RSI" in df.columns:
                df = df[(df["RSI"].fillna(50) >= rsi_min) & (df["RSI"].fillna(50) <= rsi_max)]
            if gc_only and "Golden Cross" in df.columns:
                df = df[df["Golden Cross"] == "✅"]
            if sector_filter != "Minden" and "Szektor" in df.columns:
                df = df[df["Szektor"] == sector_filter]

            st.markdown(f"**{len(df)} részvény** felel meg a szűrőknek")

            # Táblázat
            display_cols = [c for c in ["Szimbólum","Név","Szektor","P/E","PEG","ROE %",
                                         "RSI","Golden Cross","F. Score","T. Score","⭐ Score","Jelzés"]
                            if c in df.columns]
            st.dataframe(
                df[display_cols].reset_index(drop=True),
                use_container_width=True,
                height=480,
                column_config={
                    "⭐ Score": st.column_config.ProgressColumn("⭐ Score", min_value=0, max_value=100),
                    "F. Score": st.column_config.ProgressColumn("F. Score", min_value=0, max_value=100),
                    "T. Score": st.column_config.ProgressColumn("T. Score", min_value=0, max_value=100),
                }
            )

            # Export
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ CSV letöltés", csv, "investscan_screener.csv", "text/csv")


# ─────────────────── TAB 2: TICKER KEZELÉS ──────────────────
with tab2:
    st.markdown("#### ➕ Tickerek hozzáadása az adatbázishoz")
    st.info("Add meg a figyelni kívánt ticker szimbólumokat. Az **Adatkezelés** oldalon indíthatod el az adatgyűjtést.")

    col_add, col_list = st.columns([1, 1])

    with col_add:
        st.markdown("**Egyenként**")
        new_ticker = st.text_input("Ticker (pl. AAPL, ASML.AS, SAP.DE)").upper().strip()
        asset_type = st.selectbox("Típus", ["stock", "etf", "commodity"])
        market     = st.selectbox("Piac", ["US", "EU", "Globális"])

        if st.button("➕ Hozzáadás", type="primary"):
            if new_ticker:
                session = get_session()
                existing = session.query(Ticker).filter_by(symbol=new_ticker).first()
                if existing:
                    st.warning(f"⚠️ {new_ticker} már szerepel!")
                else:
                    # Gyors meta info
                    try:
                        info_d = yf.Ticker(new_ticker).info or {}
                        name_v = info_d.get("longName") or info_d.get("shortName") or new_ticker
                    except:
                        name_v = new_ticker
                    t = Ticker(symbol=new_ticker, name=name_v,
                               asset_type=asset_type, market=market)
                    session.add(t)
                    session.commit()
                    st.success(f"✅ {new_ticker} ({name_v}) hozzáadva!")
                session.close()

        st.markdown("---")
        st.markdown("**CSV import (soronként ticker)**")
        csv_file = st.file_uploader("CSV / TXT fájl", type=["csv","txt"])
        if csv_file and st.button("📥 Importálás"):
            content = csv_file.read().decode()
            symbols = [s.strip().upper() for s in content.replace(",","\n").splitlines() if s.strip()]
            session = get_session()
            added = 0
            for sym in symbols:
                if not session.query(Ticker).filter_by(symbol=sym).first():
                    session.add(Ticker(symbol=sym, name=sym))
                    added += 1
            session.commit()
            session.close()
            st.success(f"✅ {added} ticker hozzáadva!")

    with col_list:
        st.markdown("**Jelenlegi tickerek**")
        session = get_session()
        all_t = session.query(Ticker).filter_by(active=True).order_by(Ticker.symbol).all()
        session.close()

        if all_t:
            ticker_data = [{"Szimbólum": t.symbol, "Név": (t.name or "")[:30],
                            "Típus": t.asset_type, "Piac": t.market} for t in all_t]
            st.dataframe(pd.DataFrame(ticker_data), use_container_width=True, height=400)

            # Törlés
            to_del = st.selectbox("Törlendő ticker", [t.symbol for t in all_t])
            if st.button("🗑️ Kikapcsolás", help="Deaktiválja a tickert (adatok megmaradnak)"):
                session = get_session()
                t_obj = session.query(Ticker).filter_by(symbol=to_del).first()
                if t_obj:
                    t_obj.active = False
                    session.commit()
                    st.success(f"{to_del} kikapcsolva")
                session.close()
                st.rerun()
        else:
            st.info("Még nincsenek tickerek. Adj hozzá egyet balra!")
