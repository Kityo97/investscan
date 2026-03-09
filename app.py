"""
InvestScan – Befektetési Figyelő Dashboard
Főprogram – futtatás: streamlit run app.py
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from data.db import init_db
from config import PROFILE_LABELS

# ── Oldal konfiguráció ───────────────────────────────────────
st.set_page_config(
    page_title="InvestScan",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Általános */
  [data-testid="stAppViewContainer"] { background: #F0F4F8; }
  [data-testid="stSidebar"]          { background: #1E3A5F; }
  [data-testid="stSidebar"] * { color: #ECF0F1 !important; }
  [data-testid="stSidebar"] .stSelectbox label { color: #BDC3C7 !important; }

  /* Score badge-ek */
  .score-badge {
    display: inline-block; padding: 4px 12px;
    border-radius: 20px; font-weight: bold;
    font-size: 0.85em; margin: 2px;
  }
  .score-buy    { background:#D5F5E3; color:#1E8449; }
  .score-watch  { background:#FDEBD0; color:#D35400; }
  .score-hold   { background:#EAECEE; color:#5D6D7E; }
  .score-avoid  { background:#FADBD8; color:#C0392B; }

  /* Kártya */
  .metric-card {
    background: white; border-radius: 12px;
    padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid #2E6DA4;
    margin-bottom: 8px;
  }
  .card-title { font-size: 0.78em; color: #7F8C8D; text-transform: uppercase; }
  .card-value { font-size: 1.6em; font-weight: bold; color: #1E3A5F; }
  .card-delta { font-size: 0.85em; }

  /* Ticker tábla */
  .ticker-row {
    background: white; border-radius: 8px;
    padding: 12px 16px; margin: 4px 0;
    display: flex; align-items: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }
  /* Fejléc */
  .page-header {
    background: linear-gradient(135deg, #1E3A5F 0%, #2E6DA4 100%);
    color: white; padding: 20px 24px; border-radius: 12px;
    margin-bottom: 20px;
  }
  .page-header h1 { color: white !important; margin: 0; font-size: 1.6em; }
  .page-header p  { color: #BDC3C7; margin: 4px 0 0 0; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

# ── DB init ──────────────────────────────────────────────────
init_db()

# ── Session state alapértelmezések ──────────────────────────
if "profile" not in st.session_state:
    st.session_state["profile"] = None
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []
if "user_tickers" not in st.session_state:
    st.session_state["user_tickers"] = []

# ── Sidebar ──────────────────────────────────────────────────
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
        st.info("👆 Először töltsd ki a személyiségtesztet!")

    st.markdown("---")
    st.markdown("**📌 Gyors navigáció**")
    st.page_link("app.py",                        label="🏠 Főoldal / Quiz")
    st.page_link("pages/01_Dashboard.py",         label="📊 Dashboard")
    st.page_link("pages/02_Reszvenyek.py",        label="📈 Részvény részletek")
    st.page_link("pages/03_Screener.py",          label="🔍 Screener")
    st.page_link("pages/04_Makro.py",             label="🌍 Makro")
    st.page_link("pages/05_Watchlist.py",         label="⭐ Watchlist")
    st.page_link("pages/06_Adatok.py",            label="⚙️ Adatkezelés")

    st.markdown("---")
    st.markdown("<small style='color:#7F8C8D'>⚠️ Tájékoztatási célú.<br>Nem befektetési tanács.</small>",
                unsafe_allow_html=True)

# ── Főoldal – Quiz ha nincs profil ──────────────────────────
profile = st.session_state.get("profile")

if not profile:
    _show_quiz()
else:
    _show_home(profile)


def _show_quiz():
    st.markdown("""
    <div class="page-header">
      <h1>👋 Üdvözöl az InvestScan!</h1>
      <p>Töltsd ki a rövid tesztet, hogy személyre szabott befektetési elemzést kapj.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🎯 Befektetői Személyiségtest")
    st.markdown("*8 kérdés – kb. 2 perc*")

    with st.form("quiz_form"):
        q1 = st.radio(
            "1️⃣ Mikor szeretnéd a befektetéseid hozamát realizálni?",
            ["Kevesebb mint 1 év", "1–3 év", "3–7 év", "7 évnél több"],
            horizontal=True
        )
        q2 = st.radio(
            "2️⃣ Ha a portfóliód 25%-ot esik egy hónap alatt, mit tennél?",
            ["Azonnal eladnám", "Várnék és figyelnék", "Tartanám", "Többet vennék"],
            horizontal=True
        )
        q3 = st.radio(
            "3️⃣ Mi a fontosabb számodra?",
            ["Stabil évi osztalék", "Kiegyensúlyozott növekedés", "Gyors tőkenövekedés", "Rövid távú trading"],
            horizontal=True
        )
        q4 = st.radio(
            "4️⃣ Mekkora évi hozamot tartasz reálisnak/elvártnak?",
            ["5–8%", "8–15%", "15–25%", "25%+"],
            horizontal=True
        )
        q5 = st.radio(
            "5️⃣ Mennyi tapasztalatod van a tőzsdén?",
            ["Kezdő (< 1 év)", "Közepes (1–3 év)", "Haladó (3–7 év)", "Profi (7+ év)"],
            horizontal=True
        )
        q6 = st.radio(
            "6️⃣ Mennyi időt szánsz hetente elemzésre?",
            ["Szinte semmit", "1–2 óra", "3–5 óra", "5+ óra"],
            horizontal=True
        )
        q7 = st.radio(
            "7️⃣ Melyik piac érdekel elsősorban?",
            ["US részvények (NYSE/NASDAQ)", "EU részvények", "Mindkettő", "ETF-ek főleg"],
            horizontal=True
        )
        q8 = st.radio(
            "8️⃣ Fontosak-e számodra az ESG / fenntarthatósági szempontok?",
            ["Igen, szűrök rá", "Kicsit érdekel", "Nem különösebben"],
            horizontal=True
        )

        submitted = st.form_submit_button("📊 Profil meghatározása", use_container_width=True, type="primary")

    if submitted:
        profile = _calculate_profile(q1, q2, q3, q4, q5, q6)
        st.session_state["profile"] = profile
        st.session_state["preferred_market"] = q7
        st.session_state["esg_filter"] = q8
        st.success(f"✅ Profilod: **{PROFILE_LABELS[profile]}**")
        st.balloons()
        import time; time.sleep(1)
        st.rerun()


def _calculate_profile(q1, q2, q3, q4, q5, q6) -> str:
    """Egyszerű pontozás alapján profil meghatározás"""
    score = 0

    # Időhorizont
    horizon_map = {"Kevesebb mint 1 év": 0, "1–3 év": 1, "3–7 év": 2, "7 évnél több": 3}
    score += horizon_map.get(q1, 1)

    # Kockázattűrés
    risk_map = {"Azonnal eladnám": 0, "Várnék és figyelnék": 1, "Tartanám": 2, "Többet vennék": 3}
    score += risk_map.get(q2, 1)

    # Stílus
    style_map = {"Stabil évi osztalék": 0, "Kiegyensúlyozott növekedés": 1, "Gyors tőkenövekedés": 2, "Rövid távú trading": 3}
    score += style_map.get(q3, 1)

    # Hozamelvárás
    return_map = {"5–8%": 0, "8–15%": 1, "15–25%": 2, "25%+": 3}
    score += return_map.get(q4, 1)

    # Elemzési idő
    time_map = {"Szinte semmit": 0, "1–2 óra": 1, "3–5 óra": 2, "5+ óra": 3}
    score += time_map.get(q6, 1)

    # 0-15 pont → profil
    if score <= 4:    return "conservative"
    elif score <= 8:  return "balanced"
    elif score <= 11: return "growth"
    else:             return "active"


def _show_home(profile: str):
    from config import PROFILE_LABELS
    label = PROFILE_LABELS.get(profile, profile)

    st.markdown(f"""
    <div class="page-header">
      <h1>📊 InvestScan Dashboard</h1>
      <p>Profilod: {label} &nbsp;|&nbsp; Személyre szabott befektetési figyelő</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 👇 Navigálj az oldalak között a bal oldali menüvel!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="metric-card">
          <div class="card-title">📊 Dashboard</div>
          <div style="font-size:0.95em; color:#555; margin-top:6px">
            Napi top pick-ek a profilodnak megfelelően. Score-alapú rangsor.
          </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="metric-card">
          <div class="card-title">🔍 Screener</div>
          <div style="font-size:0.95em; color:#555; margin-top:6px">
            Adj hozzá ticker-eket és szűrj fundamentális / technikai mutatók alapján.
          </div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="metric-card">
          <div class="card-title">🌍 Makro</div>
          <div style="font-size:0.95em; color:#555; margin-top:6px">
            Fed kamatpálya, infláció, yield curve, VIX, szektor heatmap.
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.info("💡 **Első lépés:** Menj az **⚙️ Adatkezelés** oldalra, add meg a figyelni kívánt tickereket, majd indítsd el az adatgyűjtést!")
