"""
Részvény Részletlap – chart, mutatók, scoring breakdown
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf
from datetime import date, timedelta
from data.db import get_session, Ticker, Price, Fundamental, Technical, Score
from engine.indicators import compute_technicals, get_signals
from engine.scoring import fundamental_score, technical_score, score_to_signal
from config import PROFILE_LABELS, PROFILE_WEIGHTS
import math

st.set_page_config(page_title="Részvény – InvestScan", page_icon="📈", layout="wide")

st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#F0F4F8;}
[data-testid="stSidebar"]{background:#1E3A5F;}
[data-testid="stSidebar"] *{color:#ECF0F1!important;}
.metric-card{background:white;border-radius:12px;padding:16px;
  box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:4px solid #2E6DA4;margin-bottom:8px;}
.card-title{font-size:.78em;color:#7F8C8D;text-transform:uppercase;}
.card-value{font-size:1.4em;font-weight:bold;color:#1E3A5F;}
.page-header{background:linear-gradient(135deg,#1E3A5F 0%,#2E6DA4 100%);
  color:white;padding:20px 24px;border-radius:12px;margin-bottom:20px;}
.page-header h1{color:white!important;margin:0;}
.page-header p{color:#BDC3C7;margin:4px 0 0 0;font-size:.9em;}
.signal-badge{display:inline-block;padding:6px 16px;border-radius:20px;
  font-weight:bold;font-size:1.1em;}
</style>""", unsafe_allow_html=True)


def safe_val(v, fmt="{:.2f}", default="—"):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    try:
        return fmt.format(v)
    except:
        return str(v)


def pct(v, default="—"):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return default
    val = v * 100 if abs(v) < 2 else v
    color = "#27AE60" if val >= 0 else "#E74C3C"
    return f"<span style='color:{color}'>{val:+.1f}%</span>"


# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Részvény keresés")
    st.markdown("---")
    symbol_input = st.text_input("Ticker szimbólum (pl. AAPL, MSFT, ASML)", "AAPL").upper().strip()
    period = st.selectbox("Chart időszak", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
                          index=3)
    show_ma    = st.checkbox("MA 50/200", value=True)
    show_bb    = st.checkbox("Bollinger Bands", value=False)
    show_vol   = st.checkbox("Volume", value=True)
    show_macd  = st.checkbox("MACD panel", value=True)
    show_rsi   = st.checkbox("RSI panel", value=True)
    profile    = st.session_state.get("profile", "balanced")

# ── Adatok ───────────────────────────────────────────────────
symbol = symbol_input

@st.cache_data(ttl=900, show_spinner=False)
def load_yf_data(sym, per):
    try:
        t = yf.Ticker(sym)
        hist = t.history(period=per, auto_adjust=True)
        info = t.info or {}
        return hist, info
    except:
        return pd.DataFrame(), {}

with st.spinner(f"Betöltés: {symbol}..."):
    hist, info = load_yf_data(symbol, period)

if hist.empty:
    st.error(f"❌ Nem találtam adatot: **{symbol}**. Ellenőrizd a szimbólumot!")
    st.stop()

# Technikai indikátorok
hist.index = hist.index.date
hist_df = hist[["Open","High","Low","Close","Volume"]].copy()
hist_df.columns = ["open","high","low","close","volume"]
hist_df["adj_close"] = hist_df["close"]
tech_df = compute_technicals(hist_df)

# ── Fejléc ────────────────────────────────────────────────────
name       = info.get("longName") or info.get("shortName") or symbol
sector     = info.get("sector", "")
industry   = info.get("industry", "")
exchange   = info.get("exchange", "")
curr_price = hist["Close"].iloc[-1]
prev_price = hist["Close"].iloc[-2] if len(hist) >= 2 else curr_price
day_chg    = (curr_price - prev_price) / prev_price * 100

chg_color = "#27AE60" if day_chg >= 0 else "#E74C3C"
chg_arrow = "▲" if day_chg >= 0 else "▼"

st.markdown(f"""
<div class="page-header">
  <h1>{symbol} &nbsp; <span style="font-size:.7em;font-weight:400">{name}</span></h1>
  <p>{sector} &nbsp;|&nbsp; {industry} &nbsp;|&nbsp; {exchange}</p>
</div>
""", unsafe_allow_html=True)

# Ár + jelzés
cA, cB, cC = st.columns([2, 2, 4])
with cA:
    st.markdown(f"""<div class="metric-card">
      <div class="card-title">Aktuális ár</div>
      <div class="card-value">${curr_price:.2f}</div>
      <div style="color:{chg_color};font-weight:bold">{chg_arrow} {abs(day_chg):.2f}% ma</div>
    </div>""", unsafe_allow_html=True)

with cB:
    # Score számítás
    class MockFund:
        def __init__(self, d):
            for k, v in d.items():
                setattr(self, k, v)
    fund_mock = MockFund({
        "pe_ratio":       info.get("trailingPE"),
        "peg_ratio":      info.get("pegRatio"),
        "roe":            info.get("returnOnEquity"),
        "eps_growth_yoy": None,
        "debt_equity":    info.get("debtToEquity"),
        "fcf_yield":      None,
        "div_yield":      info.get("dividendYield"),
        "revenue_growth": info.get("revenueGrowth"),
    })

    class MockTech:
        def __init__(self, row):
            for k in ["rsi_14","macd","macd_signal","macd_hist","ma_50","ma_200",
                      "bb_upper","bb_middle","bb_lower","volume","volume_avg20"]:
                setattr(self, k, row.get(k) if not tech_df.empty else None)

    tech_mock = MockTech(tech_df.iloc[-1] if not tech_df.empty else {})
    weights   = PROFILE_WEIGHTS.get(profile, PROFILE_WEIGHTS["balanced"])
    fs = fundamental_score(fund_mock)
    ts = technical_score(tech_mock)
    ms = 50.0
    comp = fs * weights["fundamental"] + ts * weights["technical"] + ms * weights["macro"]
    signal_text, sig_color = score_to_signal(comp)

    st.markdown(f"""<div class="metric-card">
      <div class="card-title">Composite Score ({PROFILE_LABELS.get(profile,'')})</div>
      <div class="card-value" style="color:{sig_color}">{comp:.1f}/100</div>
      <div style="font-weight:bold">{signal_text}</div>
    </div>""", unsafe_allow_html=True)

with cC:
    # Mini score breakdown
    st.markdown(f"""<div class="metric-card">
      <div class="card-title">Score pillér bontás</div>
      <div style="display:flex;gap:16px;margin-top:8px">
        <div>
          <div style="font-size:.75em;color:#7F8C8D">FUNDAMENTÁLIS</div>
          <div style="font-weight:bold;color:#2E6DA4;font-size:1.3em">{fs:.0f}</div>
          <div style="background:#eee;width:80px;height:6px;border-radius:3px">
            <div style="background:#2E6DA4;width:{fs}%;height:6px;border-radius:3px"></div></div>
        </div>
        <div>
          <div style="font-size:.75em;color:#7F8C8D">TECHNIKAI</div>
          <div style="font-weight:bold;color:#27AE60;font-size:1.3em">{ts:.0f}</div>
          <div style="background:#eee;width:80px;height:6px;border-radius:3px">
            <div style="background:#27AE60;width:{ts}%;height:6px;border-radius:3px"></div></div>
        </div>
        <div>
          <div style="font-size:.75em;color:#7F8C8D">MAKRO</div>
          <div style="font-weight:bold;color:#F39C12;font-size:1.3em">{ms:.0f}</div>
          <div style="background:#eee;width:80px;height:6px;border-radius:3px">
            <div style="background:#F39C12;width:{ms}%;height:6px;border-radius:3px"></div></div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── CHART ────────────────────────────────────────────────────
rows_count = 1 + (1 if show_vol else 0) + (1 if show_macd else 0) + (1 if show_rsi else 0)
row_heights = [0.55]
specs = [[{"secondary_y": False}]]
if show_vol:
    row_heights.append(0.12)
    specs.append([{"secondary_y": False}])
if show_macd:
    row_heights.append(0.165)
    specs.append([{"secondary_y": False}])
if show_rsi:
    row_heights.append(0.165)
    specs.append([{"secondary_y": False}])

# normalize
total = sum(row_heights)
row_heights = [r / total for r in row_heights]

subplot_titles = ["Ár chart"]
if show_vol:  subplot_titles.append("Volume")
if show_macd: subplot_titles.append("MACD")
if show_rsi:  subplot_titles.append("RSI")

fig = make_subplots(
    rows=rows_count, cols=1,
    shared_xaxes=True,
    row_heights=row_heights,
    vertical_spacing=0.03,
    subplot_titles=subplot_titles,
    specs=specs,
)

dates = list(hist.index)
o = hist["Open"].values
h_v = hist["High"].values
l_v = hist["Low"].values
c_v = hist["Close"].values
vol = hist["Volume"].values

# Candlestick
fig.add_trace(go.Candlestick(
    x=dates, open=o, high=h_v, low=l_v, close=c_v,
    name="Ár",
    increasing_fillcolor="#27AE60", increasing_line_color="#27AE60",
    decreasing_fillcolor="#E74C3C", decreasing_line_color="#E74C3C",
), row=1, col=1)

# MA-k
if show_ma and not tech_df.empty:
    if "ma_50" in tech_df.columns:
        fig.add_trace(go.Scatter(x=tech_df.index, y=tech_df["ma_50"],
                                 name="MA 50", line=dict(color="#F39C12", width=1.5)), row=1, col=1)
    if "ma_200" in tech_df.columns:
        fig.add_trace(go.Scatter(x=tech_df.index, y=tech_df["ma_200"],
                                 name="MA 200", line=dict(color="#9B59B6", width=1.5)), row=1, col=1)

# Bollinger
if show_bb and not tech_df.empty:
    if "bb_upper" in tech_df.columns:
        fig.add_trace(go.Scatter(x=tech_df.index, y=tech_df["bb_upper"],
                                 name="BB Felső", line=dict(color="#BDC3C7", width=1, dash="dash")), row=1, col=1)
        fig.add_trace(go.Scatter(x=tech_df.index, y=tech_df["bb_lower"],
                                 name="BB Alsó", line=dict(color="#BDC3C7", width=1, dash="dash"),
                                 fill="tonexty", fillcolor="rgba(189,195,199,0.08)"), row=1, col=1)

# Volume
cur_row = 2
if show_vol:
    colors = ["#27AE60" if c >= p else "#E74C3C" for c, p in zip(c_v[1:], c_v[:-1])]
    colors.insert(0, "#27AE60")
    fig.add_trace(go.Bar(x=dates, y=vol, name="Volume", marker_color=colors,
                         marker_line_width=0), row=cur_row, col=1)
    cur_row += 1

# MACD
if show_macd and not tech_df.empty and "macd" in tech_df.columns:
    colors_hist = ["#27AE60" if v >= 0 else "#E74C3C" for v in tech_df["macd_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=tech_df.index, y=tech_df["macd_hist"],
                         name="MACD Hist", marker_color=colors_hist, marker_line_width=0),
                  row=cur_row, col=1)
    fig.add_trace(go.Scatter(x=tech_df.index, y=tech_df["macd"],
                             name="MACD", line=dict(color="#2E6DA4", width=1.5)), row=cur_row, col=1)
    fig.add_trace(go.Scatter(x=tech_df.index, y=tech_df["macd_signal"],
                             name="Signal", line=dict(color="#E74C3C", width=1.5, dash="dot")),
                  row=cur_row, col=1)
    cur_row += 1

# RSI
if show_rsi and not tech_df.empty and "rsi_14" in tech_df.columns:
    fig.add_trace(go.Scatter(x=tech_df.index, y=tech_df["rsi_14"],
                             name="RSI 14", line=dict(color="#9B59B6", width=1.8)), row=cur_row, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#E74C3C", line_width=1, row=cur_row, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#27AE60", line_width=1, row=cur_row, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(150,150,150,0.05)", row=cur_row, col=1)

fig.update_layout(
    height=600, plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", y=1.02, x=0),
    hovermode="x unified",
)
fig.update_xaxes(showgrid=True, gridcolor="#F0F4F8")
fig.update_yaxes(showgrid=True, gridcolor="#F0F4F8")

st.plotly_chart(fig, use_container_width=True)

# ── Fundamentális mutatók ─────────────────────────────────────
st.markdown("### 📊 Fundamentális mutatók")

f1, f2, f3, f4 = st.columns(4)
metrics = [
    ("P/E (Trailing)",   safe_val(info.get("trailingPE"), "{:.1f}"),     f1),
    ("P/E (Forward)",    safe_val(info.get("forwardPE"), "{:.1f}"),      f2),
    ("PEG Ratio",        safe_val(info.get("pegRatio"), "{:.2f}"),        f3),
    ("P/B Ratio",        safe_val(info.get("priceToBook"), "{:.2f}"),     f4),
    ("ROE",              pct(info.get("returnOnEquity")),                 f1),
    ("ROA",              pct(info.get("returnOnAssets")),                 f2),
    ("Revenue Növ.",     pct(info.get("revenueGrowth")),                  f3),
    ("Gross Margin",     pct(info.get("grossMargins")),                   f4),
    ("Debt/Equity",      safe_val(info.get("debtToEquity"), "{:.2f}"),    f1),
    ("Current Ratio",    safe_val(info.get("currentRatio"), "{:.2f}"),    f2),
    ("Dividend Yield",   pct(info.get("dividendYield")),                  f3),
    ("Beta",             safe_val(info.get("beta"), "{:.2f}"),            f4),
]

for label, val, col in metrics:
    with col:
        st.markdown(f"""<div class="metric-card" style="padding:10px 12px">
          <div class="card-title" style="font-size:.72em">{label}</div>
          <div style="font-size:1.1em;font-weight:bold;color:#1E3A5F">{val}</div>
        </div>""", unsafe_allow_html=True)

# ── Technikai jelzések ────────────────────────────────────────
st.markdown("### 📡 Technikai jelzések")
if not tech_df.empty:
    last = tech_df.iloc[-1]

    def indicator_badge(label, value, good_cond, fmt="{:.1f}"):
        val_str = fmt.format(value) if value is not None else "—"
        color = "#D5F5E3" if good_cond else "#FADBD8"
        tcolor = "#1E8449" if good_cond else "#C0392B"
        return f"""<div style="background:{color};color:{tcolor};border-radius:8px;
          padding:8px 14px;font-weight:bold;text-align:center;margin:4px">
          <div style="font-size:.72em;opacity:.8">{label}</div>
          <div>{val_str}</div></div>"""

    rsi = last.get("rsi_14")
    macd_val = last.get("macd")
    macd_sig = last.get("macd_signal")
    ma50  = last.get("ma_50")
    ma200 = last.get("ma_200")

    badges_html = ""
    if rsi:
        badges_html += indicator_badge("RSI 14", rsi, 30 <= rsi <= 65)
    if macd_val and macd_sig:
        badges_html += indicator_badge("MACD vs Signal", macd_val - macd_sig,
                                       macd_val > macd_sig, fmt="{:+.3f}")
    if ma50 and ma200:
        badges_html += indicator_badge("MA50 vs MA200", (ma50/ma200-1)*100,
                                       ma50 > ma200, fmt="{:+.1f}%")

    st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:4px'>{badges_html}</div>",
                unsafe_allow_html=True)

# ── Watchlist gomb ─────────────────────────────────────────────
st.markdown("---")
wl = st.session_state.get("watchlist", [])
col_wl1, col_wl2, _ = st.columns([2, 2, 4])
with col_wl1:
    if symbol not in wl:
        if st.button(f"⭐ Watchlistre: {symbol}", type="primary"):
            st.session_state["watchlist"].append(symbol)
            st.success(f"✅ {symbol} hozzáadva!")
    else:
        st.success(f"✅ {symbol} már a Watchlisten!")
