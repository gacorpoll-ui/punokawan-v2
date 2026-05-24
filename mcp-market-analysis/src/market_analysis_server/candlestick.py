"""Pure Python candlestick pattern detection.

ta-lib may not be available on Windows/Python 3.14.
This module implements key patterns directly from OHLCV data.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass
class DetectedPattern:
    name: str
    index: int  # bar index (0 = most recent)
    strength: int  # -100 to 100 (like ta-lib)
    direction: str  # "bullish", "bearish", "neutral"


@dataclass
class CandlestickResult:
    patterns: list = field(default_factory=list)
    strongest_bullish: str = ""
    strongest_bearish: str = ""
    total_patterns: int = 0


def _body(open_, close):
    return abs(close - open_)


def _upper_shadow(high, open_, close):
    return high - max(open_, close)


def _lower_shadow(low, open_, close):
    return min(open_, close) - low


def _total_range(high, low):
    return high - low


def _is_bullish(open_, close):
    return close > open_


def detect_doji(open_, high, low, close, body_ratio=0.05):
    """Doji: body is very small relative to total range."""
    body = _body(open_, close)
    total = _total_range(high, low)
    if total == 0:
        return 0
    if body / total < body_ratio:
        return 100 if _is_bullish(open_, close) else -100
    return 0


def detect_hammer(open_, high, low, close):
    """Hammer: small body at top, long lower shadow (2x+ body), little/no upper shadow."""
    body = _body(open_, close)
    total = _total_range(high, low)
    if total == 0 or body == 0:
        return 0
    lower = _lower_shadow(low, open_, close)
    upper = _upper_shadow(high, open_, close)
    # Lower shadow >= 2x body, upper shadow <= 0.3x total
    if lower >= body * 2 and upper <= total * 0.1:
        return 100  # Bullish hammer
    return 0


def detect_shooting_star(open_, high, low, close):
    """Shooting Star: small body at bottom, long upper shadow, little lower shadow."""
    body = _body(open_, close)
    total = _total_range(high, low)
    if total == 0 or body == 0:
        return 0
    upper = _upper_shadow(high, open_, close)
    lower = _lower_shadow(low, open_, close)
    if upper >= body * 2 and lower <= total * 0.1:
        return -100  # Bearish shooting star
    return 0


def detect_engulfing(open_prev, close_prev, open_curr, close_curr):
    """Engulfing: current bar completely engulfs previous bar."""
    body_prev = _body(open_prev, close_prev)
    body_curr = _body(open_curr, close_curr)
    if body_prev == 0:
        return 0

    prev_bullish = _is_bullish(open_prev, close_prev)
    curr_bullish = _is_bullish(open_curr, close_curr)

    # Bullish engulfing: prev bearish, curr bullish, curr body engulfs prev body
    if not prev_bullish and curr_bullish:
        if close_curr > close_prev and open_curr < open_prev:
            return 100
    # Bearish engulfing: prev bullish, curr bearish, curr body engulfs prev body
    if prev_bullish and not curr_bullish:
        if close_curr < open_prev and open_curr > close_prev:
            return -100
    return 0


def detect_pin_bar(open_, high, low, close, nose_ratio=0.3, tail_ratio=2.0):
    """Pin Bar: long tail on one side, small nose on the other.

    Bullish pin: long lower wick, small upper wick
    Bearish pin: long upper wick, small lower wick
    """
    body = _body(open_, close)
    total = _total_range(high, low)
    if total == 0:
        return 0
    upper = _upper_shadow(high, open_, close)
    lower = _lower_shadow(low, open_, close)

    # Nose must be small relative to total range
    # Bullish pin: big lower shadow
    if lower > upper * tail_ratio and upper < total * nose_ratio:
        return 100
    # Bearish pin: big upper shadow
    if upper > lower * tail_ratio and lower < total * nose_ratio:
        return -100
    return 0


def detect_marubozu(open_, high, low, close, threshold=0.9):
    """Marubozu: very small wicks, body is most of the range."""
    body = _body(open_, close)
    total = _total_range(high, low)
    if total == 0:
        return 0
    if body / total > threshold:
        return 100 if _is_bullish(open_, close) else -100
    return 0


def detect_morning_star(o1, h1, l1, c1, o2, h2, l2, c2, o3, h3, l3, c3):
    """Morning Star: bearish → small body (gap down) → bullish (gap up, closes into first body)."""
    # Bar 1: strong bearish (body > 60% of range)
    b1_body = _body(o1, c1)
    b1_range = _total_range(h1, l1)
    if b1_range == 0:
        return 0
    if not (b1_body / b1_range > 0.5 and not _is_bullish(o1, c1)):
        return 0

    # Bar 2: small body (doji or spinning top), gaps below bar 1 close
    b2_body = _body(o2, c2)
    b2_range = _total_range(h2, l2)
    if b2_range == 0:
        return 0
    if not (b2_body / b2_range < 0.3):
        return 0

    # Bar 3: strong bullish, closes above midpoint of bar 1
    b3_body = _body(o3, c3)
    b3_range = _total_range(h3, l3)
    if b3_range == 0:
        return 0
    if _is_bullish(o3, c3) and b3_body / b3_range > 0.5 and c3 > o1:
        return 100
    return 0


def detect_evening_star(o1, h1, l1, c1, o2, h2, l2, c2, o3, h3, l3, c3):
    """Evening Star: bullish → small body (gap up) → bearish (gap down, closes into first body)."""
    b1_body = _body(o1, c1)
    b1_range = _total_range(h1, l1)
    if b1_range == 0:
        return 0
    if not (b1_body / b1_range > 0.5 and _is_bullish(o1, c1)):
        return 0

    b2_body = _body(o2, c2)
    b2_range = _total_range(h2, l2)
    if b2_range == 0:
        return 0
    if not (b2_body / b2_range < 0.3):
        return 0

    b3_body = _body(o3, c3)
    b3_range = _total_range(h3, l3)
    if b3_range == 0:
        return 0
    if not _is_bullish(o3, c3) and b3_body / b3_range > 0.5 and c3 < o1:
        return -100
    return 0


def detect_all_patterns(open_arr, high_arr, low_arr, close_arr) -> CandlestickResult:
    """Detect all candlestick patterns on an array of OHLCV bars.

    Returns patterns for the most recent bars only (last 5 bars
    for single-bar patterns, last 3 for multi-bar patterns).
    """
    o = np.asarray(open_arr, dtype=np.float64)
    h = np.asarray(high_arr, dtype=np.float64)
    l = np.asarray(low_arr, dtype=np.float64)
    c = np.asarray(close_arr, dtype=np.float64)
    n = len(o)

    if n < 3:
        return CandlestickResult()

    patterns = []
    # Check last 3 bars for single-bar patterns
    for i in range(max(0, n - 3), n):
        idx = n - 1 - i  # 0 = most recent

        val = detect_doji(o[i], h[i], l[i], c[i])
        if val != 0:
            patterns.append(DetectedPattern("DOJI", idx, val, "bullish" if val > 0 else "bearish"))

        val = detect_hammer(o[i], h[i], l[i], c[i])
        if val != 0:
            patterns.append(DetectedPattern("HAMMER", idx, val, "bullish"))

        val = detect_shooting_star(o[i], h[i], l[i], c[i])
        if val != 0:
            patterns.append(DetectedPattern("SHOOTING_STAR", idx, val, "bearish"))

        val = detect_pin_bar(o[i], h[i], l[i], c[i])
        if val != 0:
            patterns.append(DetectedPattern("PIN_BAR", idx, val, "bullish" if val > 0 else "bearish"))

        val = detect_marubozu(o[i], h[i], l[i], c[i])
        if val != 0:
            patterns.append(DetectedPattern("MARUBOZU", idx, val, "bullish" if val > 0 else "bearish"))

        if i >= 1:
            val = detect_engulfing(o[i - 1], c[i - 1], o[i], c[i])
            if val != 0:
                patterns.append(DetectedPattern("ENGULFING", idx, val, "bullish" if val > 0 else "bearish"))

        if i >= 2:
            val = detect_morning_star(
                o[i - 2], h[i - 2], l[i - 2], c[i - 2],
                o[i - 1], h[i - 1], l[i - 1], c[i - 1],
                o[i], h[i], l[i], c[i],
            )
            if val != 0:
                patterns.append(DetectedPattern("MORNING_STAR", idx, val, "bullish"))

            val = detect_evening_star(
                o[i - 2], h[i - 2], l[i - 2], c[i - 2],
                o[i - 1], h[i - 1], l[i - 1], c[i - 1],
                o[i], h[i], l[i], c[i],
            )
            if val != 0:
                patterns.append(DetectedPattern("EVENING_STAR", idx, val, "bearish"))

    # Sort by recency then strength
    patterns.sort(key=lambda p: (p.index, -abs(p.strength)))

    bullish = [p for p in patterns if p.strength > 0]
    bearish = [p for p in patterns if p.strength < 0]

    return CandlestickResult(
        patterns=patterns[:10],
        strongest_bullish=bullish[0].name if bullish else "",
        strongest_bearish=bearish[0].name if bearish else "",
        total_patterns=len(patterns),
    )
