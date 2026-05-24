"""Single-call risk status aggregator."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .drawdown_guard import DrawdownResult, check_drawdown_limit
from .slippage_checker import SlippageResult, evaluate_slippage_and_latency
from .news_blackout import NewsBlackoutResult, check_news_blackout


@dataclass
class RiskSummary:
    timestamp: str
    overall_allowed: bool
    daily_drawdown: dict
    open_positions: int
    total_exposure_pct: float
    margin_level: float
    spread_status: str
    blackout_status: str
    kill_switch: bool
    warnings: list = field(default_factory=list)


def get_risk_status_summary(
    # Drawdown inputs
    today_realized_pnl: float = 0.0,
    today_floating_pnl: float = 0.0,
    open_positions_count: int = 0,
    daily_loss_limit: float = 100.0,
    balance: float = 0.0,
    # Slippage inputs
    symbol: str = "XAUUSD",
    bid: float = 0.0,
    ask: float = 0.0,
    point: float = 0.01,
    max_spread_pips: float = 3.0,
    max_latency_ms: float = 500.0,
    measured_latency_ms: float = 0.0,
    # Risk inputs
    equity: float = 0.0,
    margin_level: float = 0.0,
    total_exposure: float = 0.0,
    # News inputs
    events: list = None,
    blackout_minutes: int = 30,
) -> RiskSummary:
    """Aggregate all risk checks into a single summary.

    This is the primary tool for the AI orchestrator — one call gives
    a complete risk picture before any trade decision.
    """
    if events is None:
        events = []

    drawdown = check_drawdown_limit(
        today_realized_pnl=today_realized_pnl,
        today_floating_pnl=today_floating_pnl,
        open_positions_count=open_positions_count,
        daily_loss_limit=daily_loss_limit,
        balance=balance,
    )

    slippage = evaluate_slippage_and_latency(
        symbol=symbol,
        bid=bid,
        ask=ask,
        point=point,
        max_spread_pips=max_spread_pips,
        max_latency_ms=max_latency_ms,
        measured_latency_ms=measured_latency_ms,
    )

    news = check_news_blackout(
        events=events,
        blackout_minutes=blackout_minutes,
    )

    total_exposure_pct = (total_exposure / equity * 100) if equity > 0 else 0

    warnings = []
    if slippage.recommendation == "CAUTION":
        warnings.append(f"Spread {slippage.spread_pips} pips — elevated")
    if slippage.recommendation == "BLOCKED":
        warnings.append(f"Spread {slippage.spread_pips} pips — CRITICAL")
    if drawdown.remaining_buffer < daily_loss_limit * 0.3:
        warnings.append(f"Approaching daily loss limit — buffer: {drawdown.remaining_buffer:.1f}")
    if news.blackout_active:
        warnings.append(f"News blackout active — {len(news.events_in_blackout)} event(s) in window")

    overall_allowed = (
        not drawdown.blocked
        and not slippage.blocked
        and not news.blocked
    )

    return RiskSummary(
        timestamp=datetime.now(timezone.utc).isoformat(),
        overall_allowed=overall_allowed,
        daily_drawdown={
            "today_realized_pnl": drawdown.today_realized_pnl,
            "today_floating_pnl": drawdown.today_floating_pnl,
            "today_total_pnl": drawdown.today_total_pnl,
            "daily_loss_limit": drawdown.daily_loss_limit,
            "remaining_buffer": drawdown.remaining_buffer,
            "blocked": drawdown.blocked,
        },
        open_positions=open_positions_count,
        total_exposure_pct=round(total_exposure_pct, 2),
        margin_level=round(margin_level, 2),
        spread_status=slippage.recommendation,
        blackout_status="BLACKOUT" if news.blocked else "CLEAR",
        kill_switch=drawdown.kill_switch_active,
        warnings=warnings,
    )
