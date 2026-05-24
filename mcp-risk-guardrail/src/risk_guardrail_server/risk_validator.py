"""Trade risk validation — pure mathematical checks."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RiskValidationResult:
    passed: bool
    risk_amount: float
    risk_percent: float
    max_recommended_lot: Optional[float] = None
    failure_reasons: list = field(default_factory=list)
    checks: dict = field(default_factory=dict)


def validate_trade_risk(
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
) -> RiskValidationResult:
    """Validate a trade proposal against hard risk limits.

    All checks are mathematical — no external calls, no LLM.
    """
    direction = direction.upper()
    sl_points = abs(entry - sl)
    tp_points = abs(tp - entry)
    risk_amount = lot_size * contract_size * sl_points * point_value
    risk_pct = (risk_amount / equity) * 100 if equity > 0 else float("inf")

    rr_ratio = tp_points / sl_points if sl_points > 0 else 0

    checks = {
        "direction_valid": direction in ("BUY", "SELL"),
        "lot_positive": lot_size > 0,
        "sl_below_entry": sl < entry if direction == "BUY" else sl > entry,
        "tp_above_entry": tp > entry if direction == "BUY" else tp < entry,
        "min_sl_distance": sl_points >= min_sl_points,
        "max_sl_distance": sl_points <= max_sl_points,
        "positive_balance": balance > 0,
        "positive_equity": equity > 0,
        "margin_level_safe": margin_level >= 100.0,
        "max_risk_per_trade": risk_pct <= max_risk_pct,
        "min_rr_ratio": rr_ratio >= 1.2,
    }

    failures = []
    if not checks["direction_valid"]:
        failures.append(f"Invalid direction: {direction}")
    if not checks["lot_positive"]:
        failures.append(f"Lot size must be positive, got {lot_size}")
    if not checks["sl_below_entry"]:
        failures.append(f"SL ({sl}) must be below entry ({entry}) for BUY")
    if not checks["tp_above_entry"]:
        failures.append(f"TP ({tp}) must be above entry ({entry}) for BUY")
    if not checks["min_sl_distance"]:
        failures.append(f"SL distance ({sl_points:.1f} pts) below minimum ({min_sl_points} pts)")
    if not checks["max_sl_distance"]:
        failures.append(f"SL distance ({sl_points:.1f} pts) exceeds maximum ({max_sl_points} pts)")
    if not checks["max_risk_per_trade"]:
        failures.append(f"Risk {risk_pct:.2f}% exceeds max {max_risk_pct}%")
    if not checks["min_rr_ratio"]:
        failures.append(f"R:R ratio ({rr_ratio:.1f}) below minimum 1.2")
    if not checks["margin_level_safe"]:
        failures.append(f"Margin level ({margin_level:.0f}%) is unsafe")

    passed = all(checks.values())

    max_lot = None
    if not checks["max_risk_per_trade"] and equity > 0 and sl_points > 0:
        max_lot = (equity * max_risk_pct / 100) / (contract_size * sl_points * point_value)

    return RiskValidationResult(
        passed=passed,
        risk_amount=round(risk_amount, 2),
        risk_percent=round(risk_pct, 2),
        max_recommended_lot=round(max_lot, 3) if max_lot else None,
        failure_reasons=failures,
        checks=checks,
    )
