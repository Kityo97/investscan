"""
Makro Dashboard – Fed, infláció, yield curve, szektor heatmap
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf
from config import MACRO_TICKERS, SECTOR_ETFS, FRED_API_KEY, FRED_SERIES
from data.sources.fred import fetch_yield_curve, fetch_fed_rate, fetch_cpi, fetch_unemployment

st.set_page_config(page_title="Makro – InvestScan", page_icon="🌍", layout="wide")

st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#F0F4F8;}
[data-testid="stSidebar"]{background:#1E3A5F;}
[data-testid="stSidebar"] *{color:#ECF0F1!important;}
.metric-card{background:white;border-radius:12px;padding:16px;
  box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:4px solid #2E6DA4;margin-bottom:8px;}
.card-title{font-size:.78em;color:#7F8C8D;text-transform:uppercase;}
.card-value{font-size:1.5em;font-weight:bold;color:#1E3A5F;}
.page-header{background:linear-gradient(135deg,#1E3A5F 0%,#2E6DA4 100%);
  color:white;padding:20px 24px;border-radius:12px;margin-bottom:20px;}
.page-header h1{color:white!important;margin:0;}
.page-header p{color:#BDC3C7;margin:4px 0 0 0;}
</style>""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h1>🌍 Makro Dashboard</h1>
  <p>Globális gazdasági mutatók – Fed kamatok, infláció, yield curve, szektorok</p>
</div>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_macro_price(symbol, period="1y"):
    try:
        hist = yf.Ticker(symbol).history(period=period)
        return hist["Close"]
    except:
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def load_sector_perf():
    rows = []
    for name, sym in SECTOR_ETFS.items():
        try:
            hist = yf.Ticker(sym).history(period="1y")
            if not hist.empty:
                cl = hist["Close"]
                ret_1m  = (cl.iloc[-1] / cl.iloc[-22] - 1) * 100 if len(cl) > 22 else None
                ret_3m  = (cl.iloc[-1] / cl.iloc[-66] - 1) * 100 if len(cl) > 66 else None
                ret_ytd = (cl.iloc[-1] / cl.iloc[0] - 1) * 100
                rows.append({"Szektor": name, "ETF": sym,
                             "1 hónap %": round(ret_1m, 1) if ret_1m else None,
                             "3 hónap %": round(ret_3m, 1) if ret_3m else None,
                             "YTD %":     round(ret_ytd, 1)})
        except:
            pass
    return pd.DataFrame(rows)


# ── Makro mutatók sorban ──────────────────────────────────────
st.markdown("### 📊 Globális piaci mutatók")

cols = st.columns(len(MACRO_TICKERS))
for i, (label, sym) in enumerate(MACRO_TICKERS.items()):
    series = load_macro_price(sym, "5d")
    if not series.empty:
        curr = series.iloc[-1]
        prev = series.iloc[-2] if len(series) >= 2 else curr
        chg  = (curr - prev) / prev * 100
        chg_color = "#27AE60" if chg >= 0 else "#E74C3C"
        arrow = "▲" if chg >= 0 else "▼"
        with cols[i]:
            st.markdown(f"""<div class="metric-card" style="padding:12px">
              <div class="card-title" style="font-size:.7em">{label}</div>
              <div class="card-value" style="font-size:1.2em">{curr:,.2f}</div>
              <div style="color:{chg_color};font-size:.85em;font-weight:bold">
                {arrow} {abs(chg):.2f}%</div>
            </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Szektor heatmap ───────────────────────────────────────────
st.markdown("### 🏭 Szektor teljesítmény")

with st.spinner("Szektor adatok..."):
    sector_df = load_sector_perf()

if not sector_df.empty:
    col_heat, col_tbl = st.columns([3, 2])
    with col_heat:
        # Heatmap YTD
        fig_heat = go.Figure(go.Bar(
            x=sector_df["YTD %"],
            y=sector_df["Szektor"],
            orientation="h",
            marker_color=["#27AE60" if v >= 0 else "#E74C3C"
                          for v in sector_df["YTD %"]],
            text=[f"{v:+.1f}%" for v in sector_df["YTD %"]],
            textposition="outside",
        ))
        fig_heat.update_layout(
            title="YTD Hozam szektoronként",
            height=380, plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=40, t=40, b=20),
            xaxis=dict(title="Hozam %"),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_tbl:
        st.markdown("**Részletes teljesítmény tábla**")
        st.dataframe(
            sector_df.set_index("Szektor"),
            use_container_width=True, height=380,
            column_config={
                "1 hónap %": st.column_config.NumberColumn(format="%.1f%%"),
                "3 hónap %": st.column_config.NumberColumn(format="%.1f%%"),
                "YTD %":     st.column_config.NumberColumn(format="%.1f%%"),
            }
        )

st.markdown("---")

# ── Yield Curve + Fed + CPI (FRED) ───────────────────────────
st.markdown("### 🏛️ FRED Makrogazdasági adatok")

if not FRED_API_KEY:
    st.warning("""⚠️ **FRED API kulcs nincs beállítva.**
    
Ingyenes regisztráció: [https://fred.stlouisfed.org](https://fred.stlouisfed.org)
Beállítás: `.env` fájlban `FRED_API_KEY=kulcsod` vagy `config.py`-ban.

Az alábbi grafikonok demo adatokkal tölthetők be.""")

    if st.button("🎭 Demo adatok megjelenítése"):
        import numpy as np
        dates_demo = pd.date_range("2020-01-01", periods=50, freq="ME")
        demo_yc  = pd.Series(list(reversed([0.5, 0.4, 0.2, -0.3, -0.8, -0.5, 0.1, 0.3, 0.6, 0.8]*5)), index=dates_demo)
        demo_fed = pd.Series([0.25]*20 + [1, 1.75, 2.5, 3.5, 4.5, 5.25, 5.25, 5.0, 4.75, 4.5]*3, index=dates_demo)
        demo_cpi = pd.Series([257+i*2 for i in range(50)], index=dates_demo)

        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Scatter(x=demo_yc.index, y=demo_yc.values,
                                       fill="tozeroy", line=dict(color="#2E6DA4")))
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            fig.update_layout(title="10Y-2Y Spread (demo)", height=280,
                              plot_bgcolor="white", paper_bgcolor="white",
                              margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig2 = go.Figure(go.Scatter(x=demo_fed.index, y=demo_fed.values,
                                        line=dict(color="#E74C3C", width=2)))
            fig2.update_layout(title="Fed kamatráta (demo)", height=280,
                               plot_bgcolor="white", paper_bgcolor="white",
                               margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig2, use_container_width=True)
else:
    with st.spinner("FRED adatok betöltése..."):
        yc_data  = fetch_yield_curve(FRED_API_KEY)
        fed_data = fetch_fed_rate(FRED_API_KEY)
        cpi_data = fetch_cpi(FRED_API_KEY)
        unemp    = fetch_unemployment(FRED_API_KEY)

    c1, c2 = st.columns(2)

    with c1:
        if not yc_data.empty:
            fig_yc = go.Figure(go.Scatter(
                x=yc_data.index, y=yc_data.values,
                fill="tozeroy",
                line=dict(color="#2E6DA4"),
                name="10Y-2Y spread"
            ))
            fig_yc.add_hline(y=0, line_dash="dash", line_color="#E74C3C",
                             annotation_text="Inverzió határ")
            latest_yc = yc_data.iloc[-1]
            color_yc = "#E74C3C" if latest_yc < 0 else "#27AE60"
            fig_yc.update_layout(
                title=f"Yield Curve Spread (10Y-2Y): <b style='color:{color_yc}'>{latest_yc:.2f}%</b>",
                height=300, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_yc, use_container_width=True)

    with c2:
        if not fed_data.empty:
            fig_fed = go.Figure(go.Scatter(
                x=fed_data.index, y=fed_data.values,
                line=dict(color="#E74C3C", width=2),
                name="Fed ráta"
            ))
            fig_fed.update_layout(
                title=f"Fed Kamatráta: {fed_data.iloc[-1]:.2f}%",
                height=300, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_fed, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        if not cpi_data.empty:
            cpi_yoy = cpi_data.pct_change(12) * 100
            fig_cpi = go.Figure(go.Scatter(
                x=cpi_yoy.dropna().index, y=cpi_yoy.dropna().values,
                fill="tozeroy", line=dict(color="#F39C12", width=2)
            ))
            fig_cpi.add_hline(y=2, line_dash="dash", line_color="#27AE60",
                              annotation_text="Fed cél: 2%")
            fig_cpi.update_layout(
                title=f"CPI Infláció (YoY): {cpi_yoy.iloc[-1]:.1f}%",
                height=280, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_cpi, use_container_width=True)

    with c4:
        if not unemp.empty:
            fig_unemp = go.Figure(go.Scatter(
                x=unemp.index, y=unemp.values,
                line=dict(color="#9B59B6", width=2)
            ))
            fig_unemp.update_layout(
                title=f"Munkanélküliség: {unemp.iloc[-1]:.1f}%",
                height=280, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_unemp, use_container_width=True)

# ── Makro értékelés ───────────────────────────────────────────
st.markdown("---")
st.markdown("### 🧭 Makro értékelés")
vix = load_macro_price("^VIX", "5d")
vix_val = vix.iloc[-1] if not vix.empty else None

if vix_val:
    if vix_val < 15:
        vix_msg, vix_c = "😌 Alacsony félelem – bullish hangulat", "#27AE60"
    elif vix_val < 25:
        vix_msg, vix_c = "😐 Mérsékelt volatilitás – semleges", "#F39C12"
    elif vix_val < 35:
        vix_msg, vix_c = "😟 Emelt volatilitás – óvatosság", "#E67E22"
    else:
        vix_msg, vix_c = "😱 Magas félelem – kockázatkerülés", "#E74C3C"

    st.markdown(f"""
    <div style="background:white;border-radius:12px;padding:20px;
      box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:6px solid {vix_c}">
      <div style="font-size:.8em;color:#7F8C8D;text-transform:uppercase">VIX Félelem index</div>
      <div style="font-size:2em;font-weight:bold;color:{vix_c}">{vix_val:.1f}</div>
      <div style="font-size:1em;color:#333">{vix_msg}</div>
    </div>
    """, unsafe_allow_html=True)
