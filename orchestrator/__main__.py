"""Punokawan V2 Trading Cycle — Entry point.

Usage:
    python -m orchestrator                    # Single cycle
    python -m orchestrator --loop 300         # Loop every 300s (5 min)
    python -m orchestrator --ai               # Enable AI consultation
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

# Ensure the orchestrator can find all MCP servers
sys.path.insert(0, r"D:\Punokawan V2\mcp-market-analysis\src")
sys.path.insert(0, r"D:\Punokawan V2\mcp-learning-self\src")
sys.path.insert(0, r"D:\Punokawan V2\mcp-risk-guardrail\src")
sys.path.insert(0, r"D:\Punokawan V2\mcp-metatrader-ext\src")

from orchestrator.mcp_client import (
    MCPServers,
    call_tool,
    check_avoidance,
    collect_all_analysis,
    collect_risk_data,
    get_lot_size,
)
from orchestrator.scoring_engine import MIN_SCORE_TO_TRADE, score_setup
from orchestrator.decision_maker import (
    build_sltp_ai_prompt,
    consult_ai,
    parse_sltp_response,
    rule_based_decision,
)
from orchestrator.trading_presets import get_trading_config

DIRECTIVE_PATH = r"C:\Users\Riri\Documents\ai_directive.json"
ENV_PATH = r"D:\Punokawan V2\.env"


def _load_env() -> dict:
    """Load configuration from .env file into dict + os.environ."""
    config = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip()
                    config[key] = val
                    # Also set in os.environ for inter-module access
                    if key not in os.environ or not os.environ[key]:
                        os.environ[key] = val
    return config


def get_lot_config() -> dict:
    """Read lot sizing config from .env file.

    Returns dict with:
        mode: FIXED, RISK_PCT, or KELLY
        fixed_lot: lot size for FIXED mode
        risk_pct: risk % for RISK_PCT mode
    """
    env = _load_env()
    mode = env.get("LOT_MODE", "FIXED").upper().strip()
    fixed_lot = float(env.get("FIXED_LOT_SIZE", "0.05"))
    risk_pct = float(env.get("RISK_PER_TRADE_PCT", "1.5"))
    return {"mode": mode, "fixed_lot": fixed_lot, "risk_pct": risk_pct}


async def detect_symbol() -> str:
    """Auto-detect trading symbol based on MT5 account type.

    Checks account currency from MT5 terminal:
    - Cent account (USC, EURc, etc.) -> appends 'c' suffix
    - USD account -> standard symbol

    Falls back to SYMBOL from .env if MT5 not available.
    """
    env = _load_env()
    symbol = env.get("SYMBOL", "XAUUSD")
    account_type = env.get("ACCOUNT_TYPE", "AUTO").upper()

    if account_type != "AUTO":
        # Manual override: respect user setting
        print(f"  [SYMBOL] Manual: {symbol} (ACCOUNT_TYPE={account_type})")
        return symbol

    # Try to detect from MT5
    try:
        import MetaTrader5 as mt5
        if not mt5.terminal_info():
            mt5.initialize()
        info = mt5.account_info()
        if info:
            currency = info.currency
            print(f"  [SYMBOL] Account currency: {currency} | Balance: ${info.balance:.0f}")
            if currency.upper() in ("USC", "USDC", "CENT"):
                detected = symbol + "c" if not symbol.endswith("c") else symbol
                print(f"  [SYMBOL] Cent account detected -> {detected}")
                return detected
            else:
                # USD or other standard account — use base symbol without suffix
                clean = symbol.rstrip("c")
                print(f"  [SYMBOL] Standard account -> {clean}")
                return clean
    except Exception as e:
        print(f"  [SYMBOL] MT5 detect failed: {e}")

    print(f"  [SYMBOL] Using env: {symbol}")
    return symbol


def calculate_lot(mode: str, fixed_lot: float, risk_pct: float,
                  balance: float, sl_points: float,
                  contract_size: float = 100.0, point: float = 0.01) -> float:
    """Calculate lot size based on mode.

    FIXED: use exact fixed_lot from env
    RISK_PCT: risk % of balance based on SL distance
    KELLY: placeholder (handled by metatrader-ext)
    """
    if mode == "FIXED":
        return fixed_lot
    elif mode == "RISK_PCT":
        if sl_points <= 0:
            return fixed_lot
        risk_amount = balance * (risk_pct / 100)
        pip_value_per_lot = contract_size * point
        lot = risk_amount / (sl_points * pip_value_per_lot)
        return round(lot, 2)
    else:  # KELLY — handled by optimize_lot_size tool
        return fixed_lot

# Session trading hours (UTC)
SESSIONS = {
    "ASIAN":  {"start": 0,  "end": 9,   "label": "Asian"},
    "LONDON": {"start": 7,  "end": 16,  "label": "London"},
    "NY":     {"start": 12, "end": 21,  "label": "New York"},
    "OVERLAP": {"start": 12, "end": 16, "label": "London+NY Overlap"},
}


def get_current_session() -> str:
    """Detect current trading session based on UTC hour."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    weekday = now.weekday()

    if weekday >= 5:  # Saturday/Sunday
        return "WEEKEND"

    if SESSIONS["OVERLAP"]["start"] <= hour < SESSIONS["OVERLAP"]["end"]:
        return "OVERLAP"
    elif SESSIONS["ASIAN"]["start"] <= hour < SESSIONS["ASIAN"]["end"]:
        return "ASIAN"
    elif SESSIONS["LONDON"]["start"] <= hour < SESSIONS["LONDON"]["end"]:
        return "LONDON"
    elif SESSIONS["NY"]["start"] <= hour < SESSIONS["NY"]["end"]:
        return "NY"
    return "OFF_HOURS"


def write_directive(direction: str, entry: float, sl: float, tp: float, lot: float,
                    score: float, reasons: list, warnings: list, ai_opinion: str = "") -> bool:
    """Write ai_directive.json for MT5 bridge execution."""
    try:
        # Guard: don't overwrite existing directive
        if os.path.exists(DIRECTIVE_PATH):
            print("  [DIRECTIVE] Existing directive found — skipping (not overwriting)")
            return False

        directive = {
            "direction": direction,
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "lot": round(lot, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "punokawan_v2",
            "ai_decision": "APPROVE",
            "ai_confidence": min(0.95, score / 10.0),
            "ai_reasoning": " | ".join(reasons[-4:]) if reasons else "Rule-based approval",
            "ai_risk_notes": " | ".join(warnings) if warnings else "No warnings",
        }

        with open(DIRECTIVE_PATH, "w") as f:
            json.dump(directive, f, indent=2)

        print(f"  [DIRECTIVE] Written to {DIRECTIVE_PATH}")
        return True
    except Exception as e:
        print(f"  [DIRECTIVE] Error: {e}")
        return False


async def fetch_mt5_account() -> dict:
    """Fetch live account data from MT5 via mcp-metatrader-ext."""
    try:
        status = await call_tool(MCPServers.METATRADER_EXT, "tool_get_terminal_status", {})
        if status.get("connected"):
            acct = status.get("account", {})
            return {
                "balance": acct.get("balance", 10000.0),
                "equity": acct.get("equity", 10000.0),
                "margin_level": acct.get("margin_level", 200.0),
                "connected": True,
            }
    except Exception:
        pass
    return {"balance": 10000.0, "equity": 10000.0, "margin_level": 200.0, "connected": False}


def build_market_context(setup, analysis: dict) -> str:
    """Build a concise market context string for avoidance DB and journal."""
    smc = analysis.get("smc", {})
    ind_list = analysis.get("indicators", {}).get("results", [])
    h1 = {}
    for r in ind_list:
        if r.get("timeframe") == "H1":
            h1 = r.get("indicators", {})
            break

    parts = [
        f"{setup.direction}",
        f"bias={smc.get('current_bias', '?')}",
        f"rsi={h1.get('rsi14', '?')}",
        f"atr={h1.get('atr14', '?')}",
        f"score={setup.score}",
        f"rr={setup.rr_ratio}",
        f"obs={len(smc.get('order_blocks', []))}",
        f"fvgs={len(smc.get('fair_value_gaps', []))}",
    ]
    return " ".join(str(p) for p in parts)


async def run_cycle(
    symbol: str = "XAUUSD",
    balance: float = 10000.0,
    equity: float = 10000.0,
    use_ai: bool = False,
    api_key: str = "",
    force: bool = False,
) -> dict:
    """Run one complete trading cycle.

    Returns a dict with the full cycle log for display/journaling.
    """
    t0 = time.time()
    session = get_current_session()

    # Load trading style config
    env = _load_env()
    cfg = get_trading_config(env)

    # Auto-detect symbol from MT5 account type
    symbol = await detect_symbol()
    mt5_path = env.get("MT5_PATH", "")

    # For cent accounts: use standard symbol for data, cent suffix for trading
    if symbol.endswith("c"):
        data_symbol = symbol.rstrip("c")
        trade_symbol = symbol
        print(f"  [SYMBOL] Data: {data_symbol} | Trade: {trade_symbol}")
    else:
        data_symbol = symbol
        trade_symbol = symbol

    # Calculate daily loss limit (percentage or fixed)
    if cfg.max_daily_loss_pct > 0 and balance > 0:
        daily_loss_limit = balance * (cfg.max_daily_loss_pct / 100)
    else:
        daily_loss_limit = cfg.max_daily_loss

    # Use trading config risk params
    max_risk_pct = cfg.risk_per_trade_pct

    log = {"symbol": symbol, "timestamp": datetime.now().isoformat(), "session": session}

    print()
    print("=" * 60)
    print(f"  PUNOKAWAN V2 — Trading Cycle — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Style: {cfg.style:10s} | Session: {session:8s} | Symbol: {symbol}")
    print(f"  TF: {cfg.primary_tf:4s} | Score min: {cfg.min_confluence_score} | "
          f"SL: {cfg.min_sl_points}-{cfg.max_sl_points} | TP max: {cfg.max_tp_points}")
    if mt5_path:
        print(f"  MT5: {mt5_path}")
    print("=" * 60)

    # Session check
    if not force and session in ("WEEKEND", "OFF_HOURS"):
        print(f"\n  >>> SKIP: Market closed or off-hours ({session})")
        print(f"  Use --force to override session check")
        log["decision"] = "SKIP"
        log["reason"] = f"Session: {session}"
        return log

    # Fetch live account
    acct = await fetch_mt5_account()
    balance = acct.get("balance", balance)
    equity = acct.get("equity", equity)
    margin_level = acct.get("margin_level", 200.0)
    if acct.get("connected"):
        print(f"  Account: ${balance:.0f} balance | ${equity:.0f} equity | {margin_level:.0f}% margin")
    else:
        print(f"  Account: ${balance:.0f} (simulated — MT5 not connected)")

    # ── Phase 1: Market Analysis ──────────────────────────
    print("\n[1/5] Collecting market analysis...")
    try:
        analysis = await collect_all_analysis(data_symbol)
        log["analysis_ok"] = True
    except Exception as e:
        print(f"  ERROR: {e}")
        log["analysis_ok"] = False
        log["error"] = str(e)
        return log

    # Get bid/ask from indicators
    m15_close = 0
    for r in analysis.get("indicators", {}).get("results", []):
        if r.get("timeframe") == "M15":
            m15_close = r.get("last_close", 0)

    bid = m15_close - 0.15  # Approximate
    ask = m15_close + 0.17

    print(f"  Price: {m15_close:.2f} | Spread: {(ask - bid) / 0.01:.1f} pips")

    # ── Phase 2: Scoring ──────────────────────────────────
    print("\n[2/5] Scoring setup...")
    # Pass TP mode from env into analysis for scoring engine
    analysis["tp_mode"] = env.get("TP_MODE", "DYNAMIC").upper().strip()
    setup = score_setup(analysis)

    direction_str = setup.direction.replace("BUY", "LONG").replace("SELL", "SHORT")
    print(f"  Direction: {setup.direction}")
    print(f"  Score:     {setup.score}/10 (min: {MIN_SCORE_TO_TRADE})")
    print(f"  Entry: {setup.entry:.2f} | SL: {setup.sl:.2f} | TP: {setup.tp:.2f}")
    print(f"  R:R = 1:{setup.rr_ratio:.1f}")
    for r in setup.reasons:
        print(f"    {r}")
    if setup.warnings:
        for w in setup.warnings:
            print(f"    [WARN] {w}")

    log["setup"] = {
        "direction": setup.direction,
        "score": setup.score,
        "entry": setup.entry,
        "sl": setup.sl,
        "tp": setup.tp,
        "rr": setup.rr_ratio,
    }

    if setup.score < MIN_SCORE_TO_TRADE:
        print(f"\n  >>> SKIP: Score {setup.score} < {MIN_SCORE_TO_TRADE}")
        log["decision"] = "SKIP"
        log["reason"] = f"Score {setup.score} < {MIN_SCORE_TO_TRADE}"
        return log

    # ── Optional: AI SL/TP suggestion ──────────────────────
    tp_sl_mode = env.get("TP_SL_MODE", "DYNAMIC").upper().strip()
    ai_sltp_reasoning = ""

    if tp_sl_mode == "AI" and use_ai and api_key:
        print("\n[AI SL/TP] Consulting AI for optimal SL/TP...")
        try:
            sltp_prompt = build_sltp_ai_prompt(
                direction=setup.direction,
                price=setup.entry,
                analysis_data=analysis,
                trading_config={
                    "style": cfg.style,
                    "primary_tf": cfg.primary_tf,
                    "min_sl_points": cfg.min_sl_points,
                    "max_sl_points": cfg.max_sl_points,
                    "max_tp_points": cfg.max_tp_points,
                    "risk_per_trade_pct": cfg.risk_per_trade_pct,
                    "description": cfg.description,
                },
            )

            # Use a lightweight AI call for SL/TP only
            ai_sltp_response = await consult_ai(
                setup, risk_summary={"overall_allowed": True}, analysis_data=analysis,
                provider=ai_provider, api_key=api_key, custom_prompt=sltp_prompt,
            )

            ai_entry, ai_sl, ai_tp, ai_sltp_reasoning = parse_sltp_response(
                ai_sltp_response, setup.entry, setup.sl, setup.tp
            )

            # Validate AI-suggested levels within style constraints
            ai_sl_dist = abs(ai_entry - ai_sl)
            ai_tp_dist = abs(ai_tp - ai_entry)

            if cfg.min_sl_points <= ai_sl_dist <= cfg.max_sl_points and ai_tp_dist <= cfg.max_tp_points:
                setup.entry = ai_entry
                setup.sl = ai_sl
                setup.tp = ai_tp
                setup.rr_ratio = ai_tp_dist / ai_sl_dist if ai_sl_dist > 0 else 0
                print(f"  [AI] Entry: {ai_entry:.2f} | SL: {ai_sl:.2f} ({ai_sl_dist:.1f} pts) | TP: {ai_tp:.2f} ({ai_tp_dist:.1f} pts)")
                if ai_sltp_reasoning:
                    print(f"  [AI] {ai_sltp_reasoning[:120]}")
            else:
                print(f"  [AI] SL/TP out of style range — using structural levels instead")
                print(f"       AI SL: {ai_sl_dist:.1f} pts (range: {cfg.min_sl_points}-{cfg.max_sl_points})")
        except Exception as e:
            print(f"  [AI] SL/TP suggestion failed: {e} — using structural levels")
    elif tp_sl_mode == "AI" and not use_ai:
        print(f"  [AI SL/TP] AI mode requires --ai flag — using DYNAMIC structural levels")

    # ── Phase 3: Risk Validation ──────────────────────────
    print("\n[3/5] Risk validation...")
    try:
        risk = await collect_risk_data(
            symbol=trade_symbol,
            balance=balance,
            equity=equity,
            margin_level=margin_level,
            bid=bid,
            ask=ask,
            point=0.01,
            daily_loss_limit=daily_loss_limit,
            max_spread_pips=cfg.max_spread_pips,
            max_latency_ms=cfg.max_latency_ms,
            blackout_minutes=cfg.blackout_minutes,
        )
        log["risk"] = risk
        print(f"  Overall:  {'APPROVED' if risk.get('overall_allowed') else 'BLOCKED'}")
        print(f"  Spread:   {risk.get('spread_status', '?')}")
        print(f"  Blackout: {risk.get('blackout_status', '?')}")
        print(f"  Drawdown: buffer=${risk.get('daily_drawdown', {}).get('remaining_buffer', 0):.2f}")
    except Exception as e:
        print(f"  Risk check failed: {e}")
        log["decision"] = "BLOCKED"
        log["reason"] = f"Risk server error: {e}"
        return log

    # ── Phase 4: Avoidance Check ──────────────────────────
    print("\n[4/5] Avoidance database check...")
    market_context = build_market_context(setup, analysis)

    try:
        avoidance = await check_avoidance(market_context)
        log["avoidance"] = avoidance
        print(f"  Blocked:   {avoidance.get('blocked', False)}")
        print(f"  Max Sim:   {avoidance.get('max_similarity', 0):.3f}")
        print(f"  Lot Mult:  {avoidance.get('lot_reduction', 1.0)}x")
    except Exception:
        avoidance = {"blocked": False, "lot_reduction": 1.0, "max_similarity": 0}

    # ── Phase 5: Decision ─────────────────────────────────
    print("\n[5/5] Decision...")

    # Get trader profile
    try:
        profile = await call_tool(MCPServers.LEARNING_SELF, "tool_get_current_profile", {})
    except Exception:
        profile = {"min_rr_ratio": 1.5, "risk_percent": 1.5}

    decision = rule_based_decision(setup, risk, avoidance, profile)

    # Optional AI consultation
    if use_ai and decision.action == "EXECUTE":
        print("  Consulting AI...")
        ai_response = await consult_ai(setup, risk, analysis, provider=ai_provider, api_key=api_key)
        decision.ai_opinion = ai_response
        print(f"  AI says: {ai_response[:80]}")

        if ai_response.startswith("REJECT"):
            decision.action = "SKIP"
            decision.warnings.append("AI rejected the trade")

    log["decision"] = decision.action

    # ── Calculate lot from env config ──────────────────────
    lot_cfg = get_lot_config()
    sl_points = abs(setup.entry - setup.sl)
    env_lot = calculate_lot(
        mode=lot_cfg["mode"],
        fixed_lot=lot_cfg["fixed_lot"],
        risk_pct=lot_cfg["risk_pct"],
        balance=balance,
        sl_points=sl_points,
    )
    print(f"\n  [LOT] Mode: {lot_cfg['mode']} | Raw: {env_lot} | SL: {sl_points:.1f} pts")

    log["lot_size"] = env_lot
    log["lot_mode"] = lot_cfg["mode"]

    if decision.action == "EXECUTE":
        # Fix lot size to broker constraints via MT5
        raw_lot = env_lot
        lot_info = {}
        try:
            lot_result = await call_tool(
                MCPServers.METATRADER_EXT,
                "tool_lot_fix",
                {"lot_size": raw_lot, "symbol": trade_symbol},
            )
            fixed_lot = lot_result.get("fixed_lot", raw_lot)
            lot_info = lot_result.get("constraints", {})
            if lot_result.get("warnings"):
                for w in lot_result["warnings"]:
                    print(f"  [LOTFIX] {w}")
            print(f"  [LOTFIX] Raw: {raw_lot} -> Fixed: {fixed_lot} "
                  f"(min={lot_info.get('vol_min','?')} max={lot_info.get('vol_max','?')} "
                  f"step={lot_info.get('vol_step','?')})")
        except Exception as e:
            fixed_lot = raw_lot
            print(f"  [LOTFIX] Failed: {e} — using raw lot {fixed_lot}")

        print(f"\n  >>> EXECUTE: {decision.direction} {symbol} @ {decision.entry:.2f}")
        print(f"  >>> Lot: {fixed_lot} | SL: {decision.sl:.2f} | TP: {decision.tp:.2f}")
        print(f"  >>> Score: {decision.score}/10 | R:R 1:{setup.rr_ratio:.1f} | Session: {session}")
        if lot_info:
            print(f"  >>> Pip value/lot: ${lot_info.get('pip_value_per_lot', '?')} | "
                  f"Contract: {lot_info.get('contract_size', '?')}")

        # Write ai_directive.json for MT5 bridge (with fixed lot)
        directive_written = write_directive(
            direction=decision.direction,
            entry=decision.entry,
            sl=decision.sl,
            tp=decision.tp,
            lot=fixed_lot,
            score=decision.score,
            reasons=setup.reasons,
            warnings=decision.warnings,
            ai_opinion=decision.ai_opinion if use_ai else "",
        )

        # Log to journal
        try:
            await call_tool(
                MCPServers.LEARNING_SELF,
                "tool_log_trading_journal",
                {
                    "symbol": trade_symbol,
                    "direction": decision.direction,
                    "entry": decision.entry,
                    "sl": decision.sl,
                    "tp": decision.tp,
                    "lot_size": decision.lot_size,
                    "score": int(decision.score),
                    "session": session,
                    "verdict": "EXECUTED" if directive_written else "PENDING",
                    "notes": f"Auto-cycle {'with AI' if use_ai else 'rule-based'} | Session: {session}",
                    "market_conditions_text": market_context,
                },
            )
            print("  Journal: logged")
        except Exception:
            pass

    elif decision.action == "BLOCKED":
        print(f"\n  >>> BLOCKED: {decision.warnings}")
    else:
        print(f"\n  >>> SKIP: {decision.warnings}")

    elapsed = time.time() - t0
    print(f"\n  Cycle completed in {elapsed:.1f}s", flush=True)
    log["elapsed_s"] = round(elapsed, 1)
    sys.stdout.flush()

    return log


async def main_loop(interval: int = 300, use_ai: bool = False, force: bool = False):
    """Run continuous trading cycles."""
    env = _load_env()
    ai_provider = env.get("AI_PROVIDER", "DEEPSEEK").upper().strip()
    key_map = {"DEEPSEEK":"DEEPSEEK_API_KEY","CLAUDE":"ANTHROPIC_API_KEY","OPENAI":"OPENAI_API_KEY","GEMINI":"GEMINI_API_KEY","CUSTOM":"CUSTOM_API_KEY"}
    api_key = env.get(key_map.get(ai_provider, "DEEPSEEK_API_KEY"), "") or os.environ.get(key_map.get(ai_provider, "DEEPSEEK_API_KEY"), "")

    print("=" * 60)
    print("  PUNOKAWAN V2 — Autonomous Trading System")
    print(f"  Mode: {'AI-ASSISTED' if use_ai else 'RULE-BASED'}")
    print(f"  Force: {'YES' if force else 'NO'} | Interval: {interval}s | Symbol: XAUUSD")
    print("=" * 60)

    cycle = 0
    while True:
        cycle += 1
        try:
            await run_cycle(
                symbol="XAUUSD",
                use_ai=use_ai,
                api_key=api_key,
                force=force,
            )
        except Exception as e:
            print(f"\n  CYCLE ERROR: {e}")

        print(f"\n  Waiting {interval}s until next cycle...", flush=True)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Punokawan V2 Trading Cycle")
    parser.add_argument("--loop", type=int, default=0, help="Loop interval in seconds (0 = single run)")
    parser.add_argument("--ai", action="store_true", help="Enable AI consultation")
    parser.add_argument("--force", action="store_true", help="Skip session check (for testing)")
    parser.add_argument("--symbol", default="XAUUSD")
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    # Read AI provider + API key from .env
    env = _load_env()
    ai_provider = env.get("AI_PROVIDER", "DEEPSEEK").upper().strip()
    key_map = {"DEEPSEEK":"DEEPSEEK_API_KEY","CLAUDE":"ANTHROPIC_API_KEY","OPENAI":"OPENAI_API_KEY","GEMINI":"GEMINI_API_KEY","CUSTOM":"CUSTOM_API_KEY"}
    api_key = env.get(key_map.get(ai_provider, "DEEPSEEK_API_KEY"), "") or os.environ.get(key_map.get(ai_provider, "DEEPSEEK_API_KEY"), "")

    if args.ai and not api_key:
        print(f"[WARN] AI mode enabled but no API key found for provider '{ai_provider}'")
        print(f"       Set {key_map.get(ai_provider, 'API_KEY')} in .env")

    if args.loop > 0:
        asyncio.run(main_loop(interval=args.loop, use_ai=args.ai, force=args.force))
    else:
        asyncio.run(run_cycle(symbol=args.symbol, use_ai=args.ai, force=args.force, api_key=api_key))
