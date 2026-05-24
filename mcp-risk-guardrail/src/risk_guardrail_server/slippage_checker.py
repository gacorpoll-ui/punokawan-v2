"""Spread and latency evaluation for trade execution safety."""

import time
from dataclasses import dataclass


@dataclass
class SlippageResult:
    symbol: str
    bid: float
    ask: float
    spread_pips: float
    spread_ok: bool
    avg_latency_ms: float
    latency_ok: bool
    blocked: bool
    recommendation: str  # "OK", "CAUTION", "BLOCKED"


def evaluate_slippage_and_latency(
    symbol: str = "XAUUSD",
    bid: float = 0.0,
    ask: float = 0.0,
    point: float = 0.01,
    max_spread_pips: float = 3.0,
    max_latency_ms: float = 500.0,
    measured_latency_ms: float = 0.0,
) -> SlippageResult:
    """Evaluate current market conditions for trade entry safety.

    High spread → skip entry (not convert to limit order).
    High latency → skip entry (cannot reliably manage risk).
    """
    spread_pips = (ask - bid) / point if point > 0 else 0
    spread_ok = spread_pips <= max_spread_pips
    latency_ok = measured_latency_ms <= max_latency_ms

    if spread_pips > max_spread_pips * 1.5 or measured_latency_ms > max_latency_ms * 2:
        blocked = True
        recommendation = "BLOCKED"
    elif spread_pips > max_spread_pips or measured_latency_ms > max_latency_ms:
        blocked = False
        recommendation = "CAUTION"
    else:
        blocked = False
        recommendation = "OK"

    return SlippageResult(
        symbol=symbol,
        bid=round(bid, 2),
        ask=round(ask, 2),
        spread_pips=round(spread_pips, 1),
        spread_ok=spread_ok,
        avg_latency_ms=round(measured_latency_ms, 1),
        latency_ok=latency_ok,
        blocked=blocked,
        recommendation=recommendation,
    )
