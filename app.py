"""
InvestScan - Befektetesi Figyelő Dashboard
Foprograrm - futtatas: streamlit run app.py
"""
import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from data.db import init_db
from config import PROFILE_LABELS

st.set_page_config(
    page_title="InvestScan",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #F0F4F8; }
  [data-testid="stSidebar"] { background: #1E3A5F; }
  [data-testid="stSidebar"] * { color: #ECF0F1 !important; }
  .score-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 0.85em; margin: 2px; }
  .score-buy    { background:#D5F5E3; color:#1E8449; }
  .score-watch  { background:#FDEBD0; color:#D35400; }
  .score-hold   { background:#EAECEE; color:#5D6D7E; }
  .score-avoid  { background:#FADBD8; color:#C0392B; }
  .metric-card { background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #2E6DA4; margin-bottom: 8px; }
  .card-title { font-size: 0.78em; color: #7F8C8D; text-transform: uppercase; }
  .card-value { font-size: 1.6em; font-weight: bold; color: #1E3A5F; }
  .page-header { background: linear-gradient(135deg, #1E3A5F 0%, #2E6DA4 100%); color: white; padding: 20px 24px; border-radius: 12px; margin-bottom: 20px; }
  .page-header h1 { color: white !important; margin: 0; font-size: 1.6em; }
  .page-header p  { color: #BDC3C7; margin: 4px 0 0 0; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

init_db()

if "profile" not in st.session_state:
    st.session_state["profile"] = None
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []
if "user_tickers" not in st.session_state:
    st.session_state["user_tickers"] = []


# --- Functions defined BEFORE use ---

def _calculate_profile(q1, q2, q3, q4, q5, q6):
    score = 0
    horizon_map = {"< 1 ev": 0, "1-3 ev": 1, "3-7 ev": 2, "7+ ev": 3}
    score += horizon_map.get(q1, 1)
    risk_map = {"Azonnal eladom": 0, "Varok es figyelek": 1, "Tartom": 2, "Tobbet veszek": 3}
    score += risk_map.get(q2, 1)
    style_map = {"Stabil osztalek": 0, "Kiegyensulyozott": 1, "Gyors novekedés": 2, "Rovid tavu trading": 3}
    score += style_map.get(q3, 1)
    return_map = {"5-8%": 0, "8-15%": 1, "15-25%": 2, "25%+": 3}
    score += return_map.get(q4, 1)
    time_map = {"Szinte semmit": 0, "1-2 ora": 1, "3-5 ora": 2, "5+ ora": 3}
    score += time_map.get(q6, 1)
    if score <= 4:    return "conservative"
    elif score <= 8:  return "balanced"
    elif score <= 11: return "growth"
    else:             return "active"


def _show_quiz():
    st.markdown("""
    <div class="page-header">
      <h1>👋 Üdvözöl az InvestScan!</h1>
      <p>Töltsd ki a rövid tesztet, hogy személyre szabott elemzést kapj.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🎯 Befektetői Személyiségtest")
    st.markdown("*8 kérdés – kb. 2 perc*")

    with st.form("quiz_form"):
        q1 = st.radio("1. Mikor szeretnéd realizálni a hozamot?",
            ["< 1 ev", "1-3 ev", "3-7 ev", "7+ ev"], horizontal=True)
        q2 = st.radio("2. Ha a portfoliod 25%-ot esik, mit teszel?",
            ["Azonnal eladom", "Varok es figyelek", "Tartom", "Tobbet veszek"], horizontal=True)
        q3 = st.radio("3. Mi a fontosabb?",
            ["Stabil osztalek", "Kiegyensulyozott", "Gyors novekedés", "Rovid tavu trading"], horizontal=True)
        q4 = st.radio("4. Elvart evi hozam?",
            ["5-8%", "8-15%", "15-25%", "25%+"], horizontal=True)
        q5 = st.radio("5. Tőzsdei tapasztalat?",
            ["Kezdő < 1 ev", "Kozepes 1-3 ev", "Halado 3-7 ev", "Profi 7+ ev"], horizontal=True)
        q6 = st.radio("6. Heti elemzési idő?",
            ["Szinte semmit", "1-2 ora", "3-5 ora", "5+ ora"], horizontal=True)
        q7 = st.radio("7. Melyik piac?",
            ["US (NYSE/NASDAQ)", "EU", "Mindketto", "ETF-ek"], horizontal=True)
        q8 = st.radio("8. ESG szempontok?",
            ["Igen, szurok ra", "Kicsit erdekel", "Nem kulonosen"], horizontal=True)
        submitted = st.form_submit_button("📊 Profil meghatározása", use_container_width=True, type="primary")

    if submitted:
        p = _calculate_profile(q1, q2, q3, q4, q5, q6)
        st.session_state["profile"] = p
        st.session_state["preferred_market"] = q7
        st.session_state["esg_filter"] = q8
        label = PROFILE_LABELS.get(p, p)
        st.success(f"✅ Profilod: **{label}**")
        st.balloons()
        import time; time.sleep(1)
        st.rerun()


def _show_home(profile):
    label = PROFILE_LABELS.get(profile, profile)
    st.markdown(f"""
    <div class="page-header">
      <h1>📊 InvestScan Dashboard</h1>
      <p>Profilod: {label} | Személyre szabott befektetési figyelő</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 👇 Navigálj az oldalak között a bal oldali menüvel!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-card"><div class="card-title">📊 Dashboard</div><p>Napi top pick-ek score-alapu rangsor szerint.</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><div class="card-title">🔍 Screener</div><p>Adj hozzá tickereket es szurj mutatók alapján.</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><div class="card-title">🌍 Makro</div><p>Fed kamatpálya, infláció, yield curve, VIX.</p></div>', unsafe_allow_html=True)

    st.info("💡 **Első lépés:** Menj az **⚙️ Adatkezelés** oldalra és indítsd el az adatgyűjtést!")


# --- Sidebar (after function definitions) ---

with st.sidebar:
    st.markdown("## 📈 InvestScan")
    st.markdown("---")
    profile = st.session_state.get("profile")
    if profile:
        st.markdown(f"**Profilod:** {PROFILE_LABELS.get(profile, profile)}")
        if st.button("🔄 Profil módosítása", use_container_width=True):
            st.session_state["profile"] = None
            st.rerun()
    else:
        st.info("👆 Töltsd ki a tesztet!")
    st.markdown("---")
    st.page_link("app.py",                        label="🏠 Főoldal / Quiz")
    st.page_link("pages/01_Dashboard.py",         label="📊 Dashboard")
    st.page_link("pages/02_Reszvenyek.py",        label="📈 Résvény részletek")
    st.page_link("pages/03_Screener.py",          label="🔍 Screener")
    st.page_link("pages/04_Makro.py",             label="🌍 Makro")
    st.page_link("pages/05_Watchlist.py",         label="⭐ Watchlist")
    st.page_link("pages/06_Adatok.py",             label="⚙️ Adatkezelés")
    st.markdown("---")
    st.caption(⚠️ Tájékoztatási célú. Nem befektetési tanács.")


# --- Main ---

profile = st.session_state.get("profile")
if not profile:
    _show_quiz()
else:
    _show_home(profile)
