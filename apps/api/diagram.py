"""Render lesson visuals (circuit, equation, graph, concept map, water-pipe
analogy) as real PNG diagrams using matplotlib.

This is a deterministic, dependency-light renderer so a judge can *see* the
visual a scene calls for, rather than only receiving a spec object. It lives in
the API scope (Person 2) because scenes are planned here; the frontend may use
the PNG URL as the scene's visual source.

Kept small and side-effect free: each call draws to an in-memory buffer.
"""

from __future__ import annotations

import io
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless, no display required
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle  # noqa: E402

_STYLE = {
    "figure_bg": "#ffffff",
    "accent": "#2563eb",
    "accent2": "#059669",
    "text": "#111827",
    "grid": "#e5e7eb",
}


def render_diagram(visual: dict[str, Any], size: tuple[int, int] = (640, 360)) -> bytes:
    """Render a visual spec to PNG bytes.

    ``visual`` mirrors the scene ``visual`` object (``{"type": ...}`` plus any
    type-specific data). Unknown types render a labelled placeholder card so
    the endpoint never 500s on a new spec.
    """
    vtype = (visual or {}).get("type", "concept_map")
    renderers = {
        "circuit": _render_circuit,
        "equation": _render_equation,
        "graph": _render_graph,
        "concept_map": _render_concept_map,
        "water_pipe_analogy": _render_water_pipe,
    }
    fn = renderers.get(vtype, _render_placeholder)
    buf = io.BytesIO()
    try:
        fn(visual or {}, size)
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor=_STYLE["figure_bg"])
    finally:
        plt.close("all")
    return buf.getvalue()


def _title(ax: Any, text: str) -> None:
    ax.set_title(text, color=_STYLE["text"], fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _render_circuit(visual: dict[str, Any], size: tuple[int, int]) -> None:
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100))
    _title(ax, visual.get("title", "Simple Circuit (V = I × R)"))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal", adjustable="box")
    # Battery on the left
    ax.plot([1, 1], [3.7, 4.6], color=_STYLE["accent"], lw=3)
    ax.plot([1, 1], [1.4, 2.3], color=_STYLE["accent"], lw=5)
    ax.text(0.55, 3.2, "+V", color=_STYLE["text"], fontsize=11, fontweight="bold")
    # Resistor on the right (zig-zag)
    x = [7.2, 7.5, 7.9, 8.3, 8.7, 9.1, 9.5]
    y = [2.3, 3.7, 2.3, 3.7, 2.3, 3.7, 2.3]
    ax.plot(x, y, color=_STYLE["accent2"], lw=2.5)
    ax.text(8.4, 4.3, "R", color=_STYLE["text"], fontsize=12, fontweight="bold")
    # Wires connecting elements
    ax.plot([1, 1], [2.3, 1.8], color=_STYLE["text"], lw=2)
    ax.plot([1, 9.5], [1.8, 1.8], color=_STYLE["text"], lw=2)
    ax.plot([1, 9.5], [4.4, 4.4], color=_STYLE["text"], lw=2)
    ax.plot([9.5, 9.5], [2.3, 4.4], color=_STYLE["text"], lw=2)
    ax.plot([1, 1], [4.6, 5.2], color=_STYLE["text"], lw=2)
    ax.plot([1, 9.5], [5.2, 5.2], color=_STYLE["text"], lw=2)
    ax.plot([9.5, 9.5], [5.2, 4.4], color=_STYLE["text"], lw=2)
    # Ammeter in series + arrow for current direction
    ax.add_patch(Circle((5.0, 1.8), 0.55, fill=False, edgecolor=_STYLE["accent"], lw=2))
    ax.text(5.0, 1.8, "A", ha="center", va="center", color=_STYLE["accent"], fontweight="bold")
    ax.add_patch(FancyArrowPatch((1.5, 5.2), (4.8, 5.2), color=_STYLE["accent2"],
                                 arrowstyle="->", mutation_scale=22, lw=2.5))
    ax.text(3.1, 5.45, "I (amperes)", color=_STYLE["accent2"], fontsize=10, ha="center")


def _render_equation(visual: dict[str, Any], size: tuple[int, int]) -> None:
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100))
    _title(ax, visual.get("title", "Ohm's Law"))
    ax.text(0.5, 0.55, "V = I × R", ha="center", va="center", color=_STYLE["accent"],
            fontsize=34, fontweight="bold", transform=ax.transAxes)
    ax.text(0.5, 0.22, "Current  I = V ÷ R", ha="center", va="center",
            color=_STYLE["text"], fontsize=15, transform=ax.transAxes)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def _render_graph(visual: dict[str, Any], size: tuple[int, int]) -> None:
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100))
    _title(ax, visual.get("title", "I vs V (constant R)"))
    v = [0, 1, 2, 3, 4, 5]
    i = [0, 0.5, 1.0, 1.5, 2.0, 2.5]
    ax.plot(v, i, color=_STYLE["accent"], lw=2.5, marker="o")
    ax.set_xlabel("Voltage (V)")
    ax.set_ylabel("Current (A)")
    ax.grid(color=_STYLE["grid"], lw=1)
    ax.text(3.0, 2.1, "straight line →", color=_STYLE["accent2"], fontsize=11)


def _render_concept_map(visual: dict[str, Any], size: tuple[int, int]) -> None:
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100))
    _title(ax, visual.get("title", "Electricity concepts"))
    nodes = visual.get("nodes") or ["Voltage", "Current", "Resistance"]
    cx, cy = 5, 3
    shown = nodes[:6]
    ax.add_patch(Circle((cx, cy), 1.5, facecolor=_STYLE["accent"], alpha=0.15,
                        edgecolor=_STYLE["accent"], lw=2))
    ax.text(cx, cy, "Ohm's Law", ha="center", va="center", color=_STYLE["accent"],
            fontweight="bold", fontsize=12)
    for idx, label in enumerate(shown):
        angle = idx * (360 / len(shown))
        x = cx + 4.2 * __import__("math").cos(__import__("math").radians(angle))
        y = cy + 3.0 * __import__("math").sin(__import__("math").radians(angle))
        ax.add_patch(FancyArrowPatch((cx + 1.6 * __import__("math").cos(__import__("math").radians(angle)),
                                      cy + 1.2 * __import__("math").sin(__import__("math").radians(angle))),
                                     (x - 0.8 * __import__("math").cos(__import__("math").radians(angle)),
                                      y - 0.6 * __import__("math").sin(__import__("math").radians(angle))),
                                     color=_STYLE["grid"], arrowstyle="-", lw=1))
        ax.add_patch(Rectangle((x - 1.0, y - 0.35), 2.0, 0.7, facecolor=_STYLE["accent2"],
                               alpha=0.12, edgecolor=_STYLE["accent2"], lw=1.5))
        ax.text(x, y, label, ha="center", va="center", color=_STYLE["text"], fontsize=10)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal", adjustable="box")


def _render_water_pipe(visual: dict[str, Any], size: tuple[int, int]) -> None:
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100))
    _title(ax, visual.get("title", "Water-pipe analogy"))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.set_aspect("equal", adjustable="box")
    # Two pipes: wide (low resistance) and narrow (high resistance)
    ax.add_patch(Rectangle((1.0, 1.6), 4.5, 1.6, facecolor="#bfdbfe",
                           edgecolor=_STYLE["accent"], lw=2))
    ax.add_patch(Rectangle((1.0, 3.4), 4.5, 0.7, facecolor=_STYLE["accent"],
                           alpha=0.5))
    ax.text(2.9, 2.45, "wide pipe = low resistance", ha="center", va="center",
            color=_STYLE["text"], fontsize=10)
    ax.add_patch(Rectangle((6.5, 1.6), 2.2, 0.8, facecolor="#fecaca",
                           edgecolor=_STYLE["accent2"], lw=2))
    ax.add_patch(Rectangle((6.5, 2.5), 2.2, 0.7, fill=True, color=_STYLE["accent2"],
                           alpha=0.5))
    ax.text(7.6, 1.15, "narrow pipe = high resistance", ha="center", va="center",
            color=_STYLE["text"], fontsize=10)


def _render_placeholder(visual: dict[str, Any], size: tuple[int, int]) -> None:
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100))
    _title(ax, visual.get("type", "visual"))
    ax.text(0.5, 0.5, visual.get("title", "Visual"), ha="center", va="center",
            color=_STYLE["text"], fontsize=18, transform=ax.transAxes)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
