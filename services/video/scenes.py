"""Manim scene construction for GuruFlow teaching videos.

One ``LessonVideoScene`` renders a single contract ``Scene`` into a lesson
frame: a header with the objective, a teacher panel, the animated subject
visual, and burned-in captions that track the narration.

Deliberately LaTeX-free. Manim's ``MathTex`` needs a TeX distribution, which we
cannot assume a judge has installed, so equations are typeset with Pango
``Text`` in a monospace face. Devanagari narration is rendered with a font that
actually has the glyphs, otherwise Hindi captions come out as tofu boxes.
"""

from __future__ import annotations

import re
from typing import Any

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Circle,
    Create,
    Dot,
    FadeIn,
    Line,
    PI,
    Rectangle,
    RoundedRectangle,
    Scene,
    Text,
    VGroup,
    Write,
    config,
)

# Palette lifted from the web client so video and UI look like one product.
BG = "#0f1117"
PANEL = "#171a23"
BORDER = "#2a2f3d"
TEXT = "#e8eaf0"
DIM = "#9aa3b8"
ACCENT = "#6c8cff"
GOOD = "#3ecf8e"
WARN = "#f5a524"
SKIN = "#c98f68"

MONO = "Consolas"
SANS = "Segoe UI"
# Windows ships Nirmala UI; Linux/macOS commonly have Noto. Manim falls back to
# a default face if none match, so list them in preference order.
DEVANAGARI_FONTS = ("Nirmala UI", "Noto Sans Devanagari", "Mangal")

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def _font_for(text: str) -> str:
    """Pick a face that can actually draw this string."""
    if _DEVANAGARI.search(text or ""):
        return DEVANAGARI_FONTS[0]
    return SANS


def label(text: str, size: int = 24, color: str = TEXT, font: str | None = None) -> Text:
    return Text(text, font_size=size, color=color, font=font or _font_for(text))


def _fit(mobject, max_width: float, max_height: float):
    """Scale a mobject down to fit a box; never scale up."""
    if mobject.width > max_width:
        mobject.scale_to_fit_width(max_width)
    if mobject.height > max_height:
        mobject.scale_to_fit_height(max_height)
    return mobject


# ---------------------------------------------------------------------------
# Shape normalisers - the planner and the fixtures describe visuals differently
# ---------------------------------------------------------------------------


def _steps(data: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for step in data.get("steps", []) or []:
        if isinstance(step, str):
            out.append({"expression": step, "label": ""})
        elif isinstance(step, dict):
            out.append(
                {
                    "expression": str(step.get("expression", "")),
                    "label": str(step.get("label", "")),
                }
            )
    return [s for s in out if s["expression"]]


def _components(data: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for component in data.get("components", []) or []:
        if isinstance(component, str):
            out.append({"type": component, "label": component})
        elif isinstance(component, dict):
            out.append(
                {
                    "type": str(component.get("type", "")),
                    "label": str(component.get("label", component.get("type", ""))),
                }
            )
    return out


def _nodes(data: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for index, node in enumerate(data.get("nodes", []) or []):
        if isinstance(node, str):
            out.append(
                {
                    "id": f"n{index}",
                    "label": node,
                    "type": "formula" if "=" in node else "concept",
                }
            )
        elif isinstance(node, dict):
            out.append(
                {
                    "id": str(node.get("id", f"n{index}")),
                    "label": str(node.get("label", "")),
                    "type": str(node.get("type", "concept")),
                }
            )
    return [n for n in out if n["label"]]


def _points(data: dict[str, Any]) -> list[tuple[float, float]]:
    raw = data.get("points")
    if not raw:
        series = (data.get("series") or [{}])[0]
        raw = series.get("points")
    if not raw:
        # Canonical I = V/R curve at V = 10 when a fixture only names the axes.
        return [(x, 10.0 / x) for x in (1, 2, 4, 6, 10, 16, 20)]
    pts = []
    for point in raw:
        try:
            pts.append((float(point["x"]), float(point["y"])))
        except (KeyError, TypeError, ValueError):
            continue
    return pts or [(x, 10.0 / x) for x in (1, 2, 4, 6, 10, 16, 20)]


def _axis_label(axis: Any, fallback: str) -> str:
    if isinstance(axis, str):
        return axis
    if isinstance(axis, dict):
        return str(axis.get("label", fallback))
    return fallback


# ---------------------------------------------------------------------------
# Visual builders - each returns (mobject, [animations])
# ---------------------------------------------------------------------------


def build_equation(data: dict[str, Any]):
    steps = _steps(data)
    # Repair scenes pair the equation with an analogy and a graph, so the rows
    # have to give up width to keep the composite readable.
    has_extras = bool(data.get("analogy") or data.get("graph"))
    row_width = 5.3 if has_extras else 6.6
    rows = VGroup()
    for index, step in enumerate(steps):
        box = RoundedRectangle(
            corner_radius=0.12, width=row_width, height=0.92,
            stroke_color=ACCENT if index == len(steps) - 1 else BORDER,
            stroke_width=2,
            fill_color=PANEL, fill_opacity=1,
        )
        expr = Text(step["expression"], font_size=26 if has_extras else 30,
                    color=TEXT, font=MONO)
        expr.move_to(box.get_left() + RIGHT * (expr.width / 2 + 0.35))
        group = VGroup(box, expr)
        if step["label"]:
            note = label(step["label"], 15, DIM)
            note.move_to(box.get_right() + LEFT * (note.width / 2 + 0.3))
            group.add(note)
        rows.add(group)
    rows.arrange(DOWN, buff=0.28)

    extras = VGroup()
    if data.get("analogy") == "water-pipe":
        extras.add(_water_pipe())
    if data.get("graph"):
        graph, _ = build_graph(data["graph"])
        graph.scale(0.78)
        extras.add(graph)

    if len(extras):
        extras.arrange(DOWN, buff=0.45)
        content = VGroup(rows, extras).arrange(RIGHT, buff=0.85)
    else:
        content = rows

    animations = [Write(row, run_time=0.55) for row in rows]
    if len(extras):
        animations.append(FadeIn(extras, shift=UP * 0.2, run_time=0.6))
    return content, animations


def _water_pipe() -> VGroup:
    """Wide pipe with fast flow beside a narrow pipe with slow flow."""
    group = VGroup()
    wide = Rectangle(width=2.6, height=0.85, stroke_color=ACCENT, stroke_width=3,
                     fill_color=PANEL, fill_opacity=1)
    narrow = Rectangle(width=2.6, height=0.34, stroke_color=WARN, stroke_width=3,
                       fill_color=PANEL, fill_opacity=1)
    wide_label = label("low R - high I", 15, ACCENT)
    narrow_label = label("high R - low I", 15, WARN)
    left = VGroup(wide, wide_label).arrange(DOWN, buff=0.14)
    right = VGroup(narrow, narrow_label).arrange(DOWN, buff=0.14)
    group.add(VGroup(left, right).arrange(DOWN, buff=0.4))

    for pipe, colour, count in ((wide, ACCENT, 3), (narrow, WARN, 1)):
        for i in range(count):
            dot = Dot(radius=0.07, color=colour)
            dot.move_to(pipe.get_left() + RIGHT * (0.4 + i * 0.7))
            group.add(dot)
    return group


def build_graph(data: dict[str, Any]):
    points = _points(data)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_max = max(ys) or 1.0

    width, height = 5.4, 3.4
    # Build everything off one explicit origin so the axes actually meet.
    origin_point = LEFT * (width / 2) + DOWN * (height / 2)

    x_axis = Line(origin_point, origin_point + RIGHT * width,
                  stroke_color=BORDER, stroke_width=3)
    y_axis = Line(origin_point, origin_point + UP * height,
                  stroke_color=BORDER, stroke_width=3)

    def to_point(x: float, y: float):
        return (
            origin_point
            + RIGHT * ((x - x_min) / (x_max - x_min or 1) * width)
            + UP * (min(y, y_max) / y_max * height)
        )

    curve = VGroup(*[
        Line(to_point(*points[i]), to_point(*points[i + 1]),
             stroke_color=ACCENT, stroke_width=5)
        for i in range(len(points) - 1)
    ])
    markers = VGroup(*[Dot(to_point(*p), radius=0.08, color=ACCENT) for p in points])

    x_name = label(_axis_label(data.get("xAxis"), "Resistance"), 18, DIM)
    x_name.next_to(x_axis, DOWN, buff=0.25)
    y_name = label(_axis_label(data.get("yAxis"), "Current"), 18, DIM)
    y_name.rotate(PI / 2).next_to(y_axis, LEFT, buff=0.2)

    group = VGroup(x_axis, y_axis, curve, markers, x_name, y_name)

    title_text = data.get("title") or data.get("caption")
    if title_text:
        title = label(str(title_text), 20, TEXT)
        title.next_to(group, UP, buff=0.28)
        group.add(title)

    animations = [
        Create(VGroup(x_axis, y_axis), run_time=0.5),
        Create(curve, run_time=1.2),
        FadeIn(markers, run_time=0.4),
        FadeIn(VGroup(x_name, y_name), run_time=0.3),
    ]
    return group, animations


def build_circuit(data: dict[str, Any]):
    """Circuit loop with a battery, a load, and charge actually moving round it.

    The moving dots are driven by a dt-based updater rather than a played
    animation so the current keeps flowing for the whole scene instead of
    stopping once the intro animations finish.
    """
    components = _components(data)
    highlight = data.get("highlight", "")
    group = VGroup()

    live = highlight == "current-flow"
    loop = Rectangle(
        width=4.9, height=2.7,
        stroke_color=ACCENT if live else DIM,
        stroke_width=6 if live else 4,
    )
    group.add(loop)

    # --- battery, on the left rail ---------------------------------------
    battery_active = highlight == "battery"
    battery_colour = WARN if battery_active else TEXT
    long_plate = Line(UP * 0.34, DOWN * 0.34, stroke_color=battery_colour, stroke_width=8)
    short_plate = Line(UP * 0.16, DOWN * 0.16, stroke_color=battery_colour, stroke_width=8)
    long_plate.move_to(loop.get_left() + UP * 0.22)
    short_plate.move_to(loop.get_left() + DOWN * 0.22)
    plus = label("+", 22, battery_colour)
    plus.next_to(long_plate, LEFT, buff=0.14)

    battery = next((c for c in components if c["type"] == "battery"), None)
    battery_label = label(battery["label"] if battery else "Battery", 18,
                          WARN if battery_active else DIM)
    battery_label.next_to(loop.get_left(), LEFT, buff=0.55)
    group.add(long_plate, short_plate, plus, battery_label)

    # --- load, on the right rail -----------------------------------------
    load = next(
        (c for c in components if c["type"] in ("resistor", "bulb")),
        {"type": "bulb", "label": "Bulb"},
    )
    load_active = highlight in ("resistor", "bulb")
    load_colour = WARN if load_active else TEXT

    if load["type"] == "resistor":
        top = loop.get_right() + UP * 0.75
        pts = [top]
        for i in range(6):
            pts.append(
                top + DOWN * (0.25 * (i + 1)) + (RIGHT if i % 2 == 0 else LEFT) * 0.26
            )
        pts.append(top + DOWN * 1.6)
        shape = VGroup(*[
            Line(pts[i], pts[i + 1], stroke_color=load_colour, stroke_width=5)
            for i in range(len(pts) - 1)
        ])
    else:
        bulb = Circle(radius=0.42, stroke_color=load_colour, stroke_width=5)
        bulb.move_to(loop.get_right())
        centre = bulb.get_center()
        shape = VGroup(
            bulb,
            Line(centre + UP * 0.3 + LEFT * 0.3, centre + DOWN * 0.3 + RIGHT * 0.3,
                 stroke_color=load_colour, stroke_width=3),
            Line(centre + UP * 0.3 + RIGHT * 0.3, centre + DOWN * 0.3 + LEFT * 0.3,
                 stroke_color=load_colour, stroke_width=3),
        )
    group.add(shape)

    # Sit the label clear of the symbol rather than on top of it.
    load_label = label(load["label"], 18, WARN if load_active else DIM)
    load_label.next_to(shape, RIGHT, buff=0.3)
    group.add(load_label)

    # --- flowing charge ---------------------------------------------------
    if live:
        for index in range(4):
            dot = Dot(radius=0.09, color=ACCENT)
            dot.phase = index / 4.0
            dot.move_to(loop.point_from_proportion(dot.phase))

            def drift(mob, dt):
                mob.phase = (mob.phase + dt * 0.16) % 1.0
                mob.move_to(loop.point_from_proportion(mob.phase))

            dot.add_updater(drift)
            group.add(dot)

    annotations = data.get("annotations") or []
    if annotations:
        note = label(str(annotations[0]), 16, DIM)
        note.next_to(loop, DOWN, buff=0.32)
        group.add(note)

    animations = [Create(loop, run_time=0.9), FadeIn(group, run_time=0.5)]
    return group, animations


def build_concept_map(data: dict[str, Any]):
    nodes = _nodes(data)
    formulas = [n for n in nodes if n["type"] == "formula"]
    concepts = [n for n in nodes if n["type"] != "formula"]
    group = VGroup()

    top = None
    if formulas:
        text = Text(formulas[0]["label"], font_size=26, color=ACCENT, font=MONO)
        box = RoundedRectangle(
            corner_radius=0.12, width=max(3.2, text.width + 0.8), height=0.95,
            stroke_color=ACCENT, stroke_width=2.5, fill_color=PANEL, fill_opacity=1,
        )
        top = VGroup(box, text)
        top.move_to(UP * 1.55)
        group.add(top)

    row = VGroup()
    for node in concepts:
        text = label(node["label"], 20, TEXT)
        box = RoundedRectangle(
            corner_radius=0.1, width=max(2.0, text.width + 0.6), height=0.8,
            stroke_color=BORDER, stroke_width=2, fill_color=PANEL, fill_opacity=1,
        )
        row.add(VGroup(box, text))
    if len(row):
        row.arrange(RIGHT, buff=0.4).move_to(DOWN * 1.35)
        group.add(row)

    edges = VGroup()
    if top is not None:
        for child in row:
            edges.add(
                Line(top.get_bottom(), child.get_top(), stroke_color=BORDER, stroke_width=2)
            )
        group.add(edges)

    animations = []
    if top is not None:
        animations.append(FadeIn(top, shift=DOWN * 0.2, run_time=0.5))
    if len(edges):
        animations.append(Create(edges, run_time=0.5))
    if len(row):
        animations.append(FadeIn(row, shift=UP * 0.2, run_time=0.6))
    return group, animations


def build_fallback(data: dict[str, Any]):
    chips = VGroup()
    values = [v for v in data.values() if isinstance(v, str)][:5]
    for value in values or ["Lesson visual"]:
        text = label(value, 20, TEXT)
        box = RoundedRectangle(
            corner_radius=0.1, width=max(2.4, text.width + 0.6), height=0.8,
            stroke_color=BORDER, stroke_width=2, fill_color=PANEL, fill_opacity=1,
        )
        chips.add(VGroup(box, text))
    chips.arrange(DOWN, buff=0.3)
    return chips, [FadeIn(chips, run_time=0.7)]


BUILDERS = {
    "equation": build_equation,
    "graph": build_graph,
    "circuit": build_circuit,
    "concept_map": build_concept_map,
    "diagram": build_fallback,
    "timeline": build_fallback,
    "code_trace": build_fallback,
}


def build_visual(spec: dict[str, Any]):
    builder = BUILDERS.get((spec or {}).get("type", ""), build_fallback)
    return builder((spec or {}).get("data", {}) or {})


# ---------------------------------------------------------------------------
# Teacher figure
# ---------------------------------------------------------------------------


def build_teacher() -> tuple[VGroup, VGroup]:
    """Simple, on-brand teacher. Returns (figure, mouth) so the mouth can move."""
    head = Circle(radius=0.62, stroke_width=0, fill_color=SKIN, fill_opacity=1)
    hair = Circle(radius=0.64, stroke_width=0, fill_color="#2b2f3d", fill_opacity=1)
    hair.move_to(head.get_center() + UP * 0.22)
    left_eye = Dot(head.get_center() + LEFT * 0.22 + UP * 0.08, radius=0.062, color="#23272f")
    right_eye = Dot(head.get_center() + RIGHT * 0.22 + UP * 0.08, radius=0.062, color="#23272f")
    mouth = RoundedRectangle(
        corner_radius=0.05, width=0.34, height=0.09,
        stroke_width=0, fill_color="#6b3b30", fill_opacity=1,
    )
    mouth.move_to(head.get_center() + DOWN * 0.3)

    body = RoundedRectangle(
        corner_radius=0.28, width=1.7, height=1.15,
        stroke_width=0, fill_color=ACCENT, fill_opacity=1,
    )
    body.next_to(head, DOWN, buff=-0.12)

    figure = VGroup(body, hair, head, left_eye, right_eye, mouth)
    return figure, mouth


class LessonVideoScene(Scene):
    """Renders one contract Scene. Payload is injected as a class attribute."""

    payload: dict[str, Any] = {}

    def construct(self) -> None:
        data = self.payload
        objective: str = data.get("objective", "")
        visual_spec: dict[str, Any] = data.get("visual", {}) or {}
        captions: list[dict[str, Any]] = data.get("captions", []) or []
        duration: float = float(data.get("duration", 8.0))
        grounded: bool = bool(data.get("grounded", False))
        is_repair: bool = bool(data.get("isRepair", False))
        citation: str = data.get("citation", "")

        self.camera.background_color = BG
        half_w = config.frame_width / 2
        half_h = config.frame_height / 2

        # ---- Header -----------------------------------------------------
        mark = RoundedRectangle(
            corner_radius=0.1, width=0.62, height=0.62,
            stroke_width=0, fill_color=ACCENT, fill_opacity=1,
        )
        mark_text = Text("GF", font_size=20, color="#ffffff", font=SANS)
        mark_text.move_to(mark.get_center())
        brand = VGroup(mark, mark_text)

        title = label(objective, 24, TEXT)
        _fit(title, half_w * 1.05, 0.6)

        header = VGroup(brand, title).arrange(RIGHT, buff=0.35)
        header.to_corner(UP + LEFT, buff=0.45)

        badge_text = "REPAIR" if is_repair else ("SOURCE-GROUNDED" if grounded else "GENERAL KNOWLEDGE")
        badge_colour = WARN if (is_repair or not grounded) else GOOD
        badge_label = Text(badge_text, font_size=15, color=badge_colour, font=SANS)
        badge = RoundedRectangle(
            corner_radius=0.16, width=badge_label.width + 0.5, height=0.46,
            stroke_color=badge_colour, stroke_width=1.5,
            fill_color=PANEL, fill_opacity=1,
        )
        badge_label.move_to(badge.get_center())
        badge_group = VGroup(badge, badge_label).to_corner(UP + RIGHT, buff=0.45)

        rule = Line(
            LEFT * (half_w - 0.4), RIGHT * (half_w - 0.4),
            stroke_color=BORDER, stroke_width=2,
        ).move_to(UP * (half_h - 1.15))

        self.add(header, badge_group, rule)

        # ---- Teacher panel ----------------------------------------------
        teacher, mouth = build_teacher()
        panel = RoundedRectangle(
            corner_radius=0.2, width=3.0, height=3.5,
            stroke_color=BORDER, stroke_width=2, fill_color=PANEL, fill_opacity=1,
        )
        teacher.scale(0.95).move_to(panel.get_center() + UP * 0.1)
        name = label("GuruFlow Teacher", 16, DIM)
        name.next_to(panel.get_bottom(), UP, buff=0.22)
        teacher_panel = VGroup(panel, teacher, name)
        teacher_panel.move_to(LEFT * (half_w - 2.15) + DOWN * 0.15)
        self.add(teacher_panel)

        # Mouth movement so the teacher reads as speaking rather than frozen.
        base_height = mouth.height

        def animate_mouth(mob, dt):
            import math

            t = self.renderer.time
            scale = 1.0 + 0.85 * abs(math.sin(t * 6.5))
            mob.stretch_to_fit_height(base_height * scale)

        mouth.add_updater(animate_mouth)

        # ---- Caption band ------------------------------------------------
        caption_holder = VGroup()
        self.add(caption_holder)
        caption_state = {"index": -2}
        caption_y = -(half_h - 0.85)

        def make_caption(text: str) -> VGroup:
            body = label(text, 26, TEXT)
            _fit(body, config.frame_width - 3.0, 0.8)
            plate = RoundedRectangle(
                corner_radius=0.14,
                width=min(config.frame_width - 1.2, body.width + 1.0),
                height=body.height + 0.55,
                stroke_color=BORDER, stroke_width=1.5,
                fill_color="#1e222d", fill_opacity=1,
            )
            body.move_to(plate.get_center())
            return VGroup(plate, body).move_to([0, caption_y, 0])

        def update_caption(mob, dt):
            now = self.renderer.time
            index = -1
            for i, line in enumerate(captions):
                if line["start"] <= now < line["end"]:
                    index = i
                    break
            if index != caption_state["index"]:
                caption_state["index"] = index
                mob.become(make_caption(captions[index]["text"]) if index >= 0 else VGroup())

        caption_holder.add_updater(update_caption)

        # ---- Subject visual ----------------------------------------------
        visual, animations = build_visual(visual_spec)
        _fit(visual, 9.6, 4.35)
        visual.move_to(RIGHT * 1.85 + UP * 0.3)

        if citation:
            source = label(citation, 15, DIM)
            source.next_to(visual, DOWN, buff=0.3)
            _fit(source, 8.0, 0.4)
            self.add(source)

        # ---- Timeline ------------------------------------------------------
        self.play(FadeIn(header, run_time=0.4))
        spent = 0.4
        for animation in animations:
            run_time = getattr(animation, "run_time", 0.6)
            if spent + run_time > duration - 0.4:
                break
            self.play(animation)
            spent += run_time

        # Anything that did not get its own animation still has to appear.
        self.add(visual)

        remaining = max(0.3, duration - spent)
        self.wait(remaining)
        mouth.clear_updaters()
        caption_holder.clear_updaters()
