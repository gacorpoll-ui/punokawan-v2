"""Punokawan V2 Orchestrator — Autonomous trading cycle coordinator.

Ties together all 4 MCP servers:
  - market-analysis: Technical analysis + SMC + patterns
  - risk-guardrail: Risk validation
  - learning-self: Trade journal + avoidance database
  - metatrader-ext: Lot sizing + execution

Runs a complete trading cycle: analyze → score → validate → decide → execute.
"""
