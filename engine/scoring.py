"""
Pontozó motor – 0-100 composite score számítása
"""
import math
import logging

logger = logging.getLogger(__name__)


# ── Segédfüggvények ──────────────────────────────────────────

def sigmoid_score(value, midpoint, steepness=1.0, invert=False) -> float:
    """Sigmoid alapú normalizálás 0-100 skálára"""
    try:
        s = 1 / (1 + math.exp(-steepness * (value - midpoint)))
        score = s * 100
        return 100 - score if invert else score
    except:
        return 50.0


def linear_score(value, low, high, invert=False) -> float:
    """Lineáris interpoláció 0-100 skálára"""
    if value is None:
        return 50.0
    score = max(0, min(100, (value - low) / (high - low) * 100))
    return 100 - score if invert else score


def safe(val, default=50.0):
    """None-safe érték"""
    return val if val is not None and not math.isnan(val) else default


# ── Fundamentális score ──────────────────────────────────────

def fundamental_score(fund) -> float:
    """
    Fundamentális mutatókból 0-100 pont.
    fund: Fundamental DB rekord vagy dict
    """
    if fund is None:
        return 50.0

    def g(key):
        try:
            v = getattr(fund, key) if hasattr(fund, key) else fund.get(key)
            return None if v is None or (isinstance(v, float) and math.isnan(v)) else v
        except:
            return None

    scores = []

    # P/E ratio (alacsonyabb = jobb, 5-30 range)
    pe = g("pe_ratio")
    if pe and pe > 0:
        scores.append(("pe", linear_score(pe, 5, 35, invert=True), 1.5))

    # PEG ratio
    peg = g("peg_ratio")
    if peg and peg > 0:
        s = 100 if peg < 0.8 else linear_score(peg, 0.8, 3.0, invert=True)
        scores.append(("peg", s, 2.0))

    # ROE (magasabb = jobb)
    roe = g("roe")
    if roe is not None:
        roe_pct = roe * 100 if abs(roe) < 2 else roe
        s = sigmoid_score(roe_pct, 15, steepness=0.08)
        scores.append(("roe", s, 1.8))

    # EPS YoY növekedés
    eps_g = g("eps_growth_yoy")
    if eps_g is not None:
        eps_pct = eps_g * 100 if abs(eps_g) < 2 else eps_g
        s = sigmoid_score(eps_pct, 10, steepness=0.07)
        scores.append(("eps_growth", s, 1.5))

    # Debt/Equity (alacsonyabb = jobb)
    de = g("debt_equity")
    if de is not None:
        de_norm = de / 100 if de > 10 else de
        s = linear_score(de_norm, 0, 2.5, invert=True)
        scores.append(("debt_eq", s, 1.2))

    # FCF Yield
    fcf = g("fcf_yield")
    if fcf is not None:
        fcf_pct = fcf * 100 if abs(fcf) < 1 else fcf
        s = sigmoid_score(fcf_pct, 3, steepness=0.3)
        scores.append(("fcf", s, 1.3))

    # Dividend yield (konzervatív befektetőknek hasznos)
    div = g("div_yield")
    if div is not None:
        div_pct = div * 100 if div < 1 else div
        s = sigmoid_score(div_pct, 2.5, steepness=0.4)
        scores.append(("div", s, 0.8))

    # Revenue növekedés
    rev_g = g("revenue_growth")
    if rev_g is not None:
        rev_pct = rev_g * 100 if abs(rev_g) < 2 else rev_g
        s = sigmoid_score(rev_pct, 8, steepness=0.07)
        scores.append(("rev_growth", s, 1.2))

    if not scores:
        return 50.0

    total_w = sum(w for _, _, w in scores)
    weighted = sum(s * w for _, s, w in scores) / total_w
    return round(max(0, min(100, weighted)), 1)


# ── Technikai score ──────────────────────────────────────────

def technical_score(tech) -> float:
    """Technikai indikátorokból 0-100 pont"""
    if tech is None:
        return 50.0

    def g(key):
        try:
            v = getattr(tech, key) if hasattr(tech, key) else tech.get(key)
            return None if v is None or (isinstance(v, float) and math.isnan(v)) else v
        except:
            return None

    scores = []

    # RSI
    rsi = g("rsi_14")
    if rsi is not None:
        if rsi < 25:     s = 85   # erősen túladott – vételi jel
        elif rsi < 35:   s = 75
        elif rsi < 45:   s = 65
        elif rsi <= 60:  s = 80   # egészséges momentum
        elif rsi <= 70:  s = 55
        else:            s = 20   # túlvett
        scores.append(("rsi", s, 2.5))

    # MACD – bullish vagy bearish
    macd    = g("macd")
    macd_s  = g("macd_signal")
    macd_h  = g("macd_hist")
    if macd is not None and macd_s is not None:
        if macd > macd_s:
            s = 75 if macd > 0 else 60
        else:
            s = 30 if macd < 0 else 45
        # Histogram trend
        if macd_h is not None:
            if macd_h > 0:  s = min(100, s + 5)
            else:           s = max(0, s - 5)
        scores.append(("macd", s, 2.0))

    # Golden / Death Cross
    ma50  = g("ma_50")
    ma200 = g("ma_200")
    if ma50 and ma200:
        ratio = ma50 / ma200
        if ratio > 1.03:   s = 85
        elif ratio > 1.0:  s = 70
        elif ratio > 0.97: s = 35
        else:               s = 15
        scores.append(("cross", s, 2.2))

    # Bollinger – ár vs. sávok
    close   = g("close") if hasattr(tech, "close") else None
    bb_mid  = g("bb_middle")
    bb_up   = g("bb_upper")
    bb_low  = g("bb_lower")
    if close and bb_mid and bb_up and bb_low:
        bb_range = bb_up - bb_low
        pos = (close - bb_low) / bb_range if bb_range > 0 else 0.5
        if pos > 0.85:     s = 30   # tetején – túlvett
        elif pos > 0.6:    s = 70   # felső fele – bullish
        elif pos > 0.4:    s = 55   # közép – semleges
        elif pos > 0.15:   s = 65   # alsó fele
        else:               s = 80   # alján – oversold, vételi alap
        scores.append(("bb", s, 1.0))

    # Volume spike
    vol     = g("volume")
    vol_avg = g("volume_avg20")
    if vol and vol_avg and vol_avg > 0:
        ratio = vol / vol_avg
        if ratio > 1.5:   s = 75
        elif ratio > 1.0: s = 60
        else:              s = 45
        scores.append(("vol", s, 0.8))

    if not scores:
        return 50.0

    total_w = sum(w for _, _, w in scores)
    weighted = sum(s * w for _, s, w in scores) / total_w
    return round(max(0, min(100, weighted)), 1)


# ── Composite score ──────────────────────────────────────────

def compute_scores(fund, tech, macro_score: float = 50.0) -> dict:
    fs = fundamental_score(fund)
    ts = technical_score(tech)
    ms = float(macro_score)
    return {
        "fundamental": fs,
        "technical":   ts,
        "macro":       ms,
    }


def composite(scores: dict, weights: dict) -> float:
    fs = scores.get("fundamental", 50)
    ts = scores.get("technical", 50)
    ms = scores.get("macro", 50)
    c = (
        fs * weights.get("fundamental", 0.5) +
        ts * weights.get("technical", 0.3) +
        ms * weights.get("macro", 0.2)
    )
    return round(max(0, min(100, c)), 1)


def score_to_signal(score: float) -> tuple:
    """(jelzés szöveg, szín)"""
    if score >= 72:   return "🟢 VÉTEL",   "#27AE60"
    elif score >= 58: return "🟡 FIGYELD",  "#F39C12"
    elif score >= 42: return "⚪ TARTSD",   "#95A5A6"
    else:             return "🔴 KERÜLD",  "#E74C3C"
