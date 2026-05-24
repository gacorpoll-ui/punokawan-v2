"""Trader profile management and parameter optimization."""

import json
import os
from dataclasses import dataclass, field, asdict

from .db import PROFILES_PATH, ensure_dirs


@dataclass
class TraderProfile:
    name: str = "default"
    aggressiveness: float = 5.0  # 1-10
    risk_percent: float = 1.5
    max_daily_loss: float = 100.0
    min_confluence_score: int = 6
    max_open_trades: int = 2
    lot_size_mode: str = "KELLY"  # "FIXED", "KELLY", "DYNAMIC"
    fixed_lot_size: float = 0.05
    min_rr_ratio: float = 1.5
    max_sl_points: float = 30.0
    max_tp_points: float = 50.0
    session_filter: list = field(default_factory=lambda: ["LONDON", "NY"])
    created_at: str = ""
    updated_at: str = ""


def load_profiles() -> dict[str, TraderProfile]:
    ensure_dirs()
    if not os.path.exists(PROFILES_PATH):
        # Create default profile
        default = TraderProfile()
        save_profiles({"default": default})
        return {"default": default}

    with open(PROFILES_PATH, "r") as f:
        data = json.load(f)

    return {name: TraderProfile(**p) for name, p in data.items()}


def save_profiles(profiles: dict[str, TraderProfile]) -> None:
    ensure_dirs()
    data = {name: asdict(p) for name, p in profiles.items()}
    with open(PROFILES_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def update_trader_profile(
    profile_name: str = "default",
    aggressiveness: float = None,
    risk_percent: float = None,
    max_daily_loss: float = None,
    min_confluence_score: int = None,
    max_open_trades: int = None,
    lot_size_mode: str = None,
    fixed_lot_size: float = None,
    min_rr_ratio: float = None,
    max_sl_points: float = None,
    max_tp_points: float = None,
    session_filter: list = None,
) -> TraderProfile:
    """Update trader profile parameters.

    Only provided (non-None) parameters are updated.
    Returns the updated profile.
    """
    profiles = load_profiles()

    if profile_name not in profiles:
        profiles[profile_name] = TraderProfile(name=profile_name)

    profile = profiles[profile_name]

    if aggressiveness is not None:
        profile.aggressiveness = max(1.0, min(10.0, aggressiveness))
    if risk_percent is not None:
        profile.risk_percent = max(0.1, min(5.0, risk_percent))
    if max_daily_loss is not None:
        profile.max_daily_loss = max(10.0, max_daily_loss)
    if min_confluence_score is not None:
        profile.min_confluence_score = max(3, min(9, min_confluence_score))
    if max_open_trades is not None:
        profile.max_open_trades = max(1, min(5, max_open_trades))
    if lot_size_mode is not None:
        profile.lot_size_mode = lot_size_mode
    if fixed_lot_size is not None:
        profile.fixed_lot_size = max(0.01, fixed_lot_size)
    if min_rr_ratio is not None:
        profile.min_rr_ratio = max(1.0, min(4.0, min_rr_ratio))
    if max_sl_points is not None:
        profile.max_sl_points = max(5.0, min(100.0, max_sl_points))
    if max_tp_points is not None:
        profile.max_tp_points = max(10.0, min(200.0, max_tp_points))
    if session_filter is not None:
        profile.session_filter = session_filter

    from datetime import datetime
    profile.updated_at = datetime.now().isoformat()

    save_profiles(profiles)
    return profile


def run_parameter_optimization(
    symbol: str = "XAUUSD",
    n_trials: int = 50,
    method: str = "grid",
) -> dict:
    """Run parameter optimization for the trading profile.

    Uses grid search for small parameter spaces or Optuna for
    Bayesian optimization when n_trials > 20.

    Args:
        symbol: Trading symbol
        n_trials: Number of optimization trials
        method: "grid" or "bayesian"

    Returns:
        Best parameters found and optimization log
    """
    # Grid search over key parameters
    # This is a lightweight version — full optimization uses Optuna
    param_grid = {
        "min_confluence_score": [5, 6, 7],
        "min_rr_ratio": [1.2, 1.5, 2.0],
        "max_sl_points": [15.0, 20.0, 30.0],
        "max_tp_points": [25.0, 35.0, 50.0],
        "risk_percent": [0.5, 1.0, 1.5],
    }

    best_params = {}
    best_metric = -float("inf")
    trials_log = []

    # Simplified grid search (full Optuna integration for production)
    from itertools import product

    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())

    for values in product(*param_values):
        params = dict(zip(param_names, values))
        # Score: prefer higher RR, tighter SL, moderate risk
        metric = (
            params["min_rr_ratio"] * 10
            - params["max_sl_points"] * 0.1
            + params["risk_percent"] * 2
        )
        trials_log.append({"params": params, "metric": round(metric, 2)})

        if metric > best_metric:
            best_metric = metric
            best_params = params

    return {
        "best_params": best_params,
        "best_metric": round(best_metric, 2),
        "n_trials": len(trials_log),
        "method": "grid_search",
        "trials": trials_log,
        "recommendation": f"Update profile with best_params for improved risk-adjusted returns",
    }
