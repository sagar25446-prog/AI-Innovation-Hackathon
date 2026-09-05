"""Tests for voice synthesis, teaching-video generation and follow-up Q&A.

Anything that needs the network or a multi-second Manim render is marked slow
and skipped by default, so the core suite stays fast and offline. Run the full
set with:

    pytest apps/api/tests -q -m "slow or not slow"
"""

from __future__ import annotations

import os
import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apps.api.main import app, repository  # noqa: E402
from services import video as video_service  # noqa: E402
from services.evaluation import DIRECT_PROPORTIONALITY, build_repair_scene  # noqa: E402
from services.ingestion import ingest_topic  # noqa: E402
from services.qa import answer_question  # noqa: E402
from services.voice import SpeechResult, caption_lines, estimate_duration  # noqa: E402

RUN_SLOW = os.environ.get("GURUFLOW_RUN_SLOW_TESTS") == "1"
slow = pytest.mark.skipif(not RUN_SLOW, reason="set GURUFLOW_RUN_SLOW_TESTS=1")


@pytest.fixture
def client():
    repository.reset()
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Captions
# ---------------------------------------------------------------------------


def test_captions_split_long_narration_into_readable_lines():
    text = " ".join(["word"] * 60)
    result = SpeechResult(audio=b"", duration_seconds=20.0, provider="none")
    lines = caption_lines(result, text, max_chars=40)

    assert len(lines) > 1
    assert all(len(line["text"]) <= 45 for line in lines)
    # Monotonic, gap-free and covering the whole clip.
    assert lines[0]["start"] == pytest.approx(0.0, abs=0.01)
    assert lines[-1]["end"] == pytest.approx(20.0, abs=0.01)
    for earlier, later in zip(lines, lines[1:]):
        assert earlier["end"] <= later["start"] + 0.001


def test_captions_subdivide_a_sentence_level_boundary():
    """edge-tts gives Indian voices one SentenceBoundary for a whole sentence."""
    text = "Ohm's Law kehta hai ki V = I x R aur agar I nikalna ho toh I = V/R hota hai"
    result = SpeechResult(
        audio=b"",
        duration_seconds=10.0,
        provider="edge-tts",
        word_boundaries=[{"text": text, "start": 0.0, "end": 10.0}],
    )
    lines = caption_lines(result, text, max_chars=40)
    assert len(lines) > 1, "a long sentence boundary must still be broken up"
    assert lines[-1]["end"] == pytest.approx(10.0, abs=0.01)


def test_caption_lines_handles_empty_narration():
    assert caption_lines(SpeechResult(b"", 0.0, "none"), "") == []


def test_duration_estimate_is_positive():
    assert estimate_duration("") == 1.0
    assert estimate_duration("one two three four five") > 1.0


# ---------------------------------------------------------------------------
# Video service
# ---------------------------------------------------------------------------


def test_video_id_is_stable_and_content_addressed():
    scene = {
        "narration": "Current flows",
        "objective": "Explain current",
        "visual": {"type": "circuit", "data": {}},
        "durationSeconds": 30,
    }
    first = video_service.video_id(scene, "hinglish")
    assert first == video_service.video_id(dict(scene), "hinglish")

    # Language and narration both change the rendered output.
    assert first != video_service.video_id(scene, "english")
    changed = dict(scene, narration="Current does not flow")
    assert first != video_service.video_id(changed, "hinglish")


def test_video_status_is_absent_before_any_render():
    assert video_service.get_status("does-not-exist-at-all") == "absent"


def test_video_render_endpoint_rejects_a_missing_scene(client):
    assert client.post("/video/render", json={}).status_code in (400, 503)


def test_serving_an_unrendered_video_is_404(client):
    assert client.get("/video/nope.mp4").status_code == 404


def test_health_reports_video_capability(client):
    body = client.get("/health").json()
    assert "video" in body
    assert set(body["video"]) >= {"available", "quality", "videos"}


# ---------------------------------------------------------------------------
# Follow-up questions
# ---------------------------------------------------------------------------


def test_followup_answer_is_grounded_with_citations():
    material = ingest_topic("Ohm's Law")
    result = answer_question(
        "what happens to the current when resistance increases?",
        material.sections,
        material.document_id,
        language="english",
    )
    assert result["grounded"] is True
    assert result["citations"]
    assert result["citations"][0]["pageOrSlide"] >= 1


def test_followup_refuses_to_answer_off_material_questions():
    """The whole point of grounding: no answer beats a fabricated one."""
    material = ingest_topic("Ohm's Law")
    result = answer_question(
        "who won the 1998 football world cup?",
        material.sections,
        material.document_id,
        language="english",
    )
    assert result["grounded"] is False
    assert result["citations"] == []
    assert "could not find" in result["answer"].lower()


@pytest.mark.parametrize("language", ["english", "hindi", "hinglish"])
def test_followup_answers_in_the_learners_language(language):
    material = ingest_topic("Ohm's Law")
    result = answer_question(
        "what is resistance?", material.sections, material.document_id, language=language
    )
    assert result["answer"].strip()


def test_ask_endpoint_end_to_end(client):
    plan = client.post(
        "/lessons/plan",
        json={
            "learner": {
                "level": "beginner",
                "language": "hinglish",
                "availableMinutes": 20,
                "goal": "Understand Ohm's Law",
            },
            "topic": "Ohm's Law",
        },
    ).json()

    response = client.post(
        f"/lessons/{plan['id']}/ask",
        json={"question": "does current fall when resistance rises?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["citations"]


def test_ask_endpoint_validates_input(client):
    plan = client.post(
        "/lessons/plan",
        json={
            "learner": {
                "level": "beginner",
                "language": "english",
                "availableMinutes": 5,
                "goal": "g",
            }
        },
    ).json()
    assert client.post(f"/lessons/{plan['id']}/ask", json={"question": "  "}).status_code == 400
    assert client.post("/lessons/missing/ask", json={"question": "x"}).status_code == 404


# ---------------------------------------------------------------------------
# Slow: real renders
# ---------------------------------------------------------------------------


@slow
def test_repair_scene_renders_to_a_playable_video():
    from services.ffmpeg_util import probe_duration

    scene = build_repair_scene(DIRECT_PROPORTIONALITY, "hinglish")
    result = video_service.render_scene_video(scene, "hinglish")

    assert result.ready, f"render failed: {result.detail}"
    assert result.path.stat().st_size > 10_000
    duration = probe_duration(result.path)
    assert duration and duration > 3


# ---------------------------------------------------------------------------
# Female voice
# ---------------------------------------------------------------------------


def test_teacher_uses_female_neural_voices():
    """The GuruFlow teacher is female; these are the verified female voices."""
    from services.voice import VOICE_MAP

    assert VOICE_MAP["english"] == "en-IN-NeerjaNeural"
    assert VOICE_MAP["hindi"] == "hi-IN-SwaraNeural"
    assert VOICE_MAP["hinglish"] == "hi-IN-SwaraNeural"

    # Odia and Punjabi map to None on purpose: edge-tts has no voice for them,
    # so they fall back to gTTS or captions. Joining the raw values therefore
    # raises TypeError - filter before joining.
    configured = [voice for voice in VOICE_MAP.values() if voice]
    assert len(configured) == len(VOICE_MAP) - 2

    # The old male voices must not creep back in, in any language.
    joined = "".join(configured)
    assert "Madhur" not in joined
    assert "Prabhat" not in joined

    # Every configured voice is a real BCP-47 neural voice id.
    for language, voice in VOICE_MAP.items():
        if voice:
            assert re.match(r"^[a-z]{2}-[A-Z]{2}-\w+Neural$", voice), (
                f"{language} has a malformed voice id: {voice}"
            )


# ---------------------------------------------------------------------------
# Talking head
# ---------------------------------------------------------------------------


def test_talking_head_is_off_and_harmless_by_default(monkeypatch):
    from services.video import talking_head

    for key in (
        "GURUFLOW_TALKING_HEAD",
        "GURUFLOW_SADTALKER_DIR",
        "GURUFLOW_TEACHER_PORTRAIT",
    ):
        monkeypatch.delenv(key, raising=False)

    assert talking_head.available() is False
    assert talking_head.generate(Path("nonexistent.mp3"), Path(".")) is None


def test_talking_head_reports_what_is_missing(monkeypatch):
    from services.video import talking_head

    monkeypatch.setenv("GURUFLOW_TALKING_HEAD", "1")
    monkeypatch.delenv("GURUFLOW_SADTALKER_DIR", raising=False)
    monkeypatch.delenv("GURUFLOW_TEACHER_PORTRAIT", raising=False)

    problems = talking_head.config().problems()
    assert any("SADTALKER_DIR" in p for p in problems)
    assert any("TEACHER_PORTRAIT" in p for p in problems)
    assert "GURUFLOW_TALKING_HEAD" not in " ".join(problems)


def test_talking_head_status_carries_the_rights_notice():
    from services.video import talking_head

    status = talking_head.status()
    assert "rights" in status["portraitRights"].lower()
    assert "consent" in status["portraitRights"].lower()


def test_talking_head_changes_the_video_id(monkeypatch):
    """A composited photoreal head is a different video from a drawn one."""
    from services.video import talking_head

    scene = {
        "narration": "Current flows",
        "objective": "Explain current",
        "visual": {"type": "circuit", "data": {}},
        "durationSeconds": 30,
    }
    monkeypatch.setattr(talking_head, "available", lambda: False)
    drawn = video_service.video_id(scene, "hinglish")
    monkeypatch.setattr(talking_head, "available", lambda: True)
    composited = video_service.video_id(scene, "hinglish")
    assert drawn != composited


def test_teacher_panel_rect_is_inside_the_frame_and_h264_safe():
    from services.video.scenes import teacher_panel_rect

    for width, height in ((854, 480), (1280, 720), (1920, 1080)):
        x, y, w, h = teacher_panel_rect(width, height)
        assert 0 <= x and 0 <= y
        assert x + w <= width and y + h <= height
        # H.264 requires even dimensions.
        assert w % 2 == 0 and h % 2 == 0
        # The panel scales with the frame, so it stays roughly a fifth wide.
        assert 0.15 < w / width < 0.28


def test_sadtalker_defaults_suit_a_6gb_card():
    """crop + 256 is the low-VRAM path, and the panel is only ~248px wide."""
    from services.video import talking_head

    cfg = talking_head.TalkingHeadConfig.from_env()
    assert cfg.preprocess == "crop"
    assert cfg.size == 256
    assert cfg.still is True
    # GFPGAN roughly doubles VRAM and runtime for detail the panel cannot show.
    assert cfg.enhancer is None


def test_portrait_must_be_an_image_not_a_video(monkeypatch, tmp_path):
    """SadTalker takes a still; passing an idle video is a common mix-up."""
    from services.video import talking_head

    sadtalker = tmp_path / "SadTalker"
    sadtalker.mkdir()
    (sadtalker / "inference.py").write_text("", encoding="utf-8")
    clip = tmp_path / "idle.mp4"
    clip.write_bytes(b"x")

    monkeypatch.setenv("GURUFLOW_TALKING_HEAD", "1")
    monkeypatch.setenv("GURUFLOW_SADTALKER_DIR", str(sadtalker))
    monkeypatch.setenv("GURUFLOW_TEACHER_PORTRAIT", str(clip))

    problems = talking_head.config().problems()
    assert any("still image" in p for p in problems)


def test_config_accepts_a_complete_setup(monkeypatch, tmp_path):
    from services.video import talking_head

    sadtalker = tmp_path / "SadTalker"
    sadtalker.mkdir()
    (sadtalker / "inference.py").write_text("", encoding="utf-8")
    portrait = tmp_path / "teacher.png"
    portrait.write_bytes(b"x")

    monkeypatch.setenv("GURUFLOW_TALKING_HEAD", "1")
    monkeypatch.setenv("GURUFLOW_SADTALKER_DIR", str(sadtalker))
    monkeypatch.setenv("GURUFLOW_TEACHER_PORTRAIT", str(portrait))

    assert talking_head.config().problems() == []
    assert talking_head.available() is True


def test_status_names_the_engine():
    from services.video import talking_head

    assert talking_head.status()["engine"] == "sadtalker"


# ---------------------------------------------------------------------------
# Committed demo video seeding
# ---------------------------------------------------------------------------


def test_seed_dir_exists_and_holds_the_demo_videos():
    """Demo-day insurance: the judged lesson must not render on the critical path."""
    seed_dir = video_service.SEED_DIR
    assert seed_dir.exists(), f"expected committed demo videos at {seed_dir}"
    videos = list(seed_dir.glob("*.mp4"))
    assert len(videos) >= 9, "7 lesson scenes + 2 repair scenes expected"
    assert all(v.stat().st_size > 10_000 for v in videos)


def test_seeding_is_idempotent_and_never_clobbers_a_local_render(tmp_path):
    """A locally re-rendered video must survive a restart."""
    source = tmp_path / "seed"
    source.mkdir()
    (source / "aaaa1111.mp4").write_bytes(b"committed-copy")

    cache = video_service.CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / "aaaa1111.mp4"
    target.write_bytes(b"locally-rendered-and-newer")
    try:
        summary = video_service.seed_cache_from_repo(source)
        assert summary["skipped"] == 1
        assert summary["seeded"] == 0
        assert target.read_bytes() == b"locally-rendered-and-newer"
    finally:
        target.unlink(missing_ok=True)


def test_seeding_copies_when_the_cache_is_empty(tmp_path):
    source = tmp_path / "seed"
    source.mkdir()
    (source / "bbbb2222.mp4").write_bytes(b"x" * 32)

    target = video_service.CACHE_DIR / "bbbb2222.mp4"
    target.unlink(missing_ok=True)
    try:
        summary = video_service.seed_cache_from_repo(source)
        assert summary["seeded"] == 1
        assert target.exists()
    finally:
        target.unlink(missing_ok=True)


def test_seeding_tolerates_a_missing_seed_directory(tmp_path):
    """A fresh clone without demo assets must still start."""
    summary = video_service.seed_cache_from_repo(tmp_path / "does-not-exist")
    assert summary["available"] is False
    assert summary["seeded"] == 0


def test_committed_seeds_match_the_current_demo_lesson_hashes():
    """Guard against silent seed drift.

    Video filenames are content hashes covering narration, visual, language,
    quality *and* renderer version. Any change to those invalidates the
    committed demo videos, and the failure is silent - the demo simply starts
    rendering live again, which is exactly the risk the seeds exist to remove.

    This caught a real drift during development: adding `hideBuiltInTeacher` to
    the hash left 0 of 7 seeds matching.
    """
    from services.evaluation import (
        CONSTANT_CURRENT,
        DIRECT_PROPORTIONALITY,
        build_repair_scene,
    )
    from services.ingestion import ingest_topic
    from services.planner import plan_lesson

    seeded = {p.stem for p in video_service.SEED_DIR.glob("*.mp4")}
    assert seeded, "no committed demo videos found"

    language = "hinglish"
    plan = plan_lesson(
        {
            "level": "beginner",
            "language": language,
            "availableMinutes": 20,
            "goal": "Understand Ohm's Law",
        },
        ingest_topic("Ohm's Law"),
        topic="Ohm's Law",
    )

    expected = [(s["conceptId"], video_service.video_id(s, language)) for s in plan["scenes"]]
    expected += [
        ("repair-direct-proportionality",
         video_service.video_id(build_repair_scene(DIRECT_PROPORTIONALITY, language), language)),
        ("repair-constant-current",
         video_service.video_id(build_repair_scene(CONSTANT_CURRENT, language), language)),
    ]

    missing = [name for name, vid in expected if vid not in seeded]
    assert not missing, (
        "Committed demo videos are stale for: "
        + ", ".join(missing)
        + ". Re-render them into demo-assets/videos/ (see demo-assets/README.md)."
    )


# ---------------------------------------------------------------------------
# Prerender / status agreement
# ---------------------------------------------------------------------------


def _demo_lesson(client):
    response = client.post(
        "/lessons/plan",
        json={
            "learner": {
                "level": "beginner",
                "language": "hinglish",
                "availableMinutes": 20,
                "goal": "Understand Ohm's Law",
            },
            "topic": "Ohm's Law",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_status_covers_the_repair_scenes_prerender_warms(client):
    """The bug this guards: status counted only the plan's scenes.

    Prerender warms the two repair scenes as well, so status reported
    "all ready" while the flagship repair scene was still rendering.
    """
    plan = _demo_lesson(client)
    lesson_id = plan["id"]

    status = client.get(f"/lessons/{lesson_id}/video/status").json()
    assert status["total"] == len(plan["scenes"]) + 2, (
        "status must include both repair scenes, not just the plan's scenes"
    )

    repair = [s for s in status["scenes"] if s["isRepair"]]
    assert len(repair) == 2
    assert all(not s["isRepair"] for s in status["scenes"][: len(plan["scenes"])])


def test_status_total_matches_prerender_count(client, monkeypatch):
    """The two endpoints must never disagree about what gets rendered."""
    plan = _demo_lesson(client)
    lesson_id = plan["id"]

    queued: list[list[dict]] = []

    def fake_prerender(scenes, language):
        queued.append(list(scenes))
        return [f"vid-{i}" for i, _ in enumerate(scenes)]

    monkeypatch.setattr(video_service, "video_generation_available", lambda: True)
    monkeypatch.setattr(video_service, "prerender_lesson", fake_prerender)

    prerendered = client.post(f"/lessons/{lesson_id}/video/prerender").json()
    status = client.get(f"/lessons/{lesson_id}/video/status").json()

    assert prerendered["count"] == status["total"]
    assert len(queued[0]) == status["total"]


def test_complete_is_false_while_anything_is_unrendered(client):
    """`complete` is the signal a demo script should trust."""
    plan = _demo_lesson(client)
    status = client.get(f"/lessons/{plan['id']}/video/status").json()

    assert status["complete"] is (status["ready"] == status["total"])
    if status["ready"] < status["total"]:
        assert status["complete"] is False


def test_status_reports_failed_scenes_by_id(client):
    plan = _demo_lesson(client)
    status = client.get(f"/lessons/{plan['id']}/video/status").json()
    assert isinstance(status["failed"], list)
    for scene_id in status["failed"]:
        assert any(s["sceneId"] == scene_id for s in status["scenes"])


def test_status_404s_for_an_unknown_lesson(client):
    assert client.get("/lessons/nope/video/status").status_code == 404
