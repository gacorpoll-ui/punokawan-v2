"""Unified MCP client helper for inter-server communication."""

import json
from contextlib import asynccontextmanager

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


class MCPServers:
    """MCP server URLs."""

    MARKET_ANALYSIS = "http://127.0.0.1:8082/sse"
    LEARNING_SELF = "http://127.0.0.1:8083/sse"
    RISK_GUARDRAIL = "http://127.0.0.1:8084/sse"
    METATRADER_EXT = "http://127.0.0.1:8081/sse"
    METATRADER = "http://127.0.0.1:8080/sse"


@asynccontextmanager
async def mcp_call(server_url: str):
    """Async context manager for MCP tool calls."""
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_tool(server_url: str, tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool and return parsed JSON response."""
    async with mcp_call(server_url) as session:
        result = await session.call_tool(tool_name, arguments)
        text = result.content[0].text if result.content else "{}"
        return json.loads(text)


async def collect_all_analysis(symbol: str = "XAUUSD") -> dict:
    """Collect all market analysis data from the MCP servers.

    Returns a comprehensive data dict for the scoring engine.
    """
    data = {"symbol": symbol}

    # 1. Technical indicators (all timeframes)
    data["indicators"] = await call_tool(
        MCPServers.MARKET_ANALYSIS,
        "tool_get_technical_indicators",
        {
            "symbol": symbol,
            "timeframes": '["M15","H1","H4","D1"]',
            "count": 100,
        },
    )

    # 2. SMC levels (H1)
    data["smc"] = await call_tool(
        MCPServers.MARKET_ANALYSIS,
        "tool_detect_smc_levels",
        {"symbol": symbol, "timeframe": "H1", "count": 200},
    )

    # 3. Candlestick patterns (M15 + H1)
    data["patterns"] = {}
    for tf in ["M15", "H1"]:
        data["patterns"][tf] = await call_tool(
            MCPServers.MARKET_ANALYSIS,
            "tool_detect_candlestick_patterns",
            {"symbol": symbol, "timeframe": tf, "count": 50},
        )

    return data


async def collect_risk_data(
    symbol: str = "XAUUSD",
    balance: float = 10000.0,
    equity: float = 10000.0,
    margin_level: float = 200.0,
    bid: float = 0.0,
    ask: float = 0.0,
    point: float = 0.01,
) -> dict:
    """Collect risk assessment from the risk guardrail server."""
    return await call_tool(
        MCPServers.RISK_GUARDRAIL,
        "tool_get_risk_status_summary",
        {
            "symbol": symbol,
            "balance": balance,
            "equity": equity,
            "margin_level": margin_level,
            "bid": bid,
            "ask": ask,
            "point": point,
            "max_spread_pips": 3.0,
            "daily_loss_limit": 100.0,
        },
    )


async def check_avoidance(market_conditions_text: str) -> dict:
    """Check avoidance database for similar losing patterns."""
    return await call_tool(
        MCPServers.LEARNING_SELF,
        "tool_check_avoidance_database",
        {
            "market_conditions_text": market_conditions_text,
            "similarity_threshold": 0.80,
            "lot_reduction_threshold": 0.60,
        },
    )


async def get_lot_size(balance: float, sl_points: float) -> dict:
    """Get optimized lot size recommendation."""
    return await call_tool(
        MCPServers.METATRADER_EXT,
        "tool_optimize_lot_size",
        {
            "balance": balance,
            "risk_percent": 1.5,
            "sl_points": sl_points,
        },
    )
