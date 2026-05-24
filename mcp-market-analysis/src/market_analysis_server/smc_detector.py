"""Algorithmic Smart Money Concepts (SMC) detection from pure OHLCV data.

No TradingView dependency. No scraping.
Implements: Order Blocks, Fair Value Gaps, PDH/PDL, Swing High/Low,
Liquidity Sweeps, BOS/CHoCH detection.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class OrderBlock:
    type: str  # "demand" or "supply"
    high: float
    low: float
    close: float
    index: int  # bar index (0 = most recent)
    strength: int  # number of bars before impulse


@dataclass
class FairValueGap:
    type: str  # "BISI" (buy-side imbalance) or "SIBI" (sell-side imbalance)
    high: float
    low: float
    index: int
    filled: bool = False


@dataclass
class DailyLevels:
    pdh: float  # Previous Day High
    pdl: float  # Previous Day Low
    pdc: float  # Previous Day Close
    current_day_open: float


@dataclass
class SwingPoint:
    type: str  # "HH", "HL", "LH", "LL"
    price: float
    index: int


@dataclass
class LiquiditySweep:
    type: str  # "bullish" (swept lows, reversed up) or "bearish" (swept highs, reversed down)
    swept_level: float
    swept_index: int
    close_price: float
    pip_depth: float


@dataclass
class SMCResult:
    order_blocks: list = field(default_factory=list)
    fair_value_gaps: list = field(default_factory=list)
    daily_levels: DailyLevels = None
    swing_points: list = field(default_factory=list)
    liquidity_sweeps: list = field(default_factory=list)
    bos_levels: list = field(default_factory=list)
    choch_detected: bool = False
    current_bias: str = "NEUTRAL"


def detect_swing_points(high: np.ndarray, low: np.ndarray, window: int = 5) -> list[SwingPoint]:
    """Detect swing highs and lows using a rolling window approach.

    A swing high is a bar whose high is the maximum in a window of `window` bars
    on each side. Similarly for swing lows.
    """
    n = len(high)
    if n < window * 2 + 1:
        return []

    swings = []

    for i in range(window, n - window):
        # Swing High
        if high[i] == np.max(high[i - window:i + window + 1]):
            swings.append(SwingPoint(type="HH", price=float(high[i]), index=i))

        # Swing Low
        if low[i] == np.min(low[i - window:i + window + 1]):
            swings.append(SwingPoint(type="LL", price=float(low[i]), index=i))

    # Classify as HH/HL/LH/LL by comparing to previous swing
    classified = []
    for i, s in enumerate(swings):
        if s.type in ("HH", "LL"):
            if i > 0:
                prev = swings[i - 1]
                if s.type == "HH":
                    s.type = "HH" if s.price > prev.price else "LH"
                else:
                    s.type = "LL" if s.price < prev.price else "HL"
        classified.append(s)

    return swings


def detect_order_blocks(open_, high, low, close, lookback: int = 50) -> list[OrderBlock]:
    """Detect order blocks: the last candle before a strong impulse move.

    Bullish OB: last bearish candle before 3+ consecutive bullish closes
    Bearish OB: last bullish candle before 3+ consecutive bearish closes
    """
    o = np.asarray(open_, dtype=np.float64)
    h = np.asarray(high, dtype=np.float64)
    l = np.asarray(low, dtype=np.float64)
    c = np.asarray(close, dtype=np.float64)
    n = len(o)

    if n < 4:
        return []

    blocks = []
    recent_start = max(0, n - lookback)

    for i in range(recent_start + 3, n):
        # Check last 3 candles for consecutive direction
        bullish_run = all(c[j] > o[j] for j in range(i - 3, i))
        bearish_run = all(c[j] < o[j] for j in range(i - 3, i))

        if bullish_run:
            # OB is the candle before the impulse (i-4)
            ob_idx = i - 4
            if ob_idx >= 0 and c[ob_idx] < o[ob_idx]:  # Bearish OB candle
                blocks.append(OrderBlock(
                    type="demand",
                    high=float(h[ob_idx]),
                    low=float(l[ob_idx]),
                    close=float(c[ob_idx]),
                    index=n - 1 - ob_idx,
                    strength=3,
                ))

        if bearish_run:
            ob_idx = i - 4
            if ob_idx >= 0 and c[ob_idx] > o[ob_idx]:  # Bullish OB candle
                blocks.append(OrderBlock(
                    type="supply",
                    high=float(h[ob_idx]),
                    low=float(l[ob_idx]),
                    close=float(c[ob_idx]),
                    index=n - 1 - ob_idx,
                    strength=3,
                ))

    return blocks[-6:]  # Return up to 6 most recent blocks


def detect_fair_value_gaps(high, low, lookback: int = 30) -> list[FairValueGap]:
    """Detect Fair Value Gaps (FVG) from OHLCV bars.

    BISI (Buy-side Imbalance Sell-side Inefficiency): 3-candle pattern where
      candle[1] low > candle[-1] high  (gap between)

    SIBI (Sell-side Imbalance Buy-side Inefficiency): 3-candle pattern where
      candle[-1] low > candle[1] high  (gap between)
    """
    h = np.asarray(high, dtype=np.float64)
    l = np.asarray(low, dtype=np.float64)
    n = len(h)

    if n < 3:
        return []

    fvgs = []
    start = max(0, n - lookback)

    for i in range(start + 2, n):
        # BISI: bullish FVG
        if l[i] > h[i - 2]:
            fvgs.append(FairValueGap(
                type="BISI",
                high=float(l[i]),
                low=float(h[i - 2]),
                index=n - 1 - i,
            ))

        # SIBI: bearish FVG
        if h[i] < l[i - 2]:
            fvgs.append(FairValueGap(
                type="SIBI",
                high=float(l[i - 2]),
                low=float(h[i]),
                index=n - 1 - i,
            ))

    return fvgs


def detect_liquidity_sweeps(
    high, low, close, swing_points: list[SwingPoint], pip_threshold: float = 5.0
) -> list[LiquiditySweep]:
    """Detect when price sweeps a swing level and reverses.

    Bullish sweep: price wicks below a swing low, then closes back above it
    Bearish sweep: price wicks above a swing high, then closes back below it
    """
    h = np.asarray(high, dtype=np.float64)
    l = np.asarray(low, dtype=np.float64)
    c = np.asarray(close, dtype=np.float64)
    n = len(h)

    if n < 3:
        return []

    sweeps = []

    for sp in swing_points:
        if sp.index >= n - 1:
            continue

        # Check bars after the swing point for sweeps
        for j in range(sp.index + 1, min(sp.index + 20, n)):
            if sp.type in ("HH", "LH"):
                # Bearish sweep: a later bar's high breaks above this swing high,
                # then closes below it
                pip_depth = h[j] - sp.price
                if h[j] > sp.price and pip_depth >= pip_threshold:
                    sweeps.append(LiquiditySweep(
                        type="bearish",
                        swept_level=sp.price,
                        swept_index=n - 1 - sp.index,
                        close_price=float(c[j]),
                        pip_depth=round(float(pip_depth), 1),
                    ))
                    break

            elif sp.type in ("HL", "LL"):
                # Bullish sweep: a later bar's low breaks below this swing low,
                # then closes above it
                pip_depth = sp.price - l[j]
                if l[j] < sp.price and pip_depth >= pip_threshold:
                    sweeps.append(LiquiditySweep(
                        type="bullish",
                        swept_level=sp.price,
                        swept_index=n - 1 - sp.index,
                        close_price=float(c[j]),
                        pip_depth=round(float(pip_depth), 1),
                    ))
                    break

    return sweeps


def detect_bos_choch(
    close: np.ndarray, swing_points: list[SwingPoint], breakout_threshold: float = 3.0
) -> tuple[list[float], bool]:
    """Detect Break of Structure (BOS) and Change of Character (CHoCH).

    BOS: Price breaks a recent swing high (in uptrend) or swing low (in downtrend),
         confirming trend continuation.

    CHoCH: Price breaks a recent swing high in a downtrend (or low in uptrend),
           signaling a potential trend reversal.
    """
    c = np.asarray(close, dtype=np.float64)
    n = len(c)
    bos_levels = []
    choch = False

    if len(swing_points) < 3:
        return bos_levels, choch

    recent_swings = [s for s in swing_points if s.index >= n - 50]

    # Determine current trend from swing structure
    last_five = recent_swings[-5:] if len(recent_swings) >= 5 else recent_swings
    if len(last_five) >= 3:
        higher_highs = sum(1 for s in last_five if s.type == "HH")
        lower_lows = sum(1 for s in last_five if s.type == "LL")

        if higher_highs > lower_lows:
            # Uptrend: BOS = breaking above recent HH
            for sp in recent_swings:
                if sp.type == "HH" and sp.index < n - 1:
                    if c[-1] > sp.price:
                        bos_levels.append(sp.price)
        elif lower_lows > higher_highs:
            # Downtrend: BOS = breaking below recent LL
            for sp in recent_swings:
                if sp.type == "LL" and sp.index < n - 1:
                    if c[-1] < sp.price:
                        bos_levels.append(sp.price)

        # CHoCH detection: trend structure breaks
        if higher_highs > lower_lows:
            # Was uptrend, check for LH (first sign of reversal)
            if any(s.type == "LH" for s in last_five[-3:]):
                choch = True
        elif lower_lows > higher_highs:
            # Was downtrend, check for HL (first sign of reversal)
            if any(s.type == "HL" for s in last_five[-3:]):
                choch = True

    return list(set(bos_levels)), choch


def determine_bias(swing_points: list[SwingPoint], close: np.ndarray) -> str:
    """Determine market structure bias from swing points and price context.

    Priority:
    1. Pure HH/HL structure → BULLISH
    2. Pure LL/LH structure → BEARISH
    3. Mixed → NEUTRAL with direction hint
    """
    if len(swing_points) < 2:
        return "NEUTRAL"

    recent = swing_points[-6:] if len(swing_points) >= 6 else swing_points
    hh_count = sum(1 for s in recent if s.type == "HH")
    hl_count = sum(1 for s in recent if s.type == "HL")
    lh_count = sum(1 for s in recent if s.type == "LH")
    ll_count = sum(1 for s in recent if s.type == "LL")

    bullish_score = hh_count + hl_count
    bearish_score = lh_count + ll_count

    if bullish_score >= 3 and bearish_score <= 1:
        return "BULLISH"
    elif bearish_score >= 3 and bullish_score <= 1:
        return "BEARISH"
    elif bullish_score > bearish_score:
        return "SLIGHTLY_BULLISH"
    elif bearish_score > bullish_score:
        return "SLIGHTLY_BEARISH"
    return "NEUTRAL"


def detect_smc_levels(
    df: pd.DataFrame, window: int = 5, lookback: int = 100
) -> SMCResult:
    """Full SMC analysis from OHLCV DataFrame.

    Args:
        df: DataFrame with columns [open, high, low, close] (optionally with 'timeframe')
        window: Swing point detection window
        lookback: Max bars to look back for OBs and FVGs

    Returns:
        SMCResult with all detected levels
    """
    open_ = df["open"].values.astype(np.float64)
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    close = df["close"].values.astype(np.float64)

    swing_points = detect_swing_points(high, low, window)
    order_blocks = detect_order_blocks(open_, high, low, close, lookback)
    fvgs = detect_fair_value_gaps(high, low, lookback)
    sweeps = detect_liquidity_sweeps(high, low, close, swing_points)
    bos_levels, choch = detect_bos_choch(close, swing_points)
    bias = determine_bias(swing_points, close)

    # Daily levels from the data (last 2 days if available)
    # Using the last daily bar's high/low/close as PDH/PDL
    daily = DailyLevels(
        pdh=round(float(np.max(high[-96:])), 2) if len(high) >= 96 else round(float(np.max(high)), 2),
        pdl=round(float(np.min(low[-96:])), 2) if len(low) >= 96 else round(float(np.min(low)), 2),
        pdc=round(float(close[-1]), 2),
        current_day_open=round(float(open_[-1]), 2),
    )

    return SMCResult(
        order_blocks=order_blocks,
        fair_value_gaps=fvgs,
        daily_levels=daily,
        swing_points=swing_points[-12:] if len(swing_points) > 12 else swing_points,
        liquidity_sweeps=sweeps,
        bos_levels=bos_levels,
        choch_detected=choch,
        current_bias=bias,
    )
