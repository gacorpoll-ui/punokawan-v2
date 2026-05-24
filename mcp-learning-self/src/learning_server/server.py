"""mcp-learning-self — Learning & Adaptation MCP Server.

Provides 5 tools:
  - evaluate_trade_history: Performance metrics from trade history
  - update_trader_profile: Adjust risk/trading parameters
  - run_parameter_optimization: Grid/Bayesian param optimization
  - log_trading_journal: Persist trade evaluations (SQLite + ChromaDB)
  - check_avoidance_database: Vector similarity search to avoid losing patterns
"""

import argparse
import json

from mcp.server.fastmcp import FastMCP

from .avoidance_db import check_avoidance_database
from .journal_manager import log_trading_journal
from .performance_metrics import evaluate_trade_history
from .profile_optimizer import (
    load_profiles,
    run_parameter_optimization,
    update_trader_profile,
)

mcp = FastMCP("learning-self")


@mcp.tool()
def tool_evaluate_trade_history(
    symbol: str = "XAUUSD",
    lookback_days: int = 30,
) -> dict:
    """Compute performance metrics from trade history.

    Returns: Win Rate, Profit Factor, Sharpe Ratio, Max Drawdown,
    Expectancy, Streaks, Session/Day breakdown.
    """
    metrics = evaluate_trade_history(symbol=symbol, lookback_days=lookback_days)

    return {
        "symbol": symbol,
        "lookback_days": lookback_days,
        "total_trades": metrics.total_trades,
        "win_rate": metrics.win_rate,
        "profit_factor": metrics.profit_factor,
        "sharpe_ratio": metrics.sharpe_ratio,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "avg_win": metrics.avg_win,
        "avg_loss": metrics.avg_loss,
        "avg_rr": metrics.avg_rr,
        "expectancy": metrics.expectancy,
        "streaks": {
            "consecutive_wins_max": metrics.consecutive_wins_max,
            "consecutive_losses_max": metrics.consecutive_losses_max,
            "current_streak": metrics.current_streak,
        },
        "session_breakdown": [
            {"session": s.session, "trades": s.trades, "win_rate": s.win_rate, "total_pnl": s.total_pnl}
            for s in metrics.session_breakdown
        ],
        "day_breakdown": [
            {"day": d.day, "trades": d.trades, "win_rate": d.win_rate, "total_pnl": d.total_pnl}
            for d in metrics.day_breakdown
        ],
        "error": metrics.error,
    }


@mcp.tool()
def tool_update_trader_profile(
    profile_name: str = "default",
    aggressiveness: float = None,
    risk_percent: float = None,
    max_daily_loss: float = None,
    min_confluence_score: int = None,
    max_open_trades: int = None,
    lot_size_mode: str = None,
    fixed_lot_size: float = None,
    min_rr_ratio: float = None,
    max_sl_points: float = None,
    max_tp_points: float = None,
    session_filter_json: str = "",
) -> dict:
    """Update trader profile parameters.

    Only provided (non-None) parameters are updated.
    Profiles are persisted as JSON at D:\\Punokawan V2\\data\\trader_profiles.json
    """
    session_filter = None
    if session_filter_json:
        try:
            session_filter = json.loads(session_filter_json)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON for session_filter"}

    profile = update_trader_profile(
        profile_name=profile_name,
        aggressiveness=aggressiveness,
        risk_percent=risk_percent,
        max_daily_loss=max_daily_loss,
        min_confluence_score=min_confluence_score,
        max_open_trades=max_open_trades,
        lot_size_mode=lot_size_mode,
        fixed_lot_size=fixed_lot_size,
        min_rr_ratio=min_rr_ratio,
        max_sl_points=max_sl_points,
        max_tp_points=max_tp_points,
        session_filter=session_filter,
    )

    return {
        "profile": {
            "name": profile.name,
            "aggressiveness": profile.aggressiveness,
            "risk_percent": profile.risk_percent,
            "max_daily_loss": profile.max_daily_loss,
            "min_confluence_score": profile.min_confluence_score,
            "max_open_trades": profile.max_open_trades,
            "lot_size_mode": profile.lot_size_mode,
            "fixed_lot_size": profile.fixed_lot_size,
            "min_rr_ratio": profile.min_rr_ratio,
            "max_sl_points": profile.max_sl_points,
            "max_tp_points": profile.max_tp_points,
            "session_filter": profile.session_filter,
            "updated_at": profile.updated_at,
        }
    }


@mcp.tool()
def tool_run_parameter_optimization(
    symbol: str = "XAUUSD",
    n_trials: int = 50,
    method: str = "grid",
) -> dict:
    """Run parameter optimization for the trading strategy.

    Searches for optimal: min_confluence_score, min_rr_ratio,
    max_sl_points, max_tp_points, risk_percent.

    Args:
        symbol: Trading symbol
        n_trials: Number of optimization trials
        method: "grid" or "bayesian"
    """
    result = run_parameter_optimization(
        symbol=symbol,
        n_trials=n_trials,
        method=method,
    )
    return result


@mcp.tool()
def tool_log_trading_journal(
    ticket_id: str = "",
    symbol: str = "XAUUSD",
    direction: str = "",
    entry: float = 0.0,
    sl: float = 0.0,
    tp: float = 0.0,
    lot_size: float = 0.0,
    score: int = 0,
    confluence_reasons: str = "",
    patterns: str = "",
    session: str = "",
    verdict: str = "",
    notes: str = "",
    indicators_json: str = "",
    smc_json: str = "",
    market_conditions_text: str = "",
    exit_price: float = 0.0,
    pnl: float = 0.0,
) -> dict:
    """Log a trade to the journal (SQLite + ChromaDB).

    Stores trade details and market conditions for future analysis.
    Indexes market conditions in ChromaDB for similarity search.
    """
    result = log_trading_journal(
        ticket_id=ticket_id,
        symbol=symbol,
        direction=direction,
        entry=entry,
        sl=sl,
        tp=tp,
        lot_size=lot_size,
        score=score,
        confluence_reasons=confluence_reasons,
        patterns=patterns,
        session=session,
        verdict=verdict,
        notes=notes,
        indicators_json=indicators_json,
        smc_json=smc_json,
        market_conditions_text=market_conditions_text,
        exit_price=exit_price if exit_price else None,
        pnl=pnl if pnl else None,
    )
    return result


@mcp.tool()
def tool_check_avoidance_database(
    market_conditions_text: str = "",
    chart_image_path: str = "",
    similarity_threshold: float = 0.80,
    lot_reduction_threshold: float = 0.60,
) -> dict:
    """Check if current market conditions match past losing trades.

    Uses vector similarity search (ChromaDB + sentence-transformers).
    If similarity > similarity_threshold (80%): BLOCK trade.
    If similarity > lot_reduction_threshold (60%): HALVE lot size.

    Args:
        market_conditions_text: Text description of current market conditions
        chart_image_path: Path to chart PNG for visual similarity (optional)
        similarity_threshold: Similarity to block (default 0.80)
        lot_reduction_threshold: Similarity to halve lot (default 0.60)

    Returns:
        Blocked status, lot reduction multiplier, similar trades found
    """
    result = check_avoidance_database(
        market_conditions_text=market_conditions_text,
        chart_image_path=chart_image_path,
        similarity_threshold=similarity_threshold,
        lot_reduction_threshold=lot_reduction_threshold,
    )

    return {
        "blocked": result.blocked,
        "lot_reduction": result.lot_reduction,
        "max_similarity": result.max_similarity,
        "similar_trades": [
            {
                "trade_id": t.trade_id,
                "similarity": t.similarity,
                "verdict": t.verdict,
                "pnl": t.pnl,
                "direction": t.direction,
            }
            for t in result.similar_trades
        ],
        "method_used": result.method_used,
        "latency_ms": result.latency_ms,
    }


@mcp.tool()
def tool_get_current_profile(profile_name: str = "default") -> dict:
    """Get the current trader profile parameters."""
    profiles = load_profiles()
    profile = profiles.get(profile_name)

    if not profile:
        return {"error": f"Profile '{profile_name}' not found"}

    return {
        "name": profile.name,
        "aggressiveness": profile.aggressiveness,
        "risk_percent": profile.risk_percent,
        "max_daily_loss": profile.max_daily_loss,
        "min_confluence_score": profile.min_confluence_score,
        "max_open_trades": profile.max_open_trades,
        "lot_size_mode": profile.lot_size_mode,
        "fixed_lot_size": profile.fixed_lot_size,
        "min_rr_ratio": profile.min_rr_ratio,
        "max_sl_points": profile.max_sl_points,
        "max_tp_points": profile.max_tp_points,
        "session_filter": profile.session_filter,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def main():
    parser = argparse.ArgumentParser(description="mcp-learning-self server")
    parser.add_argument("--transport", choices=["sse", "stdio"], default="sse")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8083)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        print(f"[learning-self] Starting on {args.host}:{args.port} (SSE)")
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
