"""Trading style presets — auto-configure all parameters from one setting.

All SL/TP/trail values in PRICE UNITS (e.g., 3.0 = 30 pips = 3000 broker pts).
Universal — works for both 2-digit and 3-digit broker pricing.

Usage: set TRADING_STYLE=SCALPING|INTRADAY|SWING|CUSTOM in .env
"""

from dataclasses import dataclass, field

# ── Preset Definitions (values in PRICE UNITS) ────────────────
PRESETS = {
    "SCALPING": {
        "TIMEFRAMES": ["M1", "M5", "M15", "H1"],
        "PRIMARY_TF": "M1",
        "MIN_CONFLUENCE_SCORE": 6,
        "MIN_RR_RATIO": 1.2,
        "MIN_SL_POINTS": 3.0,       # 30 pips
        "MAX_SL_POINTS": 7.0,       # 70 pips
        "MAX_TP_POINTS": 15.0,      # 150 pips
        "RISK_PER_TRADE_PCT": 10.0,
        "MAX_DAILY_LOSS_PCT": 15.0,
        "MAX_DAILY_LOSS": 0,
        "MAX_SPREAD_PIPS": 3.0,
        "MAX_LATENCY_MS": 300,
        "BLACKOUT_MINUTES": 10,
        "USE_TRAILING_STOP": True,
        "TRAILING_TRIGGER_PTS": 5.0,  # 50 pips
        "LOT_MODE": "FIXED",
        "SESSION_FILTER": ["LONDON", "NY", "OVERLAP"],
        "description": "Scalping M1. SL 30-70 pips, TP 50-150 pips. 10% risk, 15% daily DD.",
    },
    "INTRADAY": {
        "TIMEFRAMES": ["M15", "H1", "H4", "D1"],
        "PRIMARY_TF": "H1",
        "MIN_CONFLUENCE_SCORE": 7,
        "MIN_RR_RATIO": 1.5,
        "MIN_SL_POINTS": 5.0,       # 50 pips
        "MAX_SL_POINTS": 15.0,      # 150 pips
        "MAX_TP_POINTS": 30.0,      # 300 pips
        "RISK_PER_TRADE_PCT": 1.5,
        "MAX_DAILY_LOSS_PCT": 10.0,
        "MAX_DAILY_LOSS": 0,
        "MAX_SPREAD_PIPS": 5.0,
        "MAX_LATENCY_MS": 500,
        "BLACKOUT_MINUTES": 30,
        "USE_TRAILING_STOP": True,
        "TRAILING_TRIGGER_PTS": 10.0,  # 100 pips
        "LOT_MODE": "RISK_PCT",
        "SESSION_FILTER": ["LONDON", "NY", "OVERLAP"],
        "description": "Intraday H1. SL 50-150 pips, TP 100-300 pips.",
    },
    "SWING": {
        "TIMEFRAMES": ["H1", "H4", "D1", "W1"],
        "PRIMARY_TF": "H4",
        "MIN_CONFLUENCE_SCORE": 8,
        "MIN_RR_RATIO": 2.0,
        "MIN_SL_POINTS": 10.0,      # 100 pips
        "MAX_SL_POINTS": 30.0,      # 300 pips
        "MAX_TP_POINTS": 60.0,      # 600 pips
        "RISK_PER_TRADE_PCT": 2.0,
        "MAX_DAILY_LOSS_PCT": 20.0,
        "MAX_DAILY_LOSS": 0,
        "MAX_SPREAD_PIPS": 8.0,
        "MAX_LATENCY_MS": 500,
        "BLACKOUT_MINUTES": 60,
        "USE_TRAILING_STOP": True,
        "TRAILING_TRIGGER_PTS": 20.0,  # 200 pips
        "LOT_MODE": "RISK_PCT",
        "SESSION_FILTER": ["ASIAN", "LONDON", "NY", "OVERLAP"],
        "description": "Swing H4/D1. SL 100-300 pips, TP 200-600 pips.",
    },
}


@dataclass
class TradingConfig:
    style: str
    timeframes: list
    primary_tf: str
    min_confluence_score: int
    min_rr_ratio: float
    min_sl_points: float
    max_sl_points: float
    max_tp_points: float
    risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_daily_loss: float
    max_spread_pips: float
    max_latency_ms: int
    blackout_minutes: int
    use_trailing_stop: bool
    trailing_trigger_pts: float
    lot_mode: str
    session_filter: list
    description: str = ""


def get_trading_config(env: dict) -> TradingConfig:
    """Get trading configuration from .env with preset support.

    - SCALPING/INTRADAY/SWING: use preset values (ignore .env overrides)
    - CUSTOM: use .env values exclusively
    """
    style = env.get("TRADING_STYLE", "SCALPING").upper().strip()
    preset = PRESETS.get(style, {})

    def _get(key: str, default):
        """CUSTOM mode: .env value. Preset mode: preset > default."""
        if style == "CUSTOM":
            env_val = env.get(key, "")
            if env_val != "":
                if isinstance(default, list):
                    return [s.strip() for s in env_val.split(",")]
                if isinstance(default, bool):
                    return env_val.lower() in ("true", "yes", "1")
                return type(default)(env_val)
            return default
        else:
            if preset and key in preset:
                return preset[key]
            return default

    return TradingConfig(
        style=style,
        timeframes=_get("TIMEFRAMES", ["M1", "M5", "M15", "H1"]),
        primary_tf=_get("PRIMARY_TF", "M1"),
        min_confluence_score=int(_get("MIN_CONFLUENCE_SCORE", 6)),
        min_rr_ratio=float(_get("MIN_RR_RATIO", 1.2)),
        min_sl_points=float(_get("MIN_SL_POINTS", 3.0)),
        max_sl_points=float(_get("MAX_SL_POINTS", 7.0)),
        max_tp_points=float(_get("MAX_TP_POINTS", 15.0)),
        risk_per_trade_pct=float(_get("RISK_PER_TRADE_PCT", 10.0)),
        max_daily_loss_pct=float(_get("MAX_DAILY_LOSS_PCT", 15.0)),
        max_daily_loss=float(_get("MAX_DAILY_LOSS", 0)),
        max_spread_pips=float(_get("MAX_SPREAD_PIPS", 3.0)),
        max_latency_ms=int(_get("MAX_LATENCY_MS", 300)),
        blackout_minutes=int(_get("BLACKOUT_MINUTES", 10)),
        use_trailing_stop=_get("USE_TRAILING_STOP", True),
        trailing_trigger_pts=float(_get("TRAILING_TRIGGER_PTS", 5.0)),
        lot_mode=_get("LOT_MODE", "FIXED"),
        session_filter=_get("SESSION_FILTER", ["LONDON", "NY", "OVERLAP"]),
        description=preset.get("description", "Custom configuration"),
    )
