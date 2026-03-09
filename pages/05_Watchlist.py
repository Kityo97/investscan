"""
Watchlist – Saját részvénylista követés és alert szabályok
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf
from data.db import get_session, Watchlist
from engine.scoring import score_to_signal
from datetime import datetime

st.set_page_config(page_title="Watchlist – InvestScan", page_icon="⭐", layout="wide")

st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#F0F4F8;}
[data-testid="stSidebar"]{background:#1E3A5F;}
[data-testid="stSidebar"] *{color:#ECF0F1!important;}
.page-header{background:linear-gradient(135deg,#1E3A5F 0%,#2E6DA4 100%);
  color:white;padding:20px 24px;border-radius:12px;margin-bottom:20px;}
.page-header h1{color:white!important;margin:0;}
.page-header p{color:#BDC3C7;margin:4px 0 0 0;}
.wl-card{background:white;border-radius:12px;padding:16px;
  box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:8px;}
</style>""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h1>⭐ Watchlist</h1>
  <p>Saját részvénylista – követés, vásárlási ár rögzítése, alert szabályok</p>
</div>
""", unsafe_allow_html=True)


def load_watchlist():
    session = get_session()
    items = session.query(Watchlist).order_by(Watchlist.added_at.desc()).all()
    session.close()
    return items


def get_current_price(symbol):
    try:
        t = yf.Ticker(symbol)
        h = t.history(period="5d")
        if not h.empty:
            curr = h["Close"].iloc[-1]
            prev = h["Close"].iloc[-2] if len(h) >= 2 else curr
            return curr, (curr - prev) / prev * 100
    except:
        pass
    return None, None


# ── Hozzáadás form ────────────────────────────────────────────
with st.expander("➕ Új részvény hozzáadása", expanded=False):
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        wl_sym = st.text_input("Szimbólum", placeholder="AAPL").upper().strip()
    with col_b:
        wl_buy = st.number_input("Vásárlási ár ($)", min_value=0.0, value=0.0, step=0.01)
    with col_c:
        wl_target = st.number_input("Célár ($)", min_value=0.0, value=0.0, step=0.01)
    with col_d:
        wl_stop = st.number_input("Stop Loss ($)", min_value=0.0, value=0.0, step=0.01)
    wl_notes = st.text_area("Megjegyzés", placeholder="Miért veszed fel? Stratégia?", height=70)
    wl_alert_score = st.slider("Alert ha Score eléri:", 0, 100, 70)

    if st.button("⭐ Hozzáadás", type="primary"):
        if wl_sym:
            session = get_session()
            existing = session.query(Watchlist).filter_by(symbol=wl_sym).first()
            if existing:
                st.warning(f"⚠️ {wl_sym} már szerepel a watchlisten!")
            else:
                try:
                    info = yf.Ticker(wl_sym).info or {}
                    name = info.get("longName") or info.get("shortName") or wl_sym
                except:
                    name = wl_sym
                w = Watchlist(
                    symbol=wl_sym, name=name,
                    buy_price=wl_buy if wl_buy > 0 else None,
                    target=wl_target if wl_target > 0 else None,
                    stop_loss=wl_stop if wl_stop > 0 else None,
                    notes=wl_notes,
                    alert_score=wl_alert_score,
                )
                session.add(w)
                session.commit()
                # session state sync
                wl_ss = st.session_state.get("watchlist", [])
                if wl_sym not in wl_ss:
                    st.session_state["watchlist"] = wl_ss + [wl_sym]
                st.success(f"✅ {wl_sym} hozzáadva!")
                st.rerun()
            session.close()

# ── Watchlist táblázat ────────────────────────────────────────
items = load_watchlist()

# Session state szinkron
session_wl = [w.symbol for w in items]
st.session_state["watchlist"] = session_wl

if not items:
    st.info("📋 A watchlisted üres. Adj hozzá részvényeket fent, vagy a 📈 Részvény oldalon!")
    st.stop()

st.markdown(f"### 📋 {len(items)} részvény a listán")

# Adatok betöltése
rows = []
for item in items:
    price, chg = get_current_price(item.symbol)
    row = {
        "symbol":    item.symbol,
        "name":      (item.name or item.symbol)[:30],
        "price":     price,
        "chg":       chg,
        "buy_price": item.buy_price,
        "target":    item.target,
        "stop_loss": item.stop_loss,
        "notes":     item.notes,
        "alert_score": item.alert_score,
        "added_at":  item.added_at,
        "id":        item.id,
    }
    # P&L számítás
    if price and item.buy_price and item.buy_price > 0:
        row["pnl_pct"] = (price - item.buy_price) / item.buy_price * 100
    else:
        row["pnl_pct"] = None
    rows.append(row)

# ── Kártyák ──────────────────────────────────────────────────
for row in rows:
    with st.container():
        c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 1.5, 1.5, 1.5, 1])

        with c1:
            st.markdown(f"**{row['symbol']}**")
            st.caption(row["name"])

        with c2:
            price_str = f"${row['price']:.2f}" if row['price'] else "—"
            chg_val = row['chg'] or 0
            chg_color = "#27AE60" if chg_val >= 0 else "#E74C3C"
            st.markdown(f"**{price_str}**")
            st.markdown(f"<span style='color:{chg_color};font-size:.9em'>{chg_val:+.2f}%</span>",
                        unsafe_allow_html=True)

        with c3:
            if row['buy_price']:
                st.markdown(f"Vétel: **${row['buy_price']:.2f}**")
            if row['pnl_pct'] is not None:
                pnl_c = "#27AE60" if row['pnl_pct'] >= 0 else "#E74C3C"
                st.markdown(f"<span style='color:{pnl_c};font-weight:bold'>P&L: {row['pnl_pct']:+.1f}%</span>",
                            unsafe_allow_html=True)

        with c4:
            if row['target']:
                upside = (row['target'] / row['price'] - 1) * 100 if row['price'] else None
                st.markdown(f"🎯 Cél: ${row['target']:.2f}")
                if upside:
                    st.caption(f"Potenciál: {upside:+.1f}%")
            if row['stop_loss']:
                st.markdown(f"🛑 Stop: ${row['stop_loss']:.2f}")

        with c5:
            if row['notes']:
                st.caption(row['notes'][:60])
            st.caption(f"Alert ≥ {row['alert_score']}")

        with c6:
            if st.button("🗑️", key=f"del_{row['id']}", help="Törlés"):
                session = get_session()
                w = session.query(Watchlist).filter_by(id=row['id']).first()
                if w:
                    session.delete(w)
                    session.commit()
                session.close()
                st.rerun()

    st.markdown("<hr style='margin:4px 0;border:none;border-top:1px solid #eee'>",
                unsafe_allow_html=True)

# ── Összesített P&L ───────────────────────────────────────────
st.markdown("---")
pnl_rows = [r for r in rows if r['pnl_pct'] is not None]
if pnl_rows:
    st.markdown("### 📊 P&L összesítő")
    pnl_df = pd.DataFrame(pnl_rows)[["symbol","price","buy_price","pnl_pct"]]
    pnl_df.columns = ["Szimbólum","Jelenlegi ár","Vételi ár","P&L %"]

    fig = go.Figure(go.Bar(
        x=pnl_df["Szimbólum"], y=pnl_df["P&L %"],
        marker_color=["#27AE60" if v >= 0 else "#E74C3C" for v in pnl_df["P&L %"]],
        text=[f"{v:+.1f}%" for v in pnl_df["P&L %"]],
        textposition="outside",
    ))
    fig.update_layout(
        height=320, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=20, b=20),
        yaxis_title="P&L %",
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Export ────────────────────────────────────────────────────
export_df = pd.DataFrame(rows)[["symbol","name","price","chg","buy_price","target","stop_loss","pnl_pct","notes"]]
export_df.columns = ["Szimbólum","Név","Ár","Napi %","Vételi ár","Célár","Stop Loss","P&L %","Megjegyzés"]
csv = export_df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Watchlist CSV export", csv, "investscan_watchlist.csv", "text/csv")
