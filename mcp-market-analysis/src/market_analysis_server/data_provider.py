"""OHLCV data fetching from MT5 via MCP metatrader server.

This module communicates with the existing mcp-metatrader server
to fetch historical OHLCV data for analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd


@dataclass
class OHLCVBar:
    time: str
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = 0
    spread: int = 0


@dataclass
class OHLCVResult:
    symbol: str
    timeframe: str
    bars: list = field(default_factory=list)
    count: int = 0
    from_time: str = ""
    to_time: str = ""
    error: str = ""


def fetch_ohlcv_from_mt5(
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
    count: int = 100,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> OHLCVResult:
    """Fetch OHLCV data from MetaTrader 5.

    Uses the MetaTrader5 Python package directly. The MT5 terminal
    must be running and logged in.

    Args:
        symbol: Trading symbol (default XAUUSD)
        timeframe: MT5 timeframe string (M1, M5, M15, M30, H1, H4, D1, W1, MN1)
        count: Number of bars to fetch (used if from_date not specified)
        from_date: Start date in ISO format (e.g., "2024-01-01")
        to_date: End date in ISO format

    Returns:
        OHLCVResult with structured bar data
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return OHLCVResult(
            symbol=symbol, timeframe=timeframe,
            error="MetaTrader5 package not installed. Run: pip install MetaTrader5",
        )

    # MT5 timeframe mapping
    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }

    mt5_tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)

    # Try to connect if not already
    if not mt5.terminal_info():
        if not mt5.initialize():
            return OHLCVResult(
                symbol=symbol, timeframe=timeframe,
                error=f"MT5 initialize failed: {mt5.last_error()}",
            )

    # Ensure symbol is in market watch
    mt5.symbol_select(symbol, True)

    if from_date and to_date:
        utc_from = datetime.fromisoformat(from_date)
        utc_to = datetime.fromisoformat(to_date)
        rates = mt5.copy_rates_range(symbol, mt5_tf, utc_from, utc_to)
    else:
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)

    if rates is None or len(rates) == 0:
        return OHLCVResult(
            symbol=symbol, timeframe=timeframe,
            error=f"No data returned: {mt5.last_error()}",
        )

    bars = []
    for r in rates:
        bars.append(OHLCVBar(
            time=datetime.fromtimestamp(r["time"]).isoformat(),
            open=round(float(r["open"]), 2),
            high=round(float(r["high"]), 2),
            low=round(float(r["low"]), 2),
            close=round(float(r["close"]), 2),
            tick_volume=int(r["tick_volume"]),
            spread=int(r["spread"]),
        ))

    return OHLCVResult(
        symbol=symbol,
        timeframe=timeframe,
        bars=bars,
        count=len(bars),
        from_time=bars[0].time if bars else "",
        to_time=bars[-1].time if bars else "",
    )


def bars_to_dataframe(result: OHLCVResult) -> pd.DataFrame:
    """Convert OHLCVResult to a pandas DataFrame for analysis."""
    if not result.bars:
        return pd.DataFrame()

    data = {
        "open": [b.open for b in result.bars],
        "high": [b.high for b in result.bars],
        "low": [b.low for b in result.bars],
        "close": [b.close for b in result.bars],
        "tick_volume": [b.tick_volume for b in result.bars],
    }
    df = pd.DataFrame(data, index=pd.to_datetime([b.time for b in result.bars]))
    return df
