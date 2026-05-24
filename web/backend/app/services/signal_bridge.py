"""Bridge to Punokawan V2 orchestrator — reads signal data."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Path to the trading journal database
TRADING_DB = r"D:\Punokawan V2\data\trading_journal.db"
SIGNALS_DB = r"D:\Punokawan V2\web\data\signals.db"


def get_latest_signal_from_orchestrator() -> dict:
    """Read latest signal from the trading journal database."""
    try:
        if not os.path.exists(TRADING_DB):
            return _empty_signal()

        conn = sqlite3.connect(TRADING_DB)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM trades ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        conn.close()

        if row:
            return {
                "direction": row["direction"],
                "entry": row["entry"],
                "sl": row["sl"],
                "tp": row["tp"],
                "lot_size": row["lot_size"],
                "score": row["score"],
                "session": row["session"] or "",
                "verdict": row["verdict"] or "PENDING",
                "pnl": row["pnl"],
                "created_at": row["created_at"],
            }
    except Exception:
        pass

    return _empty_signal()


def get_performance_from_db() -> dict:
    """Compute performance metrics from signal history."""
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM signals WHERE exit_price IS NOT NULL ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
        conn.close()

        if not rows:
            return _empty_performance()

        trades = [dict(r) for r in rows]
        wins = [t for t in trades if (t["pnl"] or 0) > 0]
        losses = [t for t in trades if (t["pnl"] or 0) <= 0]

        total = len(trades)
        win_count = len(wins)
        win_rate = win_count / total if total > 0 else 0

        gross_profit = sum(t["pnl"] or 0 for t in wins)
        gross_loss = abs(sum(t["pnl"] or 0 for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        net_profit = sum(t["pnl"] or 0 for t in trades)

        # Simple Sharpe approximation
        import math
        pnls = [t["pnl"] or 0 for t in trades]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        variance = sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls) if pnls else 1
        std_dev = math.sqrt(variance) if variance > 0 else 1
        sharpe = (avg_pnl / std_dev) * math.sqrt(len(pnls)) if std_dev > 0 else 0

        # Monthly breakdown
        monthly = {}
        for t in trades:
            month = (t["created_at"] or "")[:7]
            if month:
                monthly.setdefault(month, {"trades": 0, "wins": 0, "pnl": 0})
                monthly[month]["trades"] += 1
                if (t["pnl"] or 0) > 0:
                    monthly[month]["wins"] += 1
                monthly[month]["pnl"] += t["pnl"] or 0

        return {
            "total_trades": total,
            "win_rate": round(win_rate, 3),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 3),
            "net_profit": round(net_profit, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "monthly_breakdown": [
                {"month": m, "trades": d["trades"], "wins": d["wins"], "pnl": round(d["pnl"], 2)}
                for m, d in sorted(monthly.items())
            ],
        }
    except Exception as e:
        return _empty_performance()


def get_system_status() -> dict:
    """Check system health — MCP servers, MT5 connection."""
    import urllib.request

    servers = {}
    for port, name in [(8081, "mt5-ext"), (8082, "market-analysis"), (8083, "learning-self"), (8084, "risk-guardrail")]:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/sse", timeout=2)
            servers[name] = "online"
        except Exception:
            servers[name] = "offline"

    mt5_status = "unknown"
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            info = mt5.account_info()
            if info:
                mt5_status = f"connected (${info.balance:.0f})"
            else:
                mt5_status = "no account"
            mt5.shutdown()
        else:
            mt5_status = "not initialized"
    except ImportError:
        mt5_status = "MT5 package not installed"

    all_online = all(v == "online" for v in servers.values())

    return {
        "servers": servers,
        "mt5": mt5_status,
        "all_healthy": all_online,
        "timestamp": datetime.now().isoformat(),
    }


def _empty_signal() -> dict:
    return {
        "direction": "NO_TRADE",
        "entry": 0, "sl": 0, "tp": 0,
        "lot_size": 0, "score": 0,
        "session": "", "verdict": "WAITING",
        "pnl": None, "created_at": datetime.now().isoformat(),
    }


def _empty_performance() -> dict:
    return {
        "total_trades": 0, "win_rate": 0, "profit_factor": 0,
        "sharpe_ratio": 0, "net_profit": 0,
        "gross_profit": 0, "gross_loss": 0,
        "monthly_breakdown": [],
    }
