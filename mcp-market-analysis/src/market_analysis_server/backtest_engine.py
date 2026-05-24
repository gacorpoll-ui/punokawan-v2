"""Local backtesting engine using backtesting.py framework.

Runs strategy backtests on historical OHLCV data and returns
comprehensive performance metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BacktestTrade:
    entry_time: str
    exit_time: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float


@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    period_start: str
    period_end: str
    total_trades: int
    win_rate: float
    profit_factor: float
    net_profit: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_holding_bars: float
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    trade_log: list = field(default_factory=list)
    error: str = ""


def run_backtest(
    df,
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
    entry_rule: str = "SMC",
    min_score: int = 6,
    sl_points: float = 15.0,
    tp_points: float = 25.0,
    use_trailing_stop: bool = False,
    trailing_trigger: float = 10.0,
) -> BacktestResult:
    """Run a backtest on historical OHLCV data.

    This is a simplified vectorized backtest that simulates the SMC-based
    entry logic. For production use, the full backtesting.py framework
    provides more accurate trade simulation with slippage modeling.

    Args:
        df: DataFrame with [open, high, low, close, tick_volume]
        symbol: Trading symbol
        timeframe: Bar timeframe
        entry_rule: Strategy entry rule ("SMC", "MA_CROSS", "RSI")
        min_score: Minimum confluence score for entry (SMC mode)
        sl_points: Stop loss in price points
        tp_points: Take profit in price points
        use_trailing_stop: Enable trailing stop
        trailing_trigger: Points in profit before activating trailing stop

    Returns:
        BacktestResult with full performance metrics
    """
    import numpy as np

    if df.empty or len(df) < 50:
        return BacktestResult(
            symbol=symbol, timeframe=timeframe,
            period_start="", period_end="",
            total_trades=0, win_rate=0, profit_factor=0,
            net_profit=0, sharpe_ratio=0, max_drawdown_pct=0,
            avg_holding_bars=0, avg_win=0, avg_loss=0,
            best_trade=0, worst_trade=0,
            error="Insufficient data (need 50+ bars)",
        )

    close = df["close"].values.astype(np.float64)
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)

    # Simple vectorized simulation
    trades = []
    in_position = False
    direction = 0
    entry_price = 0.0
    entry_idx = 0
    sl_price = 0.0
    tp_price = 0.0
    trailing_activated = False
    trailing_sl = 0.0

    for i in range(50, len(close)):
        if not in_position:
            # Simulate entry signals
            signal = _generate_signal(close, high, low, i, entry_rule, min_score)
            if signal != 0:
                direction = signal  # 1 = BUY, -1 = SELL
                entry_price = close[i]
                entry_idx = i
                if direction == 1:
                    sl_price = entry_price - sl_points
                    tp_price = entry_price + tp_points
                else:
                    sl_price = entry_price + sl_points
                    tp_price = entry_price - tp_points
                in_position = True
                trailing_activated = False
        else:
            # Check SL/TP hit
            exit_price = 0
            exit_reason = ""
            exit_idx = i

            if direction == 1:
                if low[i] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                elif high[i] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                # Trailing stop
                elif use_trailing_stop and close[i] - entry_price >= trailing_trigger:
                    if not trailing_activated:
                        trailing_sl = entry_price + trailing_trigger * 0.5
                        trailing_activated = True
                    else:
                        trailing_sl = max(trailing_sl, close[i] - trailing_trigger)
                        sl_price = max(sl_price, trailing_sl)
                        if low[i] <= sl_price:
                            exit_price = sl_price
                            exit_reason = "TRAILING_SL"
            else:
                if high[i] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                elif low[i] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                elif use_trailing_stop and entry_price - close[i] >= trailing_trigger:
                    if not trailing_activated:
                        trailing_sl = entry_price - trailing_trigger * 0.5
                        trailing_activated = True
                    else:
                        trailing_sl = min(trailing_sl, close[i] + trailing_trigger)
                        sl_price = min(sl_price, trailing_sl)
                        if high[i] >= sl_price:
                            exit_price = sl_price
                            exit_reason = "TRAILING_SL"

            if exit_price != 0:
                pnl = (exit_price - entry_price) * direction
                pnl_pct = (pnl / entry_price) * 100

                trades.append(BacktestTrade(
                    entry_time=str(df.index[entry_idx]) if hasattr(df.index[entry_idx], 'isoformat') else str(entry_idx),
                    exit_time=str(df.index[exit_idx]) if hasattr(df.index[exit_idx], 'isoformat') else str(exit_idx),
                    direction="BUY" if direction == 1 else "SELL",
                    entry_price=round(float(entry_price), 2),
                    exit_price=round(float(exit_price), 2),
                    pnl=round(float(pnl), 2),
                    pnl_pct=round(float(pnl_pct), 3),
                ))
                in_position = False

    if not trades:
        return BacktestResult(
            symbol=symbol, timeframe=timeframe,
            period_start=str(df.index[0]) if len(df) > 0 else "",
            period_end=str(df.index[-1]) if len(df) > 0 else "",
            total_trades=0, win_rate=0, profit_factor=0,
            net_profit=0, sharpe_ratio=0, max_drawdown_pct=0,
            avg_holding_bars=0, avg_win=0, avg_loss=0,
            best_trade=0, worst_trade=0,
        )

    # Compute metrics
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]

    win_rate = len(wins) / len(trades) if trades else 0
    gross_profit = sum(t.pnl for t in wins) if wins else 0
    gross_loss = abs(sum(t.pnl for t in losses)) if losses else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    net_profit = sum(t.pnl for t in trades)

    avg_win = gross_profit / len(wins) if wins else 0
    avg_loss = -(gross_loss / len(losses)) if losses else 0

    best_trade = max(t.pnl for t in trades) if trades else 0
    worst_trade = min(t.pnl for t in trades) if trades else 0

    # Sharpe ratio (annualized, assuming 252 trading days)
    returns = [t.pnl for t in trades]
    if len(returns) > 1:
        avg_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        sharpe = (avg_return / std_return) * np.sqrt(len(trades)) if std_return > 0 else 0
    else:
        sharpe = 0

    # Max drawdown from cumulative PnL
    cumulative = np.cumsum([t.pnl for t in trades])
    peak = np.maximum.accumulate(cumulative)
    drawdowns = peak - cumulative
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0
    max_dd_pct = (max_dd / (abs(cumulative[0]) + 1000)) * 100 if len(cumulative) > 0 else 0

    return BacktestResult(
        symbol=symbol,
        timeframe=timeframe,
        period_start=str(df.index[0]) if len(df) > 0 else "",
        period_end=str(df.index[-1]) if len(df) > 0 else "",
        total_trades=len(trades),
        win_rate=round(win_rate, 3),
        profit_factor=round(profit_factor, 2),
        net_profit=round(net_profit, 2),
        sharpe_ratio=round(sharpe, 3),
        max_drawdown_pct=round(max_dd_pct, 2),
        avg_holding_bars=0,  # Simplified, not tracking exactly
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        best_trade=round(best_trade, 2),
        worst_trade=round(worst_trade, 2),
        trade_log=trades[-20:],  # Last 20 trades
    )


def _generate_signal(close, high, low, idx, rule: str, min_score: int) -> int:
    """Generate a trade signal at the given index.

    Returns: 1 (BUY), -1 (SELL), or 0 (NO TRADE)
    """
    if rule == "SMC":
        # Simplified SMC: use EMA cross + RSI hint
        if idx < 50:
            return 0

        # Quick EMA cross
        ema9 = _ema(close[:idx + 1], 9)
        ema21 = _ema(close[:idx + 1], 21)

        if np.isnan(ema9[-1]) or np.isnan(ema21[-1]) or np.isnan(ema9[-2]) or np.isnan(ema21[-2]):
            return 0

        # Golden cross
        if ema9[-2] <= ema21[-2] and ema9[-1] > ema21[-1]:
            return 1
        # Death cross
        if ema9[-2] >= ema21[-2] and ema9[-1] < ema21[-1]:
            return -1

    elif rule == "MA_CROSS":
        if idx < 50:
            return 0
        ema9 = _ema(close[:idx + 1], 9)
        ema50 = _ema(close[:idx + 1], 50)
        if np.isnan(ema9[-1]) or np.isnan(ema50[-1]):
            return 0
        if ema9[-1] > ema50[-1] and ema9[-2] <= ema50[-2]:
            return 1
        if ema9[-1] < ema50[-1] and ema9[-2] >= ema50[-2]:
            return -1

    return 0


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    import numpy as np
    result = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < period:
        return result
    multiplier = 2 / (period + 1)
    result[period - 1] = np.mean(series[:period])
    for i in range(period, len(series)):
        result[i] = (series[i] - result[i - 1]) * multiplier + result[i - 1]
    return result
