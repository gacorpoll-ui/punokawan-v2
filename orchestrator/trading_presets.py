"""Trading style presets — auto-configure all parameters from one setting.

Usage: set TRADING_STYLE=SCALPING|INTRADAY|SWING|CUSTOM in .env
The preset auto-fills all risk, SL/TP, timeframe, and scoring params.
Override individual values when using CUSTOM.
"""

from dataclasses import dataclass, field

# ── Preset Definitions ────────────────────────────────────────
PRESETS = {
    "SCALPING": {
        "TIMEFRAMES": ["M1", "M5", "M15", "H1"],
        "PRIMARY_TF": "M1",
        "MIN_CONFLUENCE_SCORE": 4,
        "MIN_RR_RATIO": 1.2,
        "MIN_SL_POINTS": 2.0,
        "MAX_SL_POINTS": 10.0,
        "MAX_TP_POINTS": 20.0,
        "RISK_PER_TRADE_PCT": 0.5,
        "MAX_DAILY_LOSS": 30.0,
        "MAX_SPREAD_PIPS": 2.0,
        "MAX_LATENCY_MS": 300,
        "BLACKOUT_MINUTES": 10,
        "USE_TRAILING_STOP": True,
        "TRAILING_TRIGGER_PTS": 3.0,
        "LOT_MODE": "FIXED",
        "SESSION_FILTER": ["LONDON", "NY", "OVERLAP"],
        "description": "Fast scalping M1-M5. Tight SL, quick TP, low risk.",
    },
    "INTRADAY": {
        "TIMEFRAMES": ["M15", "H1", "H4", "D1"],
        "PRIMARY_TF": "H1",
        "MIN_CONFLUENCE_SCORE": 6,
        "MIN_RR_RATIO": 1.5,
        "MIN_SL_POINTS": 5.0,
        "MAX_SL_POINTS": 30.0,
        "MAX_TP_POINTS": 50.0,
        "RISK_PER_TRADE_PCT": 1.0,
        "MAX_DAILY_LOSS": 100.0,
        "MAX_SPREAD_PIPS": 3.0,
        "MAX_LATENCY_MS": 500,
        "BLACKOUT_MINUTES": 30,
        "USE_TRAILING_STOP": True,
        "TRAILING_TRIGGER_PTS": 10.0,
        "LOT_MODE": "RISK_PCT",
        "SESSION_FILTER": ["LONDON", "NY", "OVERLAP"],
        "description": "Intraday H1-based. Moderate risk, news-aware.",
    },
    "SWING": {
        "TIMEFRAMES": ["H1", "H4", "D1", "W1"],
        "PRIMARY_TF": "H4",
        "MIN_CONFLUENCE_SCORE": 7,
        "MIN_RR_RATIO": 2.0,
        "MIN_SL_POINTS": 10.0,
        "MAX_SL_POINTS": 60.0,
        "MAX_TP_POINTS": 120.0,
        "RISK_PER_TRADE_PCT": 1.5,
        "MAX_DAILY_LOSS": 200.0,
        "MAX_SPREAD_PIPS": 5.0,
        "MAX_LATENCY_MS": 500,
        "BLACKOUT_MINUTES": 60,
        "USE_TRAILING_STOP": True,
        "TRAILING_TRIGGER_PTS": 20.0,
        "LOT_MODE": "RISK_PCT",
        "SESSION_FILTER": ["ASIAN", "LONDON", "NY", "OVERLAP"],
        "description": "Swing H4/D1. Wide SL, big targets, patient.",
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
            # Preset mode: use preset value, fallback to hard default
            if preset and key in preset:
                return preset[key]
            return default

    return TradingConfig(
        style=style,
        timeframes=_get("TIMEFRAMES", ["M1", "M5", "M15", "H1"]),
        primary_tf=_get("PRIMARY_TF", "M15"),
        min_confluence_score=int(_get("MIN_CONFLUENCE_SCORE", 5)),
        min_rr_ratio=float(_get("MIN_RR_RATIO", 1.5)),
        min_sl_points=float(_get("MIN_SL_POINTS", 3.0)),
        max_sl_points=float(_get("MAX_SL_POINTS", 15.0)),
        max_tp_points=float(_get("MAX_TP_POINTS", 30.0)),
        risk_per_trade_pct=float(_get("RISK_PER_TRADE_PCT", 1.0)),
        max_daily_loss=float(_get("MAX_DAILY_LOSS", 50.0)),
        max_spread_pips=float(_get("MAX_SPREAD_PIPS", 2.0)),
        max_latency_ms=int(_get("MAX_LATENCY_MS", 300)),
        blackout_minutes=int(_get("BLACKOUT_MINUTES", 15)),
        use_trailing_stop=_get("USE_TRAILING_STOP", True),
        trailing_trigger_pts=float(_get("TRAILING_TRIGGER_PTS", 5.0)),
        lot_mode=_get("LOT_MODE", "FIXED"),
        session_filter=_get("SESSION_FILTER", ["LONDON", "NY"]),
        description=preset.get("description", "Custom configuration"),
    )
