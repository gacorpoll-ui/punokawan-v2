#!/usr/bin/env python
"""Punokawan V2 — Autonomous Trading Cycle Launcher.

Usage:
    python run_trading_cycle.py              # Single cycle (rule-based)
    python run_trading_cycle.py --ai         # Single cycle with AI consultation
    python run_trading_cycle.py --loop 300   # Loop every 5 minutes
"""

import os
import sys

# Add orchestrator to path
sys.path.insert(0, os.path.dirname(__file__))

from orchestrator.__main__ import main_loop, run_cycle
import asyncio
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Punokawan V2 Autonomous Trading")
    parser.add_argument("--loop", type=int, default=0)
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--symbol", default="XAUUSD")
    args = parser.parse_args()

    if args.loop > 0:
        asyncio.run(main_loop(interval=args.loop, use_ai=args.ai))
    else:
        asyncio.run(run_cycle(symbol=args.symbol, use_ai=args.ai))
