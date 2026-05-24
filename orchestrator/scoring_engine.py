"""V2 Confluence Scoring Engine — 0-10 scoring from MCP server data.

Pure scoring logic. No TradingView dependency. No scraping.
Input: structured data from mcp-market-analysis
Output: score, direction, entry/SL/TP levels, detailed reasons.
"""

from dataclasses import dataclass, field

# ── Scoring weights ──────────────────────────────────────────
BOS_CONFIRMED = 2.0
OB_REACTION = 2.0
MULTI_TF_ALIGNMENT = 2.0
CLEAN_RR = 2.0
PATTERN_CONFIRMATION = 1.0
DIVERGENCE_BONUS = 1.0
FVG_MAGNET = 1.0
SWEEP_CONFIRMATION = 1.0
# Penalties
COUNTER_SWEEP_PENALTY = -1.0
CHoCH_WARNING = -0.5

# Total max: 11 points (with all bonuses)

MIN_SCORE_TO_TRADE = 6
MIN_RR_RATIO = 1.2
# SL/TP in PRICE UNITS (30 pips = 3.00 price movement, etc.)
# Works for both 2-digit and 3-digit broker pricing
MAX_SL_POINTS = 7.0
MIN_SL_POINTS = 3.0
MAX_TP_POINTS = 15.0


@dataclass
class TradeSetup:
    direction: str  # "BUY", "SELL", or "NO_TRADE"
    score: float
    entry: float
    sl: float
    tp: float
    rr_ratio: float
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    confluence_details: dict = field(default_factory=dict)


def score_setup(analysis_data: dict) -> TradeSetup:
    """Score a trade setup from comprehensive analysis data.

    Args:
        analysis_data: dict from collect_all_analysis() with keys:
            - indicators: Multi-TF indicator results
            - smc: SMC levels from H1
            - patterns: Candlestick patterns per timeframe

    Returns:
        TradeSetup with direction, score, entry/SL/TP, and reasons
    """
    score = 0.0
    reasons = []
    warnings = []

    # ── Extract data ──────────────────────────────────────────
    smc = analysis_data.get("smc", {})
    indicators = analysis_data.get("indicators", {}).get("results", [])
    patterns = analysis_data.get("patterns", {})

    # Build indicator lookup by timeframe
    ind_by_tf = {}
    for ind in indicators:
        ind_by_tf[ind.get("timeframe", "")] = ind

    # Get current price from M15 close
    m15 = ind_by_tf.get("M15", {})
    h1 = ind_by_tf.get("H1", {})
    h4 = ind_by_tf.get("H4", {})
    d1 = ind_by_tf.get("D1", {})

    price = m15.get("last_close", 0)
    if price == 0:
        price = h1.get("last_close", 0)
    if price == 0:
        return TradeSetup("NO_TRADE", 0, 0, 0, 0, 0, ["No price data"])

    # ── Determine direction from SMC structure ────────────────
    direction = _determine_direction(smc, ind_by_tf)
    if direction is None:
        return TradeSetup("NO_TRADE", 0, price, 0, 0, 0, ["No clear direction from structure"])

    # ── 1. BOS Confirmation (+2) ─────────────────────────────
    bos_levels = smc.get("bos_levels", [])
    if direction == "BUY":
        bos_confirm = any(price > b for b in bos_levels)
    else:
        bos_confirm = any(price < b for b in bos_levels)

    if bos_confirm:
        score += BOS_CONFIRMED
        reasons.append(f"BOS confirmed {direction.lower()} (+{BOS_CONFIRMED:.0f})")
    else:
        reasons.append("BOS not confirmed (+0)")

    # ── 2. Order Block Reaction (+2) ─────────────────────────
    obs = smc.get("order_blocks", [])
    nearest_demand = None
    nearest_supply = None

    for ob in obs:
        if ob["type"] == "demand" and ob["low"] < price:
            if nearest_demand is None or ob["high"] > nearest_demand["high"]:
                nearest_demand = ob
        elif ob["type"] == "supply" and ob["high"] > price:
            if nearest_supply is None or ob["low"] < nearest_supply["low"]:
                nearest_supply = ob

    ob_score = 0
    if direction == "BUY" and nearest_demand:
        dist = price - nearest_demand["high"]
        if 0 <= dist <= 5.0:
            ob_score = OB_REACTION
            reasons.append(f"Reacting from demand OB ({nearest_demand['high']:.2f}-{nearest_demand['low']:.2f}) (+{OB_REACTION:.0f})")
    elif direction == "SELL" and nearest_supply:
        dist = nearest_supply["low"] - price
        if 0 <= dist <= 5.0:
            ob_score = OB_REACTION
            reasons.append(f"Reacting from supply OB ({nearest_supply['low']:.2f}-{nearest_supply['high']:.2f}) (+{OB_REACTION:.0f})")

    if ob_score == 0:
        reasons.append("No relevant OB reaction (+0)")
    score += ob_score

    # ── 3. Multi-Timeframe Alignment (+2) ────────────────────
    mtf_score = _score_multi_tf(direction, ind_by_tf)
    score += mtf_score
    if mtf_score >= 2:
        reasons.append(f"Multi-TF aligned: EMAs + RSI zones (+{mtf_score:.0f})")
    elif mtf_score >= 1:
        reasons.append(f"Multi-TF partially aligned (+{mtf_score:.0f})")
    else:
        reasons.append("Multi-TF not aligned (+0)")

    # ── 4. Clean R:R (+2) ────────────────────────────────────
    h1_atr = h1.get("indicators", {}).get("atr14", 0) if h1 else 0
    entry, sl, tp = _calculate_levels(direction, price, smc, nearest_demand, nearest_supply, atr=h1_atr)

    if entry and sl and tp and sl > 0:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0

        if risk > MAX_SL_POINTS:
            warnings.append(f"SL wide ({risk:.1f} pts), tightening to {MAX_SL_POINTS}")
            if direction == "BUY":
                sl = entry - MAX_SL_POINTS
            else:
                sl = entry + MAX_SL_POINTS
            risk = MAX_SL_POINTS
            rr = abs(tp - entry) / risk

        if rr >= MIN_RR_RATIO:
            score += CLEAN_RR
            reasons.append(f"Clean R:R 1:{rr:.1f} (SL:{sl:.2f} TP:{tp:.2f}) (+{CLEAN_RR:.0f})")
        else:
            reasons.append(f"Poor R:R 1:{rr:.1f} (+0)")
    else:
        reasons.append("Cannot calculate valid SL/TP (+0)")

    # ── 5. Candlestick Pattern Confirmation (+1) ─────────────
    pat_score = _score_patterns(patterns, direction)
    score += pat_score
    if pat_score > 0:
        reasons.append(f"Candlestick patterns confirm {direction.lower()} (+{pat_score:.0f})")
    else:
        reasons.append("No confirming candlestick patterns (+0)")

    # ── 6. Divergence Bonus (+1) ─────────────────────────────
    div_score = _score_divergence(ind_by_tf, direction)
    score += div_score
    if div_score > 0:
        reasons.append(f"Divergence supports {direction.lower()} (+{div_score:.0f})")
    elif div_score < 0:
        warnings.append("Counter-direction divergence detected")

    # ── 7. FVG Magnet (+1) ───────────────────────────────────
    fvgs = smc.get("fair_value_gaps", [])
    fvg_score = _score_fvg(fvgs, direction, price)
    score += fvg_score
    if fvg_score > 0:
        reasons.append(f"FVG magnet in {direction.lower()} direction (+{fvg_score:.0f})")

    # ── 8. Liquidity Sweep Confirmation (+1) ─────────────────
    sweeps = smc.get("liquidity_sweeps", [])
    sweep_score = _score_sweeps(sweeps, direction)
    score += sweep_score
    if sweep_score > 0:
        reasons.append(f"Liquidity sweep confirms {direction.lower()} (+{sweep_score:.0f})")
    elif sweep_score < 0:
        warnings.append("Counter-direction sweep — trap risk (-1)")

    # ── CHoCH Warning ─────────────────────────────────────────
    if smc.get("choch_detected"):
        score += CHoCH_WARNING
        warnings.append("CHoCH detected — reversal possible (-0.5)")

    # Clamp score
    score = max(0, round(score, 1))

    return TradeSetup(
        direction=direction,
        score=score,
        entry=round(entry, 2),
        sl=round(sl, 2),
        tp=round(tp, 2),
        rr_ratio=round(rr, 2),
        reasons=reasons,
        warnings=warnings,
        confluence_details={
            "bos": bos_confirm,
            "ob_reaction": ob_score > 0,
            "multi_tf": mtf_score,
            "clean_rr": rr >= MIN_RR_RATIO,
            "patterns": pat_score > 0,
            "divergence": div_score,
            "fvg": fvg_score > 0,
            "sweep": sweep_score,
        },
    )


def _determine_direction(smc: dict, ind_by_tf: dict) -> str:
    """Determine trade direction from SMC structure."""
    bias = smc.get("current_bias", "NEUTRAL")

    if bias in ("BULLISH",):
        return "BUY"
    elif bias in ("BEARISH",):
        return "SELL"
    elif bias in ("SLIGHTLY_BULLISH",):
        # Check if EMAs confirm
        m15 = ind_by_tf.get("M15", {}).get("indicators", {})
        h1 = ind_by_tf.get("H1", {}).get("indicators", {})
        if m15.get("ema9", 0) > m15.get("ema21", 0) and h1.get("ema9", 0) > h1.get("ema21", 0):
            return "BUY"
        return None
    elif bias in ("SLIGHTLY_BEARISH",):
        m15 = ind_by_tf.get("M15", {}).get("indicators", {})
        h1 = ind_by_tf.get("H1", {}).get("indicators", {})
        if m15.get("ema9", 0) < m15.get("ema21", 0) and h1.get("ema9", 0) < h1.get("ema21", 0):
            return "SELL"
        return None

    return None


def _score_multi_tf(direction: str, ind_by_tf: dict) -> float:
    """Score multi-timeframe alignment using EMA and RSI.

    Returns 0, 1, or 2 based on alignment across timeframes.
    """
    alignments = 0
    total = 0

    for tf in ["M15", "H1", "H4"]:
        ind = ind_by_tf.get(tf, {}).get("indicators", {})
        if not ind:
            continue
        total += 1

        ema9 = ind.get("ema9", 0)
        ema21 = ind.get("ema21", 0)
        rsi14 = ind.get("rsi14", 50)

        ema_aligned = (direction == "BUY" and ema9 > ema21) or (direction == "SELL" and ema9 < ema21)
        rsi_aligned = (direction == "BUY" and rsi14 < 70) or (direction == "SELL" and rsi14 > 30)

        if ema_aligned and rsi_aligned:
            alignments += 1

    if total == 0:
        return 0
    ratio = alignments / total

    if ratio >= 0.75:
        return 2.0
    elif ratio >= 0.5:
        return 1.0
    return 0


def _score_patterns(patterns: dict, direction: str) -> float:
    """Score candlestick pattern confirmation."""
    bull_patterns = ["ENGULFING", "HAMMER", "MORNING_STAR", "PIN_BAR", "MARUBOZU"]
    bear_patterns = ["ENGULFING", "SHOOTING_STAR", "EVENING_STAR", "PIN_BAR", "MARUBOZU"]

    confirm = 0
    for tf in ["M15", "H1"]:
        pat = patterns.get(tf, {})
        strongest = pat.get("strongest_bullish", "") if direction == "BUY" else pat.get("strongest_bearish", "")
        if strongest in (bull_patterns if direction == "BUY" else bear_patterns):
            confirm += 0.5

    return min(confirm, 1.0)


def _score_divergence(ind_by_tf: dict, direction: str) -> float:
    """Score divergence detection."""
    for tf in ["H4", "H1"]:
        ind = ind_by_tf.get(tf, {})
        div = ind.get("divergence")
        if div:
            div_type = div.get("type", "")
            if (direction == "BUY" and div_type == "bullish") or (direction == "SELL" and div_type == "bearish"):
                return 1.0
            elif (direction == "BUY" and div_type == "bearish") or (direction == "SELL" and div_type == "bullish"):
                return -0.5
    return 0


def _score_fvg(fvgs: list, direction: str, price: float) -> float:
    """Score FVG magnet effect."""
    for fvg in fvgs:
        fvg_type = fvg.get("type", "")
        fvg_high = fvg.get("high", 0)
        fvg_low = fvg.get("low", 0)

        if direction == "BUY" and fvg_type == "BISI" and fvg_low > price:
            gap = fvg_high - fvg_low
            return 1.0 if gap >= 3.0 else 0.5
        elif direction == "SELL" and fvg_type == "SIBI" and fvg_high < price:
            gap = fvg_high - fvg_low
            return 1.0 if gap >= 3.0 else 0.5

    return 0


def _score_sweeps(sweeps: list, direction: str) -> float:
    """Score liquidity sweep confirmation."""
    for sw in sweeps:
        sw_type = sw.get("type", "")
        depth = sw.get("pip_depth", 0)

        if (direction == "BUY" and sw_type == "bullish") or (direction == "SELL" and sw_type == "bearish"):
            return 1.0 if depth >= 5 else 0.5
        elif (direction == "BUY" and sw_type == "bearish") or (direction == "SELL" and sw_type == "bullish"):
            return -1.0

    return 0


def _calculate_levels(direction: str, price: float, smc: dict,
                      nearest_demand: dict, nearest_supply: dict,
                      atr: float = 0) -> tuple:
    """Calculate entry, SL, and TP from structural levels.

    Uses ATR-based minimum SL when available.
    SL = max(structural_level, ATR * 0.5, MIN_SL_POINTS)
    """
    entry = price
    sl = 0
    tp = 0

    # Dynamic minimum SL based on ATR (volatility-adjusted)
    dynamic_min_sl = MIN_SL_POINTS
    if atr > 0:
        dynamic_min_sl = max(MIN_SL_POINTS, atr * 0.5)

    daily = smc.get("daily_levels", {})
    pdh = daily.get("pdh", 0)
    pdl = daily.get("pdl", 0)

    if direction == "BUY":
        # SL: below nearest demand OB, or below PDL, or ATR-based
        if nearest_demand:
            sl = nearest_demand["low"] - 0.50
        elif pdl:
            sl = pdl - 0.50
        else:
            sl = price - dynamic_min_sl

        # Ensure minimum SL distance (ATR-adjusted)
        if sl >= price - dynamic_min_sl:
            sl = price - dynamic_min_sl

        # TP: nearest supply OB, PDH, or FVG above
        targets = []
        if nearest_supply and nearest_supply["low"] > price + 2.0:
            targets.append(nearest_supply["low"])
        if pdh and pdh > price + 5.0:
            targets.append(pdh)

        for fvg in smc.get("fair_value_gaps", []):
            if fvg.get("type") == "BISI" and fvg["low"] > price + 2.0:
                targets.append(fvg["low"])

        for b in smc.get("bos_levels", []):
            if b > price + 2.0:
                targets.append(b)

        if targets:
            tp = min(targets)
        else:
            tp = price + (dynamic_min_sl * 2.0)  # Default 1:2 RR

        if tp <= price + dynamic_min_sl:
            tp = price + MAX_TP_POINTS * 0.6

    else:  # SELL
        # SL: above nearest supply OB, or above PDH
        if nearest_supply:
            sl = nearest_supply["high"] + 0.50
        elif pdh:
            sl = pdh + 0.50
        else:
            sl = price + dynamic_min_sl

        if sl <= price + dynamic_min_sl:
            sl = price + dynamic_min_sl

        # TP: nearest demand OB, PDL, or FVG below
        targets = []
        if nearest_demand and nearest_demand["high"] < price - 2.0:
            targets.append(nearest_demand["high"])
        if pdl and pdl < price - 5.0:
            targets.append(pdl)

        for fvg in smc.get("fair_value_gaps", []):
            if fvg.get("type") == "SIBI" and fvg["high"] < price - 2.0:
                targets.append(fvg["high"])

        for b in smc.get("bos_levels", []):
            if b < price - 2.0:
                targets.append(b)

        if targets:
            tp = max(targets)
        else:
            tp = price - (dynamic_min_sl * 2.0)

        if tp >= price - dynamic_min_sl:
            tp = price - MAX_TP_POINTS * 0.6

    # Clamp SL and TP
    sl_dist = abs(entry - sl)
    if sl_dist > MAX_SL_POINTS:
        sl = entry - MAX_SL_POINTS if direction == "BUY" else entry + MAX_SL_POINTS
    elif sl_dist < dynamic_min_sl:
        sl = entry - dynamic_min_sl if direction == "BUY" else entry + dynamic_min_sl

    tp_dist = abs(tp - entry)
    if tp_dist > MAX_TP_POINTS:
        tp = entry + MAX_TP_POINTS if direction == "BUY" else entry - MAX_TP_POINTS

    return entry, sl, tp
