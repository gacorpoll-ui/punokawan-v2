"""Daily loss limit enforcement with emergency kill switch."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone


KILL_SWITCH_PATH = r"D:\Punokawan V2\kill_switch.flag"
RESET_PATH = r"D:\Punokawan V2\kill_switch_reset.flag"


@dataclass
class DrawdownResult:
    kill_switch_active: bool
    today_realized_pnl: float
    today_floating_pnl: float
    today_total_pnl: float
    daily_loss_limit: float
    remaining_buffer: float
    positions_affected: int
    blocked: bool


def _read_kill_switch() -> bool:
    return os.path.exists(KILL_SWITCH_PATH)


def _set_kill_switch(reason: str) -> None:
    with open(KILL_SWITCH_PATH, "w") as f:
        f.write(f"KILL SWITCH ACTIVATED: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Reason: {reason}\n")


def _clear_kill_switch() -> None:
    if os.path.exists(KILL_SWITCH_PATH):
        os.remove(KILL_SWITCH_PATH)


def check_drawdown_limit(
    today_realized_pnl: float = 0.0,
    today_floating_pnl: float = 0.0,
    open_positions_count: int = 0,
    daily_loss_limit: float = 100.0,
    balance: float = 0.0,
) -> DrawdownResult:
    """Check if daily loss limit is breached. Activates kill switch if exceeded.

    This function is called before every trade entry and during active position
    monitoring. If today's total PnL exceeds the daily loss limit, a kill switch
    file is created that blocks all new entries.
    """
    today_total_pnl = today_realized_pnl + today_floating_pnl
    remaining_buffer = daily_loss_limit + today_total_pnl  # today_total_pnl is negative for losses

    kill_switch = _read_kill_switch()

    # Check for manual reset request
    if kill_switch and os.path.exists(RESET_PATH):
        _clear_kill_switch()
        os.remove(RESET_PATH)
        kill_switch = False

    blocked = kill_switch or today_total_pnl <= -daily_loss_limit

    if blocked and not kill_switch:
        _set_kill_switch(
            f"Daily loss limit {daily_loss_limit} breached. Total PnL today: {today_total_pnl:.2f}"
        )
        kill_switch = True

    return DrawdownResult(
        kill_switch_active=kill_switch,
        today_realized_pnl=round(today_realized_pnl, 2),
        today_floating_pnl=round(today_floating_pnl, 2),
        today_total_pnl=round(today_total_pnl, 2),
        daily_loss_limit=daily_loss_limit,
        remaining_buffer=round(remaining_buffer, 2),
        positions_affected=open_positions_count,
        blocked=blocked,
    )
