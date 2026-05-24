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


# ── Multi-Provider AI Configuration ──────────────────────────

PROVIDERS = {
    "DEEPSEEK": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "header_key": "Authorization",
        "header_prefix": "Bearer ",
    },
    "CLAUDE": {
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-sonnet-4-20250514",
        "header_key": "x-api-key",
        "header_prefix": "",
        "version": "2023-06-01",
    },
    "OPENAI": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o",
        "header_key": "Authorization",
        "header_prefix": "Bearer ",
    },
    "GEMINI": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        "model": "gemini-2.0-flash",
        "header_key": "x-goog-api-key",
        "header_prefix": "",
    },
    "CUSTOM": {
        "url": "",  # Set via CUSTOM_API_URL in .env
        "model": "",  # Set via CUSTOM_MODEL in .env
        "header_key": "Authorization",
        "header_prefix": "Bearer ",
    },
}


def _get_api_key(provider: str) -> str:
    """Get API key for the given provider from .env."""
    import os

    key_map = {
        "DEEPSEEK": "DEEPSEEK_API_KEY",
        "CLAUDE": "ANTHROPIC_API_KEY",
        "OPENAI": "OPENAI_API_KEY",
        "GEMINI": "GEMINI_API_KEY",
    }
    env_var = key_map.get(provider, "")
    # Try env file first, then OS env
    if env_var:
        return os.environ.get(env_var, "")
    return ""


def build_sltp_ai_prompt(
    direction: str, price: float, analysis_data: dict, trading_config: dict
) -> str:
    """Build a prompt for AI to suggest SL/TP based on trading style + market context.

    The AI receives full market structure and style parameters,
    then returns specific SL and TP values.
    """
    smc = analysis_data.get("smc", {})
    ind_list = analysis_data.get("indicators", {}).get("results", [])

    # Format indicators
    ind_lines = []
    for r in ind_list:
        ind = r.get("indicators", {})
        ind_lines.append(
            f"  {r['timeframe']:4s} Close={r['last_close']} "
            f"RSI={ind.get('rsi14','?')} ATR={ind.get('atr14','?')} "
            f"EMA9={ind.get('ema9','?')}"
        )

    # Format SMC
    obs = smc.get("order_blocks", [])
    ob_lines = [f"  [{ob['type']}] {ob['high']:.2f}-{ob['low']:.2f}" for ob in obs[:6]]
    fvgs = smc.get("fair_value_gaps", [])
    fvg_lines = [f"  [{f['type']}] {f['high']:.2f}-{f['low']:.2f}" for f in fvgs[:6]]
    sweeps = smc.get("liquidity_sweeps", [])
    swp_lines = [f"  [{s['type']}] level={s['swept_level']:.2f} depth={s['pip_depth']}pips" for s in sweeps[:4]]

    prompt = f"""You are an expert XAUUSD {trading_config.get('style', 'SCALPING')} trader. Suggest optimal SL and TP.

## Trading Style
- Style: {trading_config.get('style', 'SCALPING')}
- Primary TF: {trading_config.get('primary_tf', 'M1')}
- SL range: {trading_config.get('min_sl_points', 3)}-{trading_config.get('max_sl_points', 7)} price units
- TP max: {trading_config.get('max_tp_points', 15)} price units
- Risk/trade: {trading_config.get('risk_per_trade_pct', 10)}%
- Description: {trading_config.get('description', '')}

## Market Context
- Direction: {direction}
- Current Price: {price:.2f}
- Market Bias: {smc.get('current_bias', 'N/A')}
- CHoCH: {smc.get('choch_detected', False)}
- BOS Levels: {smc.get('bos_levels', [])[:5]}

## Indicators
{chr(10).join(ind_lines) if ind_lines else 'No indicator data'}

## Order Blocks (nearest to price)
{chr(10).join(ob_lines) if ob_lines else 'None'}

## Fair Value Gaps
{chr(10).join(fvg_lines) if fvg_lines else 'None'}

## Liquidity Sweeps
{chr(10).join(swp_lines) if swp_lines else 'None'}

## Daily Levels
PDH={smc.get('daily_levels', {}).get('pdh', '?')} PDL={smc.get('daily_levels', {}).get('pdl', '?')}

Respond with EXACTLY this JSON format (no other text):
{{"entry": {price:.2f}, "sl": 0.00, "tp": 0.00, "reasoning": "one line explanation"}}

Choose SL and TP based on:
1. Nearest structural levels (OB, FVG, PDH/PDL, swing points)
2. ATR for volatility-adjusted distance
3. Trading style constraints
4. SL must protect against noise (use ATR-based buffer)
5. TP must target the nearest logical structural level"""
    return prompt


def parse_sltp_response(response: str, fallback_entry: float, fallback_sl: float, fallback_tp: float) -> tuple:
    """Parse AI SL/TP response. Falls back to structural values if parsing fails."""
    import json as _json
    try:
        # Extract JSON from response (may have markdown wrapping)
        text = response.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = _json.loads(text[start:end])
            entry = float(data.get("entry", fallback_entry))
            sl = float(data.get("sl", fallback_sl))
            tp = float(data.get("tp", fallback_tp))
            reasoning = data.get("reasoning", "")
            return entry, sl, tp, reasoning
    except Exception:
        pass
    return fallback_entry, fallback_sl, fallback_tp, ""


def build_ai_prompt(setup: TradeSetup, risk_summary: dict, analysis_data: dict) -> str:
    """Build a prompt for AI trade consultation."""
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
    provider: str = "DEEPSEEK",
    api_key: str = "",
    custom_prompt: str = "",
) -> str:
    """Consult external AI for trade decision — multi-provider support.

    Providers: DEEPSEEK, CLAUDE, OPENAI, GEMINI, CUSTOM
    Set custom_prompt to override the default decision prompt (for SL/TP, etc.)
    Falls back to rule-based approval if API unavailable or no key.
    """
    if not api_key:
        return "APPROVE"

    cfg = dict(PROVIDERS.get(provider.upper(), {}))
    if not cfg:
        return f"APPROVE (unknown provider: {provider})"

    # Custom provider: read URL and model from .env
    if provider.upper() == "CUSTOM":
        import os
        custom_url = os.environ.get("CUSTOM_API_URL", "")
        custom_model = os.environ.get("CUSTOM_MODEL", "gpt-4o")
        if not custom_url:
            return "APPROVE (CUSTOM_API_URL not set in .env)"
        cfg["url"] = custom_url
        cfg["model"] = custom_model

    prompt = custom_prompt if custom_prompt else build_ai_prompt(setup, risk_summary, analysis_data)

    try:
        import requests

        headers = {"Content-Type": "application/json"}
        headers[cfg["header_key"]] = cfg["header_prefix"] + api_key

        if cfg.get("version"):
            headers["anthropic-version"] = cfg["version"]

        if provider.upper() == "CLAUDE":
            # Anthropic Messages API format
            body = {
                "model": cfg["model"],
                "max_tokens": 100,
                "temperature": 0.3,
                "system": "You are a professional XAUUSD scalping analyst. Respond with exactly one word: APPROVE, MODIFY, or REJECT.",
                "messages": [{"role": "user", "content": prompt}],
            }
        elif provider.upper() == "GEMINI":
            # Google Gemini API format
            body = {
                "contents": [{
                    "parts": [{"text": f"You are a professional XAUUSD scalping analyst. Respond with exactly one word: APPROVE, MODIFY, or REJECT.\n\n{prompt}"}]
                }],
                "generationConfig": {"maxOutputTokens": 50, "temperature": 0.3},
            }
        else:
            # OpenAI-compatible format (DeepSeek, OpenAI, and others)
            body = {
                "model": cfg["model"],
                "messages": [
                    {"role": "system", "content": "You are a professional XAUUSD scalping analyst. Respond with exactly one word: APPROVE, MODIFY, or REJECT."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 100,
                "temperature": 0.3,
            }

        response = requests.post(cfg["url"], headers=headers, json=body, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if provider.upper() == "CLAUDE":
                content = data["content"][0]["text"].strip()
            elif provider.upper() == "GEMINI":
                content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                content = data["choices"][0]["message"]["content"].strip()
            return content
        else:
            print(f"  [AI] {provider} error: {response.status_code} {response.text[:100]}")
    except Exception as e:
        print(f"  [AI] {provider} exception: {e}")

    return "APPROVE"
