"""
Dashboard – Napi Top Pick-ek
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.db import get_session, Ticker, Score, Price, Fundamental, Technical
from engine.scoring import score_to_signal, composite as calc_composite
from config import PROFILE_LABELS, PROFILE_WEIGHTS, SECTOR_ETFS
import yfinance as yf
from datetime import date, timedelta

st.set_page_config(page_title="Dashboard – InvestScan", page_icon="📊", layout="wide")

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#F0F4F8;}
[data-testid="stSidebar"]{background:#1E3A5F;}
[data-testid="stSidebar"] *{color:#ECF0F1!important;}
.metric-card{background:white;border-radius:12px;padding:16px;
  box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:4px solid #2E6DA4;margin-bottom:8px;}
.card-title{font-size:.78em;color:#7F8C8D;text-transform:uppercase;letter-spacing:.05em;}
.card-value{font-size:1.7em;font-weight:bold;color:#1E3A5F;}
.page-header{background:linear-gradient(135deg,#1E3A5F 0%,#2E6DA4 100%);
  color:white;padding:20px 24px;border-radius:12px;margin-bottom:20px;}
.page-header h1{color:white!important;margin:0;font-size:1.6em;}
.page-header p{color:#BDC3C7;margin:4px 0 0 0;font-size:.9em;}
</style>""", unsafe_allow_html=True)


def get_profile():
    return st.session_state.get("profile", "balanced")


def load_top_picks(profile: str, limit: int = 15) -> pd.DataFrame:
    session = get_session()
    try:
        scores = (session.query(Score, Ticker)
                  .join(Ticker, Score.ticker_id == Ticker.id)
                  .filter(Score.profile == profile)
                  .order_by(Score.date.desc(), Score.composite_score.desc())
                  .limit(limit * 3)
                  .all())

        seen = set()
        rows = []
        for s, t in scores:
            if t.symbol in seen:
                continue
            seen.add(t.symbol)
            rows.append({
                "symbol":    t.symbol,
                "name":      t.name or t.symbol,
                "sector":    t.sector or "—",
                "fund_s":    s.fundamental_score,
                "tech_s":    s.technical_score,
                "macro_s":   s.macro_score,
                "composite": s.composite_score,
                "signal":    s.signal,
                "date":      s.date,
            })
            if len(rows) >= limit:
                break
        return pd.DataFrame(rows)
    finally:
        session.close()


def get_price_change(symbol: str) -> tuple:
    """(mai záró, napi változás %)"""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if len(hist) >= 2:
            prev  = hist["Close"].iloc[-2]
            curr  = hist["Close"].iloc[-1]
            chg   = (curr - prev) / prev * 100
            return round(curr, 2), round(chg, 2)
        elif len(hist) == 1:
            return round(hist["Close"].iloc[-1], 2), 0.0
    except:
        pass
    return None, None


def get_sparkline(symbol: str) -> list:
    try:
        hist = yf.Ticker(symbol).history(period="1mo")
        return list(hist["Close"].round(2))
    except:
        return []


# ── Oldal ────────────────────────────────────────────────────
profile = get_profile()
label   = PROFILE_LABELS.get(profile, profile)

st.markdown(f"""
<div class="page-header">
  <h1>📊 Napi Top Pick-ek</h1>
  <p>Profil: {label} &nbsp;|&nbsp; {date.today().strftime('%Y. %B %d.')}</p>
</div>
""", unsafe_allow_html=True)

# ── Profil választó ha nincs beállítva ───────────────────────
with st.sidebar:
    st.markdown("## 📊 Dashboard")
    st.markdown("---")
    profile_options = list(PROFILE_LABELS.keys())
    profile_labels  = list(PROFILE_LABELS.values())
    idx = profile_options.index(profile) if profile in profile_options else 1
    chosen = st.selectbox("Profil", profile_labels, index=idx)
    profile = profile_options[profile_labels.index(chosen)]
    st.session_state["profile"] = profile

    st.markdown("---")
    n_picks = st.slider("Top N részvény", 5, 20, 10)
    min_score = st.slider("Min. composite score", 0, 80, 40)

# ── Adatok betöltése ─────────────────────────────────────────
df = load_top_picks(profile, limit=50)

if df.empty:
    st.warning("⚠️ Még nincsenek score adatok. Menj az **⚙️ Adatkezelés** oldalra és indítsd el az adatgyűjtést!")
    st.stop()

df = df[df["composite"] >= min_score].head(n_picks)

# ── Összefoglaló metrikák ────────────────────────────────────
buy_cnt   = len(df[df["signal"] == "BUY"])
watch_cnt = len(df[df["signal"] == "WATCH"])
avg_score = df["composite"].mean() if not df.empty else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="metric-card">
      <div class="card-title">🟢 Vételi jelzés</div>
      <div class="card-value">{buy_cnt}</div>
      <div style="color:#7F8C8D;font-size:.85em">részvény</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card">
      <div class="card-title">🟡 Figyeld</div>
      <div class="card-value">{watch_cnt}</div>
      <div style="color:#7F8C8D;font-size:.85em">részvény</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card">
      <div class="card-title">📈 Átlag Score</div>
      <div class="card-value">{avg_score:.1f}</div>
      <div style="color:#7F8C8D;font-size:.85em">/ 100</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card">
      <div class="card-title">📅 Frissítve</div>
      <div class="card-value" style="font-size:1.2em">{df["date"].max() if not df.empty else "—"}</div>
      <div style="color:#7F8C8D;font-size:.85em">legutóbbi adat</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Top Picks tábla ──────────────────────────────────────────
st.markdown("### 🏆 Top Részvények")

for _, row in df.iterrows():
    signal_text, signal_color = score_to_signal(row["composite"])
    price, chg = get_price_change(row["symbol"])
    chg_str = f"{chg:+.2f}%" if chg is not None else ""
    chg_color = "#27AE60" if (chg or 0) >= 0 else "#E74C3C"
    price_str = f"${price}" if price else "—"

    with st.container():
        col_sym, col_name, col_price, col_chg, col_score, col_sig, col_btn = st.columns([1.2, 2.5, 1.2, 1.0, 2.0, 1.5, 1.0])

        with col_sym:
            st.markdown(f"**{row['symbol']}**")
            st.caption(row["sector"][:18] if row["sector"] else "")

        with col_name:
            st.markdown(row["name"][:35] if row["name"] else "")

        with col_price:
            st.markdown(f"**{price_str}**")

        with col_chg:
            st.markdown(f"<span style='color:{chg_color};font-weight:bold'>{chg_str}</span>",
                        unsafe_allow_html=True)

        with col_score:
            # Score breakdown mini-bar
            fs = row.get("fund_s", 0) or 0
            ts = row.get("tech_s", 0) or 0
            ms = row.get("macro_s", 0) or 0
            comp = row["composite"] or 0
            bar_color = "#27AE60" if comp >= 70 else "#F39C12" if comp >= 55 else "#95A5A6"
            st.markdown(f"""
            <div style="font-size:.8em;color:#555">
              F:{fs:.0f} &nbsp; T:{ts:.0f} &nbsp; M:{ms:.0f}
            </div>
            <div style="background:#eee;border-radius:4px;height:8px;margin-top:4px">
              <div style="background:{bar_color};width:{comp}%;height:8px;border-radius:4px"></div>
            </div>
            <div style="font-size:.8em;font-weight:bold;color:{bar_color}">{comp:.0f}/100</div>
            """, unsafe_allow_html=True)

        with col_sig:
            st.markdown(f"<span style='font-weight:bold'>{signal_text}</span>",
                        unsafe_allow_html=True)

        with col_btn:
            wl = st.session_state.get("watchlist", [])
            if row["symbol"] not in wl:
                if st.button("⭐", key=f"wl_{row['symbol']}", help="Watchlistre ad"):
                    st.session_state["watchlist"].append(row["symbol"])
                    st.rerun()
            else:
                st.markdown("✅")

    st.markdown("<hr style='margin:4px 0;border:none;border-top:1px solid #eee'>",
                unsafe_allow_html=True)

# ── Score eloszlás ───────────────────────────────────────────
st.markdown("---")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### 📊 Score eloszlás")
    fig = px.histogram(
        df, x="composite", nbins=10,
        color_discrete_sequence=["#2E6DA4"],
        labels={"composite": "Composite Score", "count": "Darab"},
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="white", paper_bgcolor="white",
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_chart2:
    st.markdown("#### 🏭 Szektorok")
    sector_counts = df["sector"].value_counts().reset_index()
    sector_counts.columns = ["sector", "count"]
    fig2 = px.pie(
        sector_counts, names="sector", values="count",
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.4,
    )
    fig2.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        height=260, showlegend=True,
        legend=dict(font=dict(size=10)),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Scoring pillérek összehasonlítása ────────────────────────
st.markdown("#### 🎯 Scoring pillérek – Top 10")
top10 = df.head(10).copy()
if not top10.empty:
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="Fundamentális", x=top10["symbol"], y=top10["fund_s"],
                          marker_color="#2E6DA4"))
    fig3.add_trace(go.Bar(name="Technikai",     x=top10["symbol"], y=top10["tech_s"],
                          marker_color="#27AE60"))
    fig3.add_trace(go.Bar(name="Makro",         x=top10["symbol"], y=top10["macro_s"],
                          marker_color="#F39C12"))
    fig3.update_layout(
        barmode="group", height=320,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", y=-0.25),
        yaxis=dict(range=[0, 105]),
    )
    st.plotly_chart(fig3, use_container_width=True)
