"""Visual builder tests: shape normalisation and dispatch.

Pure-function level - these do not render, so they stay fast.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402

from services.video.scenes import (  # noqa: E402
    BUILDERS,
    _code_lines,
    _execution_steps,
    _plain_expression,
    build_visual,
)


# ---------------------------------------------------------------------------
# code_trace
# ---------------------------------------------------------------------------


def test_code_lines_accepts_a_list_or_a_blob():
    assert _code_lines({"lines": ["a", "b"]}) == ["a", "b"]
    assert _code_lines({"code": "a\nb"}) == ["a", "b"]
    assert _code_lines({}) == []


def test_execution_steps_accepts_bare_indices_and_objects():
    assert _execution_steps({"executionOrder": [0, 2]}, 3) == [
        {"line": 0, "note": ""},
        {"line": 2, "note": ""},
    ]
    steps = _execution_steps({"executionOrder": [{"line": 1, "note": "call"}]}, 3)
    assert steps == [{"line": 1, "note": "call"}]


def test_execution_steps_tolerates_one_based_numbering():
    """A human writing the fixture will reach for 1-based line numbers."""
    steps = _execution_steps({"executionOrder": [1, 2, 3]}, 3)
    assert [s["line"] for s in steps] == [0, 1, 2]


def test_execution_steps_drops_out_of_range_lines():
    steps = _execution_steps({"executionOrder": [0, 99, -5]}, 3)
    assert [s["line"] for s in steps] == [0]


def test_execution_steps_ignores_junk_entries():
    steps = _execution_steps({"executionOrder": ["nope", None, {"note": "no line"}, 1]}, 3)
    assert [s["line"] for s in steps] == [1]


def test_code_trace_is_dispatched_to_a_real_builder():
    """It used to fall through to the generic chip layout."""
    assert BUILDERS["code_trace"].__name__ == "build_code_trace"


def test_code_trace_builds_with_an_execution_order():
    mobject, animations = build_visual(
        {
            "type": "code_trace",
            "data": {
                "language": "python",
                "lines": ["def f(x):", "    return x", "print(f(1))"],
                "executionOrder": [
                    {"line": 0, "note": "define"},
                    {"line": 2, "note": "call"},
                    {"line": 1, "note": "body"},
                ],
            },
        }
    )
    assert mobject.submobjects
    assert animations


def test_code_trace_without_an_execution_order_still_renders_the_code():
    mobject, animations = build_visual(
        {"type": "code_trace", "data": {"lines": ["print(1)"]}}
    )
    assert mobject.submobjects
    assert animations


def test_code_trace_with_no_code_falls_back_cleanly():
    mobject, animations = build_visual({"type": "code_trace", "data": {}})
    assert mobject is not None
    assert animations


# ---------------------------------------------------------------------------
# diagram composites
# ---------------------------------------------------------------------------


def test_diagram_is_dispatched_to_the_composite_builder():
    assert BUILDERS["diagram"].__name__ == "build_diagram"


def test_repair_fixture_composite_does_not_fall_back():
    """demo-fixtures ships the repair scene as a rich `diagram` composite."""
    import json

    fixture = json.loads(
        (REPO_ROOT / "demo-fixtures" / "ohms-law-repair-scene.json").read_text(
            encoding="utf-8"
        )
    )
    mobject, animations = build_visual(fixture["visual"])
    # The fallback emits a single chip group; the composite emits equation rows
    # plus the analogy/graph column.
    assert len(mobject.submobjects) >= 2
    assert len(animations) >= 3


def test_plain_diagram_still_uses_the_chip_fallback():
    mobject, animations = build_visual(
        {"type": "diagram", "data": {"description": "a labelled cell"}}
    )
    assert mobject is not None
    assert animations


@pytest.mark.parametrize(
    "raw,expected",
    [
        ({"rawExpression": "I = V / R"}, "I = V / R"),
        ({"expression": r"\frac{V}{R}"}, "V / R"),
        ({"expression": r"V = I \cdot R"}, "V = I x R"),
        ({}, ""),
    ],
)
def test_latex_is_reduced_to_plain_text(raw, expected):
    """The renderer has no TeX install, so LaTeX would otherwise draw literally."""
    assert _plain_expression(raw) == expected


# ---------------------------------------------------------------------------
# Dispatch coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "visual_type",
    ["circuit", "equation", "graph", "concept_map", "diagram", "timeline", "code_trace"],
)
def test_every_contract_visual_type_builds_something(visual_type):
    """No contract visual type may raise, even with an empty payload."""
    mobject, animations = build_visual({"type": visual_type, "data": {}})
    assert mobject is not None
    assert isinstance(animations, list)


def test_an_unknown_visual_type_falls_back_rather_than_raising():
    mobject, animations = build_visual({"type": "hologram", "data": {"a": "b"}})
    assert mobject is not None


# ---------------------------------------------------------------------------
# timeline (History)
# ---------------------------------------------------------------------------


def test_timeline_is_dispatched_to_a_real_builder():
    assert BUILDERS["timeline"].__name__ == "build_timeline"


def test_timeline_events_accept_several_key_spellings():
    from services.video.scenes import _timeline_events

    assert _timeline_events({"events": [{"date": "1947", "label": "Independence"}]}) == [
        {"date": "1947", "label": "Independence"}
    ]
    # `year`/`title` and `when`/`event` are equally plausible authoring choices.
    assert _timeline_events({"items": [{"year": "1930", "title": "Salt March"}]}) == [
        {"date": "1930", "label": "Salt March"}
    ]
    assert _timeline_events({"points": [{"when": "1919", "event": "Bagh"}]}) == [
        {"date": "1919", "label": "Bagh"}
    ]


def test_timeline_accepts_bare_strings_and_ignores_junk():
    from services.video.scenes import _timeline_events

    events = _timeline_events({"events": ["Partition", None, 42, {"nothing": "here"}]})
    assert events == [{"date": "", "label": "Partition"}]


def test_timeline_caps_events_so_labels_cannot_collide():
    from services.video.scenes import _timeline_events

    many = [{"date": str(y), "label": f"e{y}"} for y in range(1900, 1920)]
    assert len(_timeline_events({"events": many})) == 6


def test_timeline_builds_with_events():
    mobject, animations = build_visual(
        {
            "type": "timeline",
            "data": {
                "title": "Independence",
                "events": [
                    {"date": "1857", "label": "First War"},
                    {"date": "1947", "label": "Independence"},
                ],
            },
        }
    )
    assert mobject.submobjects
    assert animations


def test_timeline_with_no_events_falls_back_cleanly():
    mobject, animations = build_visual({"type": "timeline", "data": {}})
    assert mobject is not None
    assert animations


# ---------------------------------------------------------------------------
# labelled diagram (Biology)
# ---------------------------------------------------------------------------


def test_diagram_parts_accept_several_key_spellings():
    from services.video.scenes import _diagram_parts

    assert _diagram_parts({"parts": [{"label": "Nucleus"}]}) == ["Nucleus"]
    assert _diagram_parts({"labels": ["Cell wall"]}) == ["Cell wall"]
    assert _diagram_parts({"elements": [{"name": "Vacuole"}]}) == ["Vacuole"]


def test_labelled_diagram_builds_leader_lines_for_each_part():
    mobject, animations = build_visual(
        {
            "type": "diagram",
            "data": {
                "title": "Plant cell",
                "parts": [{"label": "Nucleus"}, {"label": "Chloroplast"}],
            },
        }
    )
    assert mobject.submobjects
    # body, inner, title, leaders, captions
    assert len(mobject.submobjects) >= 4
    assert animations


def test_a_diagram_with_no_parts_still_falls_back():
    """A description-only diagram has nothing to label."""
    mobject, animations = build_visual(
        {"type": "diagram", "data": {"description": "just prose"}}
    )
    assert mobject is not None
    assert animations


def test_the_repair_composite_still_wins_over_the_labelled_path():
    """A composite must not be mistaken for a plain labelled diagram."""
    mobject, animations = build_visual(
        {
            "type": "diagram",
            "data": {
                "composite": True,
                "equation": {"steps": [{"rawExpression": "I = V / R", "title": "Ohm"}]},
                "analogy": {"diagramType": "hydraulic_analogy"},
            },
        }
    )
    assert mobject.submobjects
    assert animations


def test_no_contract_visual_type_is_left_on_the_generic_fallback():
    """Every type now has a purpose-built builder."""
    generic = {name for name, fn in BUILDERS.items() if fn.__name__ == "build_fallback"}
    assert generic == set(), f"still falling back: {generic}"
