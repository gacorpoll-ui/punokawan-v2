"""mcp-metatrader-ext — Extended MT5 tools for Punokawan V2.

Adds missing tools to the existing metatrader-mcp-server:
  - optimize_lot_size: Kelly Criterion position sizing
  - get_terminal_status: MT5 connectivity & market status
  - get_ohlcv_data_structured: Structured OHLCV (not CSV)
"""

import argparse
import math
import sys
from datetime import datetime
from typing import Optional

# Add the existing server to path
sys.path.insert(0, r"D:\punokawan\metatrader-mcp-server\src")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("metatrader-extended")


def _get_mt5_client():
    """Lazy-import the MT5 client. Uses MT5_PATH from env if set."""
    try:
        import os
        import MetaTrader5 as mt5

        # Read MT5 path from .env (loaded into os.environ by orchestrator)
        mt5_path = os.environ.get("MT5_PATH", "")
        if mt5_path and os.path.exists(mt5_path):
            # Store for later initialize calls
            os.environ["_MT5_PATH_RESOLVED"] = mt5_path

        return mt5
    except ImportError:
        return None


def _init_mt5():
    """Initialize MT5 with custom path if configured."""
    mt5 = _get_mt5_client()
    if mt5 is None:
        return None
    import os
    path = os.environ.get("_MT5_PATH_RESOLVED", "") or os.environ.get("MT5_PATH", "")
    if path and os.path.exists(path):
        if not mt5.terminal_info():
            mt5.initialize(path=path)
    else:
        if not mt5.terminal_info():
            mt5.initialize()
    return mt5


@mcp.tool()
def tool_optimize_lot_size(
    balance: float,
    risk_percent: float = 1.5,
    sl_points: float = 15.0,
    contract_size: float = 100.0,
    tick_value: float = 1.0,
    point: float = 0.01,
    win_rate: float = 0.0,
    avg_win: float = 0.0,
    avg_loss: float = 0.0,
) -> dict:
    """Calculate optimal lot size using Kelly Criterion and fixed-risk methods.

    Kelly Formula: f* = W - (1-W)/R  where R = avg_win/avg_loss
    Half-Kelly is used as the conservative recommendation.

    Args:
        balance: Account balance
        risk_percent: Risk % per trade (default 1.5)
        sl_points: Stop loss distance in points
        contract_size: Contract size per lot (100 for XAUUSD)
        tick_value: Value per tick in account currency
        point: Point size (0.01 for XAUUSD)
        win_rate: Historical win rate (0.0-1.0). If 0, skip Kelly calculation.
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount

    Returns:
        Kelly fraction, half-Kelly lot, fixed-risk lot, and recommendation
    """
    # Fixed-risk lot size
    risk_amount = balance * (risk_percent / 100)
    pip_value_per_lot = contract_size * point  # Value per 1 pip per 1 lot
    fixed_risk_lot = risk_amount / (sl_points * pip_value_per_lot) if sl_points > 0 else 0

    # Kelly Criterion (only if we have historical data)
    kelly_fraction = 0.0
    half_kelly_lot = 0.0
    quarter_kelly_lot = 0.0

    if win_rate > 0 and avg_win > 0 and avg_loss > 0:
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 2.0
        kelly_fraction = win_rate - ((1 - win_rate) / payoff_ratio)
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25% of capital

        kelly_risk_amount = balance * kelly_fraction
        half_kelly_lot = kelly_risk_amount / (2 * sl_points * pip_value_per_lot) if sl_points > 0 else 0
        quarter_kelly_lot = kelly_risk_amount / (4 * sl_points * pip_value_per_lot) if sl_points > 0 else 0

    # Recommendation: use half-Kelly if available, otherwise fixed-risk
    if half_kelly_lot > 0 and half_kelly_lot < fixed_risk_lot:
        recommended_lot = half_kelly_lot
        method = "half_kelly"
    else:
        recommended_lot = fixed_risk_lot
        method = "fixed_risk"

    # Round to 2 decimal places (standard for XAUUSD)
    recommended_lot = max(0.01, round(recommended_lot * 100) / 100)

    return {
        "balance": round(balance, 2),
        "risk_percent": risk_percent,
        "sl_points": sl_points,
        "risk_amount": round(risk_amount, 2),
        "kelly_fraction": round(kelly_fraction, 4),
        "half_kelly_lot": round(half_kelly_lot, 3),
        "quarter_kelly_lot": round(quarter_kelly_lot, 3),
        "fixed_risk_lot": round(fixed_risk_lot, 3),
        "recommended_lot": recommended_lot,
        "method": method,
        "max_risk_amount": round(risk_amount, 2),
        "max_risk_percent": risk_percent,
    }


@mcp.tool()
def tool_get_terminal_status(symbol: str = "XAUUSD") -> dict:
    """Check MT5 terminal connectivity and market status.

    Returns terminal info, connection status, whether market is open,
    and server time. Useful for health checks before trading.
    """
    mt5 = _get_mt5_client()
    if mt5 is None:
        return {"error": "MetaTrader5 package not available"}

    connected = False
    terminal_info = {}
    account_info = {}
    server_time = ""
    market_open = False
    last_error = ""

    try:
        if not mt5.terminal_info():
            last_error = str(mt5.last_error())
            if not mt5.initialize():
                return {
                    "connected": False,
                    "error": f"MT5 not initialized: {mt5.last_error()}",
                    "market_open": False,
                    "trade_allowed": False,
                }

        ti = mt5.terminal_info()
        if ti:
            connected = ti.connected
            terminal_info = {
                "path": ti.path,
                "build": ti.build,
                "name": ti.name,
                "community_account": ti.community_account,
                "community_connection": ti.community_connection,
            }

        ai = mt5.account_info()
        if ai:
            account_info = {
                "login": ai.login,
                "server": ai.server,
                "balance": ai.balance,
                "equity": ai.equity,
                "margin_level": ai.margin_level,
                "trade_allowed": ai.trade_allowed,
                "trade_expert": ai.trade_expert,
            }

        # Check if market is open for the symbol
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info:
            market_open = symbol_info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED

        server_time = datetime.now().isoformat()

    except Exception as e:
        last_error = str(e)

    return {
        "connected": connected,
        "terminal": terminal_info,
        "account": account_info,
        "server_time": server_time,
        "market_open": market_open,
        "trade_allowed": account_info.get("trade_allowed", False),
        "last_error": last_error,
        "symbols_count": 0,  # Would need mt5.symbols_total()
    }


@mcp.tool()
def tool_lot_fix(
    lot_size: float,
    symbol: str = "XAUUSD",
) -> dict:
    """Fix lot size to comply with MT5 broker symbol constraints.

    Validates and corrects: min lot, max lot, lot step rounding.
    Uses live MT5 symbol info for the constraints.

    Args:
        lot_size: Raw/desired lot size (e.g., 0.123 → fixed to 0.12)
        symbol: Trading symbol

    Returns:
        Fixed lot size with constraint details
    """
    mt5 = _get_mt5_client()
    if mt5 is None:
        # Fallback: use default XAUUSD constraints
        return _lot_fix_fallback(lot_size)

    try:
        if not mt5.terminal_info():
            mt5.initialize()

        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)

        if info is None:
            return _lot_fix_fallback(lot_size)

        vol_min = float(info.volume_min)
        vol_max = float(info.volume_max)
        vol_step = float(info.volume_step)
        contract_size = float(info.trade_contract_size)
        tick_value = float(info.trade_tick_value)
        tick_size = float(info.trade_tick_size)
        point = float(info.point)
        digits = int(info.digits)

    except Exception:
        return _lot_fix_fallback(lot_size)

    raw = lot_size

    # Calculate decimal places from vol_step
    step_str = f"{vol_step:.10f}".rstrip('0')
    if '.' in step_str:
        step_decimals = len(step_str.split('.')[1])
    else:
        step_decimals = 0

    # Round to nearest valid step
    if vol_step > 0:
        steps = round(raw / vol_step)
        fixed = round(steps * vol_step, step_decimals)
    else:
        fixed = raw

    # Clamp to min/max
    fixed = max(vol_min, min(vol_max, fixed))

    # Final rounding to step precision
    fixed = round(fixed, step_decimals)

    warnings = []
    if abs(raw - fixed) > 0.0001:
        if raw < vol_min:
            warnings.append(f"Increased from {raw} to min {vol_min}")
        elif raw > vol_max:
            warnings.append(f"Reduced from {raw} to max {vol_max}")
        else:
            warnings.append(f"Rounded from {raw} to nearest step {vol_step}")

    return {
        "symbol": symbol,
        "raw_lot": raw,
        "fixed_lot": max(vol_min, round(fixed, 2)),
        "warnings": warnings,
        "constraints": {
            "vol_min": vol_min,
            "vol_max": vol_max,
            "vol_step": vol_step,
            "contract_size": contract_size,
            "tick_value": round(tick_value, 4),
            "point": point,
            "digits": digits,
            "pip_value_per_lot": round(contract_size * point, 2),
        },
    }


def _lot_fix_fallback(lot_size: float) -> dict:
    """Fallback lot fix with hardcoded XAUUSD constraints."""
    vol_min, vol_max, vol_step = 0.01, 200.0, 0.01
    raw = lot_size
    steps = round(raw / vol_step)
    fixed = steps * vol_step
    fixed = max(vol_min, min(vol_max, fixed))
    fixed = round(fixed, 2)
    return {
        "symbol": "XAUUSD",
        "raw_lot": raw,
        "fixed_lot": fixed,
        "warnings": [f"Rounded from {raw} to step {vol_step}"] if raw != fixed else [],
        "constraints": {
            "vol_min": vol_min, "vol_max": vol_max, "vol_step": vol_step,
            "contract_size": 100.0, "tick_value": 1.0, "point": 0.01, "digits": 2,
            "pip_value_per_lot": 1.0,
        },
    }


@mcp.tool()
def tool_get_symbol_info(symbol: str = "XAUUSD") -> dict:
    """Get complete MT5 symbol specification.

    Returns all trading constraints: lot limits, contract size,
    tick value, spread, swap rates, margin requirements.
    """
    mt5 = _get_mt5_client()
    if mt5 is None:
        return {"error": "MetaTrader5 package not available"}

    try:
        if not mt5.terminal_info():
            mt5.initialize()

        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)

        if info is None:
            return {"error": f"Symbol {symbol} not found"}

        return {
            "symbol": info.name,
            "description": info.description,
            "digits": info.digits,
            "point": info.point,
            "spread": info.spread,
            "spread_float": info.spread_float,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "volume_limit": info.volume_limit,
            "contract_size": info.trade_contract_size,
            "tick_value": info.trade_tick_value,
            "tick_size": info.trade_tick_size,
            "swap_long": info.swap_long,
            "swap_short": info.swap_short,
            "margin_initial": info.margin_initial,
            "margin_maintenance": info.margin_maintenance,
            "trade_mode": info.trade_mode,
            "trade_calc_mode": info.trade_calc_mode,
            "trade_allowed": bool(info.trade_mode != 0),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def tool_get_ohlcv_data(
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
    count: int = 100,
    from_date: str = "",
    to_date: str = "",
) -> dict:
    """Fetch OHLCV data from MT5 as structured JSON (not CSV).

    Args:
        symbol: Trading symbol
        timeframe: MT5 timeframe (M1, M5, M15, M30, H1, H4, D1, W1)
        count: Number of bars
        from_date: Start date ISO format (optional, overrides count)
        to_date: End date ISO format (optional)

    Returns:
        Structured OHLCV bars with metadata
    """
    mt5 = _get_mt5_client()
    if mt5 is None:
        return {"error": "MetaTrader5 package not available"}

    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    mt5_tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)

    try:
        if not mt5.terminal_info():
            if not mt5.initialize():
                return {"error": f"MT5 init failed: {mt5.last_error()}"}

        mt5.symbol_select(symbol, True)

        if from_date and to_date:
            utc_from = datetime.fromisoformat(from_date)
            utc_to = datetime.fromisoformat(to_date)
            rates = mt5.copy_rates_range(symbol, mt5_tf, utc_from, utc_to)
        else:
            rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)

        if rates is None or len(rates) == 0:
            return {"error": f"No data: {mt5.last_error()}"}

        bars = []
        for r in rates:
            bars.append({
                "time": datetime.fromtimestamp(r["time"]).isoformat(),
                "open": round(float(r["open"]), 2),
                "high": round(float(r["high"]), 2),
                "low": round(float(r["low"]), 2),
                "close": round(float(r["close"]), 2),
                "tick_volume": int(r["tick_volume"]),
                "spread": int(r["spread"]),
            })

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(bars),
            "from_time": bars[0]["time"] if bars else "",
            "to_time": bars[-1]["time"] if bars else "",
            "bars": bars,
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="mcp-metatrader-ext server")
    parser.add_argument("--transport", choices=["sse", "stdio"], default="sse")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        print(f"[metatrader-ext] Starting on {args.host}:{args.port} (SSE)")
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
