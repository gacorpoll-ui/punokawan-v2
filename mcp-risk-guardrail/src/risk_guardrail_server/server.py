"""mcp-risk-guardrail — Deterministic Risk Validation MCP Server.

100% rule-based. No LLM calls. Every decision is mathematical, consistent,
and low-latency (<50ms target).

Provides 5 tools:
  - validate_trade_risk: Mathematical risk checks (lot, SL, exposure)
  - check_drawdown_limit: Daily loss limit with emergency kill switch
  - evaluate_slippage_and_latency: Spread and latency safety check
  - check_news_blackout: Block entries before high-impact news
  - get_risk_status_summary: Single-call risk overview
"""

import argparse
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .drawdown_guard import check_drawdown_limit
from .news_blackout import check_news_blackout
from .risk_summary import get_risk_status_summary
from .risk_validator import validate_trade_risk
from .slippage_checker import evaluate_slippage_and_latency

mcp = FastMCP("risk-guardrail")


@mcp.tool()
def tool_validate_trade_risk(
    symbol: str,
    direction: str,
    lot_size: float,
    entry: float,
    sl: float,
    tp: float,
    balance: float,
    equity: float,
    margin_level: float,
    contract_size: float = 100.0,
    point_value: float = 1.0,
    max_risk_pct: float = 1.5,
    min_sl_points: float = 2.0,
    max_sl_points: float = 50.0,
) -> dict:
    """Validate a trade proposal against hard risk limits.

    Checks: lot size, SL distance, risk % of equity, margin level, R:R ratio.
    Returns pass/fail with detailed failure reasons and recommended lot size.
    """
    result = validate_trade_risk(
        symbol=symbol,
        direction=direction,
        lot_size=lot_size,
        entry=entry,
        sl=sl,
        tp=tp,
        balance=balance,
        equity=equity,
        margin_level=margin_level,
        contract_size=contract_size,
        point_value=point_value,
        max_risk_pct=max_risk_pct,
        min_sl_points=min_sl_points,
        max_sl_points=max_sl_points,
    )
    return {
        "passed": result.passed,
        "risk_amount": result.risk_amount,
        "risk_percent": result.risk_percent,
        "max_recommended_lot": result.max_recommended_lot,
        "failure_reasons": result.failure_reasons,
        "checks": result.checks,
    }


@mcp.tool()
def tool_check_drawdown_limit(
    today_realized_pnl: float = 0.0,
    today_floating_pnl: float = 0.0,
    open_positions_count: int = 0,
    daily_loss_limit: float = 100.0,
    balance: float = 0.0,
) -> dict:
    """Check if daily loss limit is breached.

    Activates emergency kill switch if today's total PnL exceeds the limit.
    Kill switch persists as a flag file and blocks all new entries.
    """
    result = check_drawdown_limit(
        today_realized_pnl=today_realized_pnl,
        today_floating_pnl=today_floating_pnl,
        open_positions_count=open_positions_count,
        daily_loss_limit=daily_loss_limit,
        balance=balance,
    )
    return {
        "kill_switch_active": result.kill_switch_active,
        "today_realized_pnl": result.today_realized_pnl,
        "today_floating_pnl": result.today_floating_pnl,
        "today_total_pnl": result.today_total_pnl,
        "daily_loss_limit": result.daily_loss_limit,
        "remaining_buffer": result.remaining_buffer,
        "positions_affected": result.positions_affected,
        "blocked": result.blocked,
    }


@mcp.tool()
def tool_evaluate_slippage_and_latency(
    symbol: str = "XAUUSD",
    bid: float = 0.0,
    ask: float = 0.0,
    point: float = 0.01,
    max_spread_pips: float = 3.0,
    max_latency_ms: float = 500.0,
    measured_latency_ms: float = 0.0,
) -> dict:
    """Evaluate bid-ask spread and latency for trade entry safety.

    High spread (>3 pips) → block or caution.
    High latency (>500ms) → block or caution.
    Does NOT auto-convert to limit orders — just skips the entry.
    """
    result = evaluate_slippage_and_latency(
        symbol=symbol,
        bid=bid,
        ask=ask,
        point=point,
        max_spread_pips=max_spread_pips,
        max_latency_ms=max_latency_ms,
        measured_latency_ms=measured_latency_ms,
    )
    return {
        "symbol": result.symbol,
        "bid": result.bid,
        "ask": result.ask,
        "spread_pips": result.spread_pips,
        "spread_ok": result.spread_ok,
        "avg_latency_ms": result.avg_latency_ms,
        "latency_ok": result.latency_ok,
        "blocked": result.blocked,
        "recommendation": result.recommendation,
    }


@mcp.tool()
def tool_check_news_blackout(
    events_json: str = "[]",
    blackout_minutes: int = 30,
) -> dict:
    """Check if current time falls within a news blackout window.

    Receives economic calendar events and checks if any high-impact event
    is within ±blackout_minutes of now. If so, blocks all new entries.

    Args:
        events_json: JSON string of event dicts with keys: name, time, currency, impact
        blackout_minutes: Minutes before/after an event to block trading
    """
    import json

    try:
        events = json.loads(events_json) if isinstance(events_json, str) else events_json
    except (json.JSONDecodeError, TypeError):
        events = []

    result = check_news_blackout(events=events, blackout_minutes=blackout_minutes)
    return {
        "blackout_active": result.blackout_active,
        "blocked": result.blocked,
        "events_in_blackout": [
            {"name": e.name, "time": e.time, "currency": e.currency, "impact": e.impact}
            for e in result.events_in_blackout
        ],
        "next_high_impact_event": {
            "name": result.next_high_impact_event.name,
            "time": result.next_high_impact_event.time,
            "currency": result.next_high_impact_event.currency,
            "impact": result.next_high_impact_event.impact,
        }
        if result.next_high_impact_event
        else None,
        "remaining_minutes": result.remaining_minutes,
    }


@mcp.tool()
def tool_get_risk_status_summary(
    today_realized_pnl: float = 0.0,
    today_floating_pnl: float = 0.0,
    open_positions_count: int = 0,
    daily_loss_limit: float = 100.0,
    balance: float = 0.0,
    equity: float = 0.0,
    margin_level: float = 0.0,
    total_exposure: float = 0.0,
    symbol: str = "XAUUSD",
    bid: float = 0.0,
    ask: float = 0.0,
    point: float = 0.01,
    max_spread_pips: float = 3.0,
    max_latency_ms: float = 500.0,
    measured_latency_ms: float = 0.0,
    events_json: str = "[]",
    blackout_minutes: int = 30,
) -> dict:
    """Get a complete risk status summary in a single call.

    Aggregates: daily drawdown, spread/latency, news blackout, exposure.
    This is the primary risk check before any trade decision.
    """
    import json

    try:
        events = json.loads(events_json) if isinstance(events_json, str) else events_json
    except (json.JSONDecodeError, TypeError):
        events = []

    result = get_risk_status_summary(
        today_realized_pnl=today_realized_pnl,
        today_floating_pnl=today_floating_pnl,
        open_positions_count=open_positions_count,
        daily_loss_limit=daily_loss_limit,
        balance=balance,
        symbol=symbol,
        bid=bid,
        ask=ask,
        point=point,
        max_spread_pips=max_spread_pips,
        max_latency_ms=max_latency_ms,
        measured_latency_ms=measured_latency_ms,
        equity=equity,
        margin_level=margin_level,
        total_exposure=total_exposure,
        events=events,
        blackout_minutes=blackout_minutes,
    )
    return {
        "timestamp": result.timestamp,
        "overall_allowed": result.overall_allowed,
        "daily_drawdown": result.daily_drawdown,
        "open_positions": result.open_positions,
        "total_exposure_pct": result.total_exposure_pct,
        "margin_level": result.margin_level,
        "spread_status": result.spread_status,
        "blackout_status": result.blackout_status,
        "kill_switch": result.kill_switch,
        "warnings": result.warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="mcp-risk-guardrail server")
    parser.add_argument("--transport", choices=["sse", "stdio"], default="sse")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8084)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        print(f"[risk-guardrail] Starting on {args.host}:{args.port} (SSE)")
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
