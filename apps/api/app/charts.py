"""PNG charts for the owner bot, in the store's palette (sand surface, clay ink, one sage series).

Rules followed (single-series charts): one validated hue (#4f8540 passes lightness, chroma and 3:1 contrast
on #f5f0e8), no legend box (the title names the series), thin bars with a 4px rounded data-end and a square
baseline, 2px line with an end dot, hairline recessive grid, values in ink colors — never the series color.
A PNG has no hover, so ranked bars carry their value at the tip and the text reply repeats the numbers.
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import math  # noqa: E402

from matplotlib.patches import Polygon  # noqa: E402

SURFACE, INK, INK_2, MUTED, GRID, SERIES = "#f5f0e8", "#2f2a24", "#5a5148", "#8a7f72", "#e2d8c8", "#4f8540"
ASSETS = Path(__file__).parent / "assets"
for f in ("Inter.ttf", "Fraunces.ttf"):
    if (ASSETS / f).exists():
        font_manager.fontManager.addfont(str(ASSETS / f))
SANS = "Inter" if (ASSETS / "Inter.ttf").exists() else "DejaVu Sans"
SERIF = "Fraunces" if (ASSETS / "Fraunces.ttf").exists() else SANS
DPI, WIDTH_IN = 200, 6.4


def _figure(height_in: float, title: str, subtitle: str):
    fig = plt.figure(figsize=(WIDTH_IN, height_in), dpi=DPI, facecolor=SURFACE)
    fig.text(0.04, 1 - 0.32 / height_in, title, fontfamily=SERIF, fontsize=15, color=INK, va="top")
    fig.text(0.04, 1 - 0.66 / height_in, subtitle, fontfamily=SANS, fontsize=8.5, color=MUTED, va="top")
    fig.text(0.96, 0.12 / height_in, "Ardea Skin · demo data", fontfamily=SANS, fontsize=6.5, color=MUTED,
             ha="right", va="bottom")
    return fig


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=INK_2, labelsize=8, length=0)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontfamily(SANS)


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE)
    plt.close(fig)
    return buf.getvalue()


def _bar_patch(v: float, y0: float, h: float, rx: float, ry: float) -> Polygon:
    """One filled shape: square at the baseline (x=0), rounded corners at the data end."""
    pts = [(0, y0), (v - rx, y0)]
    for k in range(9):  # bottom-right corner
        a = -math.pi / 2 + k * math.pi / 16
        pts.append((v - rx + rx * math.cos(a), y0 + ry + ry * math.sin(a)))
    for k in range(9):  # top-right corner
        a = k * math.pi / 16
        pts.append((v - rx + rx * math.cos(a), y0 + h - ry + ry * math.sin(a)))
    pts += [(v - rx, y0 + h), (0, y0 + h)]
    return Polygon(pts, closed=True, linewidth=0, facecolor=SERIES)


def ranked_bars(title: str, subtitle: str, labels: list[str], values: list[float], fmt=lambda v: f"{v:,.0f}") -> bytes:
    """Horizontal ranking, biggest on top. Labels are truncated to stay inside the left gutter."""
    n = max(len(values), 1)
    height = 1.25 + 0.36 * n
    fig = _figure(height, title, subtitle)
    top_in, bottom_in, left = 0.95, 0.35, 0.36
    ax = fig.add_axes((left, bottom_in / height, 0.56, 1 - (top_in + bottom_in) / height))
    _style(ax)
    vmax = max(values or [1]) or 1
    ax.set_xlim(0, vmax * 1.18)
    ax.set_ylim(n - 0.5, -0.5)
    ax.set_yticks(range(n), [(lb if len(lb) <= 30 else lb[:29] + "…") for lb in labels])
    ax.set_xticks([])
    # 4px radius and ≤ 0.22 in bar thickness, converted to data units of each axis
    ax_w_in = WIDTH_IN * 0.56
    ax_h_in = height * (1 - (top_in + bottom_in) / height)
    x_per_in, y_per_in = (vmax * 1.18) / ax_w_in, n / ax_h_in
    thick = min(0.22 * y_per_in, 0.62)
    r_in = 4 / 96
    for i, v in enumerate(values):
        if v <= 0:
            continue
        ax.add_patch(_bar_patch(v, i - thick / 2, thick, min(r_in * x_per_in, v / 2), min(r_in * y_per_in, thick / 2)))
        ax.text(v + vmax * 0.02, i, fmt(v), va="center", ha="left", fontfamily=SANS, fontsize=8, color=INK)
    return _png(fig)


def time_line(title: str, subtitle: str, days: list[date], values: list[float], fmt=lambda v: f"{v:,.0f}") -> bytes:
    """One series over time: 2px line, ~10% wash, end dot with its value, hairline horizontal grid."""
    height = 3.6
    fig = _figure(height, title, subtitle)
    ax = fig.add_axes((0.1, 0.42 / height, 0.82, 1 - 1.4 / height))
    _style(ax)
    ax.plot(days, values, color=SERIES, linewidth=2, solid_joinstyle="round", solid_capstyle="round")
    ax.fill_between(days, values, color=SERIES, alpha=0.10, linewidth=0)
    if days:
        ax.scatter([days[-1]], [values[-1]], s=40, color=SERIES, edgecolors=SURFACE, linewidths=2, zorder=3)
        ax.annotate(fmt(values[-1]), (days[-1], values[-1]), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontfamily=SANS, fontsize=8, color=INK)
    ax.set_ylim(0, max(values or [1]) * 1.2 or 1)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v)))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.tick_params(axis="x", which="both", length=0, pad=6)
    return _png(fig)
