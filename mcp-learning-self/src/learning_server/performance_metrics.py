"""Performance metrics computation from trade history."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from .db import get_sqlite_connection


@dataclass
class SessionStats:
    session: str
    trades: int
    wins: int
    win_rate: float
    total_pnl: float


@dataclass
class DayStats:
    day: str
    trades: int
    wins: int
    win_rate: float
    total_pnl: float


@dataclass
class PerformanceMetrics:
    total_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float
    avg_rr: float
    expectancy: float
    consecutive_wins_max: int
    consecutive_losses_max: int
    current_streak: str
    session_breakdown: list = field(default_factory=list)
    day_breakdown: list = field(default_factory=list)
    error: str = ""


def evaluate_trade_history(
    symbol: str = "XAUUSD",
    lookback_days: int = 30,
    trades_override: list = None,
) -> PerformanceMetrics:
    """Compute performance metrics from trade history.

    Args:
        symbol: Filter by symbol
        lookback_days: Days of history to analyze
        trades_override: Pass a list of trade dicts directly (bypasses SQLite)

    Returns:
        PerformanceMetrics with all computed values
    """
    if trades_override:
        trades = trades_override
    else:
        conn = get_sqlite_connection()
        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        cursor = conn.execute(
            "SELECT * FROM trades WHERE symbol=? AND created_at >= ? AND exit_price IS NOT NULL ORDER BY created_at",
            (symbol, cutoff),
        )
        columns = [desc[0] for desc in cursor.description]
        trades = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

    if not trades:
        return PerformanceMetrics(
            total_trades=0, win_rate=0, profit_factor=0, sharpe_ratio=0,
            max_drawdown_pct=0, avg_win=0, avg_loss=0, avg_rr=0,
            expectancy=0, consecutive_wins_max=0, consecutive_losses_max=0,
            current_streak="NONE",
        )

    pnls = [t.get("pnl", 0) or 0 for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total = len(pnls)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / total if total > 0 else 0

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    avg_win = gross_profit / win_count if win_count > 0 else 0
    avg_loss = -(gross_loss / loss_count) if loss_count > 0 else 0
    avg_rr = avg_win / abs(avg_loss) if avg_loss != 0 else 0

    expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))

    # Sharpe ratio
    if len(pnls) > 1:
        avg_pnl = np.mean(pnls)
        std_pnl = np.std(pnls, ddof=1)
        sharpe = (avg_pnl / std_pnl) * np.sqrt(len(pnls)) if std_pnl > 0 else 0
    else:
        sharpe = 0

    # Max drawdown from cumulative PnL
    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdowns = peak - cumulative
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0
    max_dd_pct = (max_dd / (abs(cumulative[0]) + 1000)) * 100 if len(cumulative) > 0 else 0

    # Streaks
    consecutive_wins = 0
    consecutive_losses = 0
    max_cw = 0
    max_cl = 0
    current_streak_type = "NONE"
    for p in pnls:
        if p > 0:
            consecutive_wins += 1
            consecutive_losses = 0
            current_streak_type = "WIN"
        else:
            consecutive_losses += 1
            consecutive_wins = 0
            current_streak_type = "LOSS"
        max_cw = max(max_cw, consecutive_wins)
        max_cl = max(max_cl, consecutive_losses)

    # Session breakdown
    sessions = {}
    for t in trades:
        session = t.get("session", "UNKNOWN")
        pnl = t.get("pnl", 0) or 0
        if session not in sessions:
            sessions[session] = {"trades": 0, "wins": 0, "total_pnl": 0}
        sessions[session]["trades"] += 1
        if pnl > 0:
            sessions[session]["wins"] += 1
        sessions[session]["total_pnl"] += pnl

    session_breakdown = [
        SessionStats(
            session=s,
            trades=d["trades"],
            wins=d["wins"],
            win_rate=round(d["wins"] / d["trades"], 3) if d["trades"] > 0 else 0,
            total_pnl=round(d["total_pnl"], 2),
        )
        for s, d in sessions.items()
    ]

    # Day of week breakdown
    days = {}
    for t in trades:
        day = t.get("day_of_week", "UNKNOWN")
        pnl = t.get("pnl", 0) or 0
        if day not in days:
            days[day] = {"trades": 0, "wins": 0, "total_pnl": 0}
        days[day]["trades"] += 1
        if pnl > 0:
            days[day]["wins"] += 1
        days[day]["total_pnl"] += pnl

    day_breakdown = [
        DayStats(
            day=d,
            trades=dd["trades"],
            wins=dd["wins"],
            win_rate=round(dd["wins"] / dd["trades"], 3) if dd["trades"] > 0 else 0,
            total_pnl=round(dd["total_pnl"], 2),
        )
        for d, dd in days.items()
    ]

    return PerformanceMetrics(
        total_trades=total,
        win_rate=round(win_rate, 3),
        profit_factor=round(profit_factor, 2),
        sharpe_ratio=round(sharpe, 3),
        max_drawdown_pct=round(max_dd_pct, 2),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        avg_rr=round(avg_rr, 2),
        expectancy=round(expectancy, 2),
        consecutive_wins_max=max_cw,
        consecutive_losses_max=max_cl,
        current_streak=current_streak_type,
        session_breakdown=session_breakdown,
        day_breakdown=day_breakdown,
    )
