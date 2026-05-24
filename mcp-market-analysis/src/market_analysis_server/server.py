"""mcp-market-analysis — Native Technical Analysis MCP Server.

All analysis runs locally using pure Python — zero scraping.
Provides 6 tools:
  - get_technical_indicators: Multi-timeframe indicators with divergence detection
  - detect_candlestick_patterns: Pure Python pattern recognition
  - detect_smc_levels: Algorithmic SMC from OHLCV data
  - generate_chart_image: mplfinance chart rendering
  - run_backtest: Local vectorized backtesting
  - check_economic_calendar: Forex Factory news events
"""

import argparse
import json
import os
from datetime import datetime

import pandas as pd
from mcp.server.fastmcp import FastMCP

from .backtest_engine import run_backtest
from .candlestick import detect_all_patterns, CandlestickResult
from .chart_generator import generate_chart_image
from .data_provider import fetch_ohlcv_from_mt5, bars_to_dataframe
from .economic_calendar import check_economic_calendar
from .indicators import compute_indicators
from .smc_detector import detect_smc_levels

mcp = FastMCP("market-analysis")


def _get_data(symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame:
    """Helper to fetch and convert data."""
    result = fetch_ohlcv_from_mt5(symbol=symbol, timeframe=timeframe, count=count)
    if result.error:
        raise ValueError(result.error)
    return bars_to_dataframe(result)


@mcp.tool()
def tool_get_technical_indicators(
    symbol: str = "XAUUSD",
    timeframes: str = '["M15","H1","H4","D1"]',
    indicators: str = '["EMA9","EMA21","EMA50","RSI14","MACD","ATR14","BB"]',
    count: int = 100,
) -> dict:
    """Compute technical indicators across multiple timeframes.

    Args:
        symbol: Trading symbol
        timeframes: JSON array of timeframe strings
        indicators: JSON array of indicator names to compute
        count: Number of bars to fetch per timeframe

    Returns:
        Per-timeframe indicator values, divergence detection results
    """
    try:
        tf_list = json.loads(timeframes) if isinstance(timeframes, str) else timeframes
        ind_list = json.loads(indicators) if isinstance(indicators, str) else indicators
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in timeframes or indicators parameter"}

    results = []
    for tf in tf_list:
        try:
            result = fetch_ohlcv_from_mt5(symbol=symbol, timeframe=tf, count=count)
            if result.error:
                results.append({"timeframe": tf, "error": result.error})
                continue

            df = bars_to_dataframe(result)
            snapshots = compute_indicators(df, [tf], selected=ind_list)

            for snap in snapshots:
                div_info = None
                if snap.divergence and snap.divergence.detected:
                    div_info = {
                        "type": snap.divergence.type,
                        "price_bar": snap.divergence.price_point,
                        "rsi_bar": snap.divergence.rsi_point,
                    }

                results.append({
                    "timeframe": snap.timeframe,
                    "last_close": snap.last_close,
                    "timestamp": snap.timestamp,
                    "indicators": snap.indicators,
                    "divergence": div_info,
                })
        except Exception as e:
            results.append({"timeframe": tf, "error": str(e)})

    return {"symbol": symbol, "results": results, "count": len(results)}


@mcp.tool()
def tool_detect_candlestick_patterns(
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
    count: int = 50,
) -> dict:
    """Detect candlestick patterns from OHLCV data.

    Patterns detected: Doji, Hammer, Shooting Star, Engulfing,
    Pin Bar, Marubozu, Morning Star, Evening Star.

    Returns the strongest bullish and bearish patterns on recent bars.
    """
    try:
        result = fetch_ohlcv_from_mt5(symbol=symbol, timeframe=timeframe, count=count)
        if result.error:
            return {"error": result.error}

        df = bars_to_dataframe(result)
        patterns = detect_all_patterns(
            df["open"].values,
            df["high"].values,
            df["low"].values,
            df["close"].values,
        )

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_patterns": patterns.total_patterns,
            "strongest_bullish": patterns.strongest_bullish,
            "strongest_bearish": patterns.strongest_bearish,
            "patterns": [
                {
                    "name": p.name,
                    "index": p.index,
                    "strength": p.strength,
                    "direction": p.direction,
                }
                for p in patterns.patterns[:8]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def tool_detect_smc_levels(
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
    count: int = 200,
    window: int = 5,
) -> dict:
    """Detect Smart Money Concepts levels algorithmically from OHLCV data.

    Returns: Order Blocks, Fair Value Gaps, PDH/PDL, Swing High/Low,
    Liquidity Sweeps, BOS levels, CHoCH status, and Market Bias.

    No TradingView dependency. Pure algorithmic detection.
    """
    try:
        result = fetch_ohlcv_from_mt5(symbol=symbol, timeframe=timeframe, count=count)
        if result.error:
            return {"error": result.error}

        df = bars_to_dataframe(result)
        smc = detect_smc_levels(df, window=window)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_bias": smc.current_bias,
            "choch_detected": smc.choch_detected,
            "bos_levels": [round(b, 2) for b in smc.bos_levels[-5:]],
            "order_blocks": [
                {
                    "type": ob.type,
                    "high": ob.high,
                    "low": ob.low,
                    "index": ob.index,
                    "strength": ob.strength,
                }
                for ob in smc.order_blocks
            ],
            "fair_value_gaps": [
                {
                    "type": fvg.type,
                    "high": round(fvg.high, 2),
                    "low": round(fvg.low, 2),
                    "index": fvg.index,
                }
                for fvg in smc.fair_value_gaps[-6:]
            ],
            "daily_levels": {
                "pdh": smc.daily_levels.pdh,
                "pdl": smc.daily_levels.pdl,
                "pdc": smc.daily_levels.pdc,
            },
            "swing_points": [
                {"type": sp.type, "price": round(sp.price, 2), "index": sp.index}
                for sp in smc.swing_points[-8:]
            ],
            "liquidity_sweeps": [
                {
                    "type": sw.type,
                    "swept_level": round(sw.swept_level, 2),
                    "pip_depth": sw.pip_depth,
                }
                for sw in smc.liquidity_sweeps[-5:]
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def tool_generate_chart_image(
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
    count: int = 100,
    annotations_json: str = "[]",
    show_ema: bool = True,
) -> dict:
    """Generate an annotated OHLCV chart image for AI multimodal analysis.

    Args:
        symbol: Trading symbol
        timeframe: Bar timeframe
        count: Number of candles
        annotations_json: JSON array of annotation objects
            Each: {"type": "hline|zone", "price": float, "price2": float, "label": str, "color": str}
        show_ema: Overlay EMA 9 and EMA 21

    Returns:
        Path to saved PNG image
    """
    try:
        result = fetch_ohlcv_from_mt5(symbol=symbol, timeframe=timeframe, count=count)
        if result.error:
            return {"error": result.error}

        df = bars_to_dataframe(result)
        annotations = json.loads(annotations_json) if isinstance(annotations_json, str) else []

        chart = generate_chart_image(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            count=count,
            annotations=annotations,
            show_ema=show_ema,
        )

        return {
            "image_path": chart.image_path,
            "width": chart.width,
            "height": chart.height,
            "generated_at": chart.generated_at,
            "error": chart.error,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def tool_run_backtest(
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
    count: int = 2000,
    entry_rule: str = "SMC",
    min_score: int = 6,
    sl_points: float = 15.0,
    tp_points: float = 25.0,
    use_trailing_stop: bool = False,
    trailing_trigger: float = 10.0,
) -> dict:
    """Run a backtest on historical OHLCV data.

    Args:
        symbol: Trading symbol
        timeframe: Bar timeframe
        count: Number of bars to fetch
        entry_rule: Strategy type ("SMC", "MA_CROSS", "RSI")
        min_score: Min confluence score for entry
        sl_points: Stop loss in price points
        tp_points: Take profit in price points
        use_trailing_stop: Enable trailing stop
        trailing_trigger: Points before trail activates

    Returns:
        Backtest performance metrics and last 20 trades
    """
    try:
        result = fetch_ohlcv_from_mt5(symbol=symbol, timeframe=timeframe, count=count)
        if result.error:
            return {"error": result.error}

        df = bars_to_dataframe(result)
        bt = run_backtest(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            entry_rule=entry_rule,
            min_score=min_score,
            sl_points=sl_points,
            tp_points=tp_points,
            use_trailing_stop=use_trailing_stop,
            trailing_trigger=trailing_trigger,
        )

        return {
            "symbol": bt.symbol,
            "timeframe": bt.timeframe,
            "period": {"start": bt.period_start, "end": bt.period_end},
            "metrics": {
                "total_trades": bt.total_trades,
                "win_rate": bt.win_rate,
                "profit_factor": bt.profit_factor,
                "net_profit": bt.net_profit,
                "sharpe_ratio": bt.sharpe_ratio,
                "max_drawdown_pct": bt.max_drawdown_pct,
                "avg_win": bt.avg_win,
                "avg_loss": bt.avg_loss,
                "best_trade": bt.best_trade,
                "worst_trade": bt.worst_trade,
            },
            "trade_log": [
                {
                    "entry": t.entry_time,
                    "exit": t.exit_time,
                    "direction": t.direction,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                }
                for t in bt.trade_log
            ],
            "error": bt.error,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def tool_check_economic_calendar(
    currency: str = "USD",
    impact_filter: str = "HIGH",
    window_minutes: int = 60,
) -> dict:
    """Fetch economic calendar and check for high-impact news events.

    Uses Forex Factory (scraping). Isolated module — easily replaced
    if a paid API becomes available.

    Args:
        currency: Currency code to filter (default "USD" for XAUUSD)
        impact_filter: "HIGH", "MEDIUM", "LOW", or "ALL"
        window_minutes: Check window in minutes from now

    Returns:
        Events list, blackout status, next high-impact event
    """
    try:
        cal = check_economic_calendar(
            currency=currency,
            impact_filter=impact_filter,
            window_minutes=window_minutes,
        )

        return {
            "blackout_active": cal.blackout_active,
            "next_high_impact": {
                "name": cal.next_high_impact.name,
                "time": cal.next_high_impact.time,
                "currency": cal.next_high_impact.currency,
                "impact": cal.next_high_impact.impact,
            }
            if cal.next_high_impact
            else None,
            "remaining_minutes": cal.remaining_minutes,
            "events": [
                {"name": e.name, "time": e.time, "currency": e.currency, "impact": e.impact}
                for e in cal.events[:10]
            ],
            "error": cal.error,
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="mcp-market-analysis server")
    parser.add_argument("--transport", choices=["sse", "stdio"], default="sse")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8082)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        print(f"[market-analysis] Starting on {args.host}:{args.port} (SSE)")
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
