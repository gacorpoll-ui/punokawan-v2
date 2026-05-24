"""Pure numpy/pandas technical indicators — no pandas-ta dependency.

pandas-ta requires numba which doesn't support Python 3.14 yet.
This module implements all needed indicators directly.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class DivergenceResult:
    detected: bool
    type: str  # "bullish", "bearish", "hidden_bullish", "hidden_bearish", "none"
    price_point: int  # bar index
    rsi_point: int


@dataclass
class IndicatorSnapshot:
    timeframe: str
    last_close: float
    timestamp: str
    indicators: dict = field(default_factory=dict)
    divergence: Optional[DivergenceResult] = None


def ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    result = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < period:
        return result
    multiplier = 2 / (period + 1)
    result[period - 1] = np.mean(series[:period])
    for i in range(period, len(series)):
        result[i] = (series[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


def sma(series: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average."""
    result = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < period:
        return result
    cumsum = np.cumsum(np.insert(series, 0, 0))
    result[period - 1:] = (cumsum[period:] - cumsum[:-period]) / period
    return result


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index (Wilder's smoothing)."""
    result = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) < period + 1:
        return result
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, len(close)):
        avg_gain = (avg_gain * (period - 1) + gain[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i - 1]) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))
    return result


def macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, and histogram."""
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range (Wilder's smoothing)."""
    result = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) < period + 1:
        return result

    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ),
    )

    result[period] = np.mean(tr[1:period + 1])
    for i in range(period + 1, len(tr)):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def bollinger_bands(close: np.ndarray, period: int = 20, std_dev: float = 2.0):
    """Bollinger Bands: middle (SMA), upper, lower."""
    middle = sma(close, period)
    # Rolling std
    rolling_std = np.full_like(close, np.nan, dtype=np.float64)
    for i in range(period - 1, len(close)):
        rolling_std[i] = np.std(close[i - period + 1:i + 1], ddof=0)
    upper = middle + std_dev * rolling_std
    lower = middle - std_dev * rolling_std
    return upper, middle, lower


def detect_divergence(close: np.ndarray, rsi_values: np.ndarray, lookback: int = 50) -> DivergenceResult:
    """Detect RSI divergence from price action.

    Bullish: price makes lower low, RSI makes higher low.
    Bearish: price makes higher high, RSI makes lower high.
    """
    if len(close) < lookback or len(rsi_values) < lookback:
        return DivergenceResult(detected=False, type="none", price_point=-1, rsi_point=-1)

    recent_close = close[-lookback:]
    recent_rsi = rsi_values[-lookback:]

    valid = ~np.isnan(recent_close) & ~np.isnan(recent_rsi)
    if valid.sum() < 10:
        return DivergenceResult(detected=False, type="none", price_point=-1, rsi_point=-1)

    price = recent_close[valid]
    rsi_v = recent_rsi[valid]

    # Find local extremes
    half = len(price) // 2
    first_half_p = price[:half]
    second_half_p = price[half:]
    first_half_r = rsi_v[:half]
    second_half_r = rsi_v[half:]

    if len(first_half_p) < 5 or len(second_half_p) < 5:
        return DivergenceResult(detected=False, type="none", price_point=-1, rsi_point=-1)

    p1_low = np.min(first_half_p)
    p2_low = np.min(second_half_p)
    p1_high = np.max(first_half_p)
    p2_high = np.max(second_half_p)

    r1_low = np.min(first_half_r)
    r2_low = np.min(second_half_r)
    r1_high = np.max(first_half_r)
    r2_high = np.max(second_half_r)

    # Bearish divergence: price higher high, RSI lower high
    if p2_high > p1_high and r2_high < r1_high:
        return DivergenceResult(detected=True, type="bearish",
                                price_point=int(np.argmax(second_half_p) + half),
                                rsi_point=int(np.argmax(second_half_r) + half))

    # Bullish divergence: price lower low, RSI higher low
    if p2_low < p1_low and r2_low > r1_low:
        return DivergenceResult(detected=True, type="bullish",
                                price_point=int(np.argmin(second_half_p) + half),
                                rsi_point=int(np.argmin(second_half_r) + half))

    return DivergenceResult(detected=False, type="none", price_point=-1, rsi_point=-1)


def compute_indicators(
    df: pd.DataFrame,
    timeframes: list,
    selected: Optional[list] = None,
) -> list[IndicatorSnapshot]:
    """Compute technical indicators across multiple timeframes.

    Args:
        df: DataFrame with columns [timeframe, open, high, low, close, tick_volume]
        timeframes: List of timeframe labels
        selected: Specific indicators to compute, or None for all defaults

    Returns:
        List of IndicatorSnapshot, one per timeframe
    """
    if selected is None:
        selected = ["EMA9", "EMA21", "EMA50", "RSI14", "MACD", "ATR14", "BB"]

    results = []

    for tf in timeframes:
        tf_data = df[df["timeframe"] == tf] if "timeframe" in df.columns else df
        if tf_data.empty:
            continue

        close = tf_data["close"].values.astype(np.float64)
        high = tf_data["high"].values.astype(np.float64)
        low = tf_data["low"].values.astype(np.float64)
        open_ = tf_data["open"].values.astype(np.float64)

        indicators = {}
        rsi_values = None

        if "EMA9" in selected:
            indicators["ema9"] = round(float(ema(close, 9)[-1]), 2)
        if "EMA21" in selected:
            indicators["ema21"] = round(float(ema(close, 21)[-1]), 2)
        if "EMA50" in selected:
            indicators["ema50"] = round(float(ema(close, 50)[-1]), 2)
        if "RSI14" in selected:
            rsi_values = rsi(close, 14)
            indicators["rsi14"] = round(float(rsi_values[-1]), 2)
        if "MACD" in selected:
            macd_line, signal_line, histogram = macd(close)
            indicators["macd_line"] = round(float(macd_line[-1]), 4)
            indicators["macd_signal"] = round(float(signal_line[-1]), 4)
            indicators["macd_histogram"] = round(float(histogram[-1]), 4)
        if "ATR14" in selected:
            indicators["atr14"] = round(float(atr(high, low, close, 14)[-1]), 2)
        if "BB" in selected:
            upper, middle, lower = bollinger_bands(close)
            bb_position = (close[-1] - lower[-1]) / (upper[-1] - lower[-1]) if upper[-1] != lower[-1] else 0.5
            indicators["bb_upper"] = round(float(upper[-1]), 2)
            indicators["bb_middle"] = round(float(middle[-1]), 2)
            indicators["bb_lower"] = round(float(lower[-1]), 2)
            indicators["bb_position"] = round(float(bb_position), 3)  # 0=at lower, 1=at upper

        # Divergence detection
        divergence = None
        if rsi_values is not None:
            divergence = detect_divergence(close, rsi_values)

        results.append(IndicatorSnapshot(
            timeframe=tf,
            last_close=round(float(close[-1]), 2),
            timestamp=str(tf_data.index[-1]) if hasattr(tf_data.index[-1], 'isoformat') else "",
            indicators=indicators,
            divergence=divergence,
        ))

    return results
