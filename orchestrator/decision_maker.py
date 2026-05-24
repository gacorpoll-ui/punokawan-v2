"""AI Decision Maker — Final trade approval/rejection logic.

Can operate in two modes:
1. Rule-based (deterministic): Score threshold + risk checks only
2. AI-assisted (optional): Sends analysis to DeepSeek/Claude for final review

The rule-based mode is always active. AI consultation is a bonus layer.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .scoring_engine import MIN_SCORE_TO_TRADE, TradeSetup


@dataclass
class DecisionResult:
    action: str  # "EXECUTE", "SKIP", "BLOCKED"
    direction: str
    entry: float
    sl: float
    tp: float
    lot_size: float
    score: float
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    risk_details: dict = field(default_factory=dict)
    avoidance: dict = field(default_factory=dict)
    ai_opinion: str = ""
    timestamp: str = ""


def rule_based_decision(
    setup: TradeSetup,
    risk_summary: dict,
    avoidance_result: dict,
    trader_profile: dict,
) -> DecisionResult:
    """Make a deterministic trading decision based on rules.

    Decision flow:
    1. Score >= MIN_SCORE_TO_TRADE? → continue
    2. All risk checks pass? → continue
    3. Not blocked by avoidance DB? → continue
    4. R:R meets profile minimum? → EXECUTE
    """
    warnings = list(setup.warnings)

    # Check 1: Minimum score
    if setup.score < MIN_SCORE_TO_TRADE:
        return DecisionResult(
            action="SKIP",
            direction=setup.direction,
            entry=setup.entry,
            sl=setup.sl,
            tp=setup.tp,
            lot_size=0,
            score=setup.score,
            reasons=setup.reasons,
            warnings=warnings + [f"Score {setup.score} < {MIN_SCORE_TO_TRADE} minimum"],
            timestamp=datetime.now().isoformat(),
        )

    # Check 2: Risk guardrail
    if not risk_summary.get("overall_allowed", False):
        risk_warnings = risk_summary.get("warnings", [])
        return DecisionResult(
            action="BLOCKED",
            direction=setup.direction,
            entry=setup.entry,
            sl=setup.sl,
            tp=setup.tp,
            lot_size=0,
            score=setup.score,
            reasons=setup.reasons,
            warnings=warnings + risk_warnings,
            risk_details=risk_summary,
            timestamp=datetime.now().isoformat(),
        )

    # Check 3: Kill switch
    if risk_summary.get("kill_switch", False):
        return DecisionResult(
            action="BLOCKED",
            direction=setup.direction,
            entry=setup.entry,
            sl=setup.sl,
            tp=setup.tp,
            lot_size=0,
            score=setup.score,
            warnings=warnings + ["KILL SWITCH ACTIVE"],
            risk_details=risk_summary,
            timestamp=datetime.now().isoformat(),
        )

    # Check 4: Avoidance database
    if avoidance_result.get("blocked", False):
        similar = avoidance_result.get("similar_trades", [])
        return DecisionResult(
            action="BLOCKED",
            direction=setup.direction,
            entry=setup.entry,
            sl=setup.sl,
            tp=setup.tp,
            lot_size=0,
            score=setup.score,
            warnings=warnings + [f"Pattern matches {len(similar)} losing trades — avoidance block"],
            avoidance=avoidance_result,
            timestamp=datetime.now().isoformat(),
        )

    # Check 5: Lot reduction from avoidance
    lot_multiplier = avoidance_result.get("lot_reduction", 1.0)

    # Check 6: R:R meets profile minimum
    min_rr = trader_profile.get("min_rr_ratio", 1.5)
    if setup.rr_ratio < min_rr:
        return DecisionResult(
            action="SKIP",
            direction=setup.direction,
            entry=setup.entry,
            sl=setup.sl,
            tp=setup.tp,
            lot_size=0,
            score=setup.score,
            warnings=warnings + [f"R:R {setup.rr_ratio} < {min_rr} minimum"],
            timestamp=datetime.now().isoformat(),
        )

    # All checks passed → Calculate lot size
    sl_points = abs(setup.entry - setup.sl)
    risk_pct = trader_profile.get("risk_percent", 1.5)

    # Simple fixed-risk lot calculation (Kelly handled by metatrader-ext)
    lot_size = 0.05  # Default
    if sl_points > 0:
        # 1% risk on $10,000 account with XAUUSD
        risk_amount = 10000 * (risk_pct / 100)
        lot_size = risk_amount / (sl_points * 100 * 0.01)  # 100 units * $0.01 per point
        lot_size = round(lot_size * 100) / 100  # Round to 0.01
        lot_size = max(0.01, min(lot_size, 1.0))  # Clamp

    lot_size *= lot_multiplier
    lot_size = max(0.01, round(lot_size * 100) / 100)

    return DecisionResult(
        action="EXECUTE",
        direction=setup.direction,
        entry=setup.entry,
        sl=setup.sl,
        tp=setup.tp,
        lot_size=lot_size,
        score=setup.score,
        reasons=setup.reasons,
        warnings=warnings,
        risk_details=risk_summary,
        avoidance=avoidance_result,
        timestamp=datetime.now().isoformat(),
    )


def build_ai_prompt(setup: TradeSetup, risk_summary: dict, analysis_data: dict) -> str:
    """Build a prompt for AI trade consultation (DeepSeek/Claude)."""
    smc = analysis_data.get("smc", {})

    prompt = f"""You are an expert XAUUSD scalping analyst. Review this trade setup:

## Trade Proposal
- Direction: {setup.direction}
- Entry: {setup.entry:.2f}
- Stop Loss: {setup.sl:.2f}
- Take Profit: {setup.tp:.2f}
- R:R Ratio: 1:{setup.rr_ratio}
- Confluence Score: {setup.score}/10

## Market Structure
- Bias: {smc.get('current_bias', 'N/A')}
- CHoCH: {smc.get('choch_detected', False)}
- Order Blocks: {len(smc.get('order_blocks', []))}
- FVGs: {len(smc.get('fair_value_gaps', []))}
- Sweeps: {len(smc.get('liquidity_sweeps', []))}

## Scoring Breakdown
{chr(10).join(f'- {r}' for r in setup.reasons)}

## Warnings
{chr(10).join(f'- {w}' for w in setup.warnings) if setup.warnings else 'None'}

## Risk Status
- Overall: {'APPROVED' if risk_summary.get('overall_allowed') else 'BLOCKED'}
- Spread: {risk_summary.get('spread_status', 'N/A')}
- Blackout: {risk_summary.get('blackout_status', 'N/A')}

Respond with exactly one word: APPROVE, MODIFY, or REJECT.
If MODIFY, suggest new SL and TP values on the next line.
"""
    return prompt


async def consult_ai(
    setup: TradeSetup,
    risk_summary: dict,
    analysis_data: dict,
    api_key: str = "",
) -> str:
    """Consult external AI for trade decision.

    Uses DeepSeek API. Falls back to rule-based if API unavailable.
    """
    if not api_key:
        return "APPROVE"  # Default: trust the rules

    prompt = build_ai_prompt(setup, risk_summary, analysis_data)

    try:
        import requests

        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a professional XAUUSD scalping analyst. Respond concisely."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 100,
                "temperature": 0.3,
            },
            timeout=15,
        )

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"].strip()
            return content
    except Exception:
        pass

    return "APPROVE"  # Fallback to rule-based approval
