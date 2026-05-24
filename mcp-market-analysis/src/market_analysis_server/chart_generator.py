"""OHLCV chart rendering with SMC annotations using mplfinance."""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class ChartAnnotation:
    """Single chart annotation."""
    type: str  # "hline", "zone", "text", "arrow"
    price: float = 0.0
    price2: float = 0.0  # For zones
    label: str = ""
    color: str = "white"
    index: int = -1


@dataclass
class ChartResult:
    image_path: str
    width: int
    height: int
    generated_at: str
    error: str = ""


def generate_chart_image(
    df: pd.DataFrame,
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
    count: int = 100,
    annotations: Optional[list] = None,
    output_dir: str = r"D:\Punokawan V2\charts",
    show_ema: bool = True,
) -> ChartResult:
    """Generate an annotated OHLCV chart as a PNG image.

    Uses mplfinance for candlestick rendering. Annotations can include:
    - Horizontal lines (SMC levels, PDH/PDL)
    - Shaded zones (Order Blocks, FVGs)
    - Text labels
    - Arrows/markers (swing points, sweeps)

    Args:
        df: DataFrame with [open, high, low, close, tick_volume] columns
        symbol: Trading symbol
        timeframe: Chart timeframe
        count: Number of candles to show
        annotations: List of ChartAnnotation dicts
        output_dir: Where to save the PNG
        show_ema: Whether to plot EMA 9 and EMA 21 overlays

    Returns:
        ChartResult with the image file path
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import mplfinance as mpf
    except ImportError as e:
        return ChartResult(
            image_path="",
            width=0,
            height=0,
            generated_at="",
            error=f"Missing dependency: {e}",
        )

    if annotations is None:
        annotations = []

    os.makedirs(output_dir, exist_ok=True)

    # Trim to requested count
    plot_df = df.tail(count).copy()
    if plot_df.empty:
        return ChartResult(image_path="", width=0, height=0, generated_at="", error="No data")

    # Ensure datetime index
    if not isinstance(plot_df.index, pd.DatetimeIndex):
        try:
            plot_df.index = pd.to_datetime(plot_df.index)
        except Exception:
            plot_df.index = pd.RangeIndex(len(plot_df))

    # Build additional plots (EMA overlays)
    add_plots = []
    if show_ema and len(plot_df) >= 21:
        close = plot_df["close"].values.astype(np.float64)
        ema9 = _ema(close, 9)
        ema21 = _ema(close, 21)
        add_plots.extend([
            mpf.make_addplot(ema9, color="#2962FF", width=0.8, label="EMA9"),
            mpf.make_addplot(ema21, color="#FF6D00", width=0.8, label="EMA21"),
        ])

    # Build horizontal lines and shaded regions from annotations
    hlines = {}
    shaded_regions = []

    for ann in annotations:
        if isinstance(ann, dict):
            ann_type = ann.get("type", "")
            price = ann.get("price", 0)
            price2 = ann.get("price2", 0)
            label = ann.get("label", "")
            color = ann.get("color", "white")
        else:
            ann_type = ann.type
            price = ann.price
            price2 = ann.price2
            label = ann.label
            color = ann.color

        if ann_type == "hline":
            hlines[price] = (color, 0.8, f"-- {label}" if label else "--")
        elif ann_type == "zone" and price2 > 0:
            # Determine a shade color
            shade_color = _color_to_mpl(color, alpha=0.15)
            shaded_regions.append({
                "x1": plot_df.index[0],
                "x2": plot_df.index[-1],
                "y1": price,
                "y2": price2,
                "color": shade_color,
                "label": label,
            })

    # Style
    mc = mpf.make_marketcolors(
        up="#00c853", down="#ff1744", edge="inherit", wick="inherit", volume="in", alpha=0.85
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor="#1a1a2e",
        figcolor="#1a1a2e",
        gridcolor="#2d2d44",
        gridstyle="--",
        y_on_right=False,
    )

    title = f"{symbol} {timeframe} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_{timeframe}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)

    # Plot
    fig, axes = mpf.plot(
        plot_df,
        type="candle",
        style=style,
        title=title,
        ylabel="Price",
        volume=False,
        addplot=add_plots if add_plots else None,
        hlines=hlines if hlines else None,
        figsize=(14, 8),
        tight_layout=True,
        returnfig=True,
    )

    # Add shaded regions manually
    ax = axes[0]
    for region in shaded_regions:
        ax.fill_between(
            [region["x1"], region["x2"]],
            region["y1"],
            region["y2"],
            color=region["color"],
        )
        if region.get("label"):
            mid_y = (region["y1"] + region["y2"]) / 2
            ax.text(
                region["x1"], mid_y, f"  {region['label']}",
                verticalalignment="center", fontsize=7, color="#aaaaaa", alpha=0.7,
            )

    fig.savefig(filepath, dpi=100, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)

    return ChartResult(
        image_path=filepath,
        width=1400,
        height=800,
        generated_at=datetime.now().isoformat(),
    )


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    result = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < period:
        return result
    multiplier = 2 / (period + 1)
    result[period - 1] = np.mean(series[:period])
    for i in range(period, len(series)):
        result[i] = (series[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


def _color_to_mpl(color_name: str, alpha: float = 0.15):
    """Convert named colors to RGBA."""
    color_map = {
        "green": (0.0, 0.78, 0.33, alpha),
        "red": (1.0, 0.09, 0.27, alpha),
        "blue": (0.16, 0.38, 1.0, alpha),
        "orange": (1.0, 0.43, 0.0, alpha),
        "yellow": (1.0, 0.92, 0.02, alpha),
        "white": (1.0, 1.0, 1.0, alpha),
        "purple": (0.61, 0.15, 0.69, alpha),
        "cyan": (0.0, 0.74, 0.83, alpha),
    }
    return color_map.get(color_name, (0.5, 0.5, 0.5, alpha))
