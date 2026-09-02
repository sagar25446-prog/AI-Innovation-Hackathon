"""GuruFlow teacher-brain API.

Runs the whole product loop:
``Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate ->
Adapt -> Continue``

The API also serves the web client and Person 3's media/visual ES modules, so
the entire SaaS runs from one process with no build step and no API keys.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, HTTPException, UploadFile, File  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from apps.api.models import (  # noqa: E402
    AnswerRequest,
    EvaluationResult,
    LearningReport,
    LessonPlan,
    MaterialRequest,
    PlanRequest,
)
from apps.api.store import InMemoryLessonRepository, LessonSession  # noqa: E402
from services.evaluation import (  # noqa: E402
    CHECKPOINT_CONCEPT_ID,
    build_report,
    evaluate_answer,
)
from services.ingestion import ingest_text, ingest_topic  # noqa: E402
from services.planner import plan_lesson  # noqa: E402

WEB_DIR = REPO_ROOT / "apps" / "web"

# Mastery credited for a concept the learner watched all the way through.
TAUGHT_MASTERY = 0.8

app = FastAPI(
    title="GuruFlow Teacher Brain",
    version="2.0.0",
    description=(
        "Source-grounded, multilingual AI teacher. Plans lessons from material, "
        "detects misconceptions and adapts the next scene."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("GURUFLOW_CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

repository = InMemoryLessonRepository()


@app.middleware("http")
async def no_store_for_assets(request, call_next):
    """Stop browsers caching the client during a demo.

    A stale styles.css or app.js after a last-minute fix is a classic demo
    failure; the app is small enough that revalidating every asset costs
    nothing.
    """
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".js", ".css", ".html", ".json")) or path == "/":
        response.headers["Cache-Control"] = "no-store, must-revalidate"
    return response


# ---------------------------------------------------------------------------
# Health and materials
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, Any]:
    from services.llm import gemini_available
    return {
        "status": "ok",
        "service": "guruflow-teacher-brain",
        "mode": "deterministic" if not gemini_available() else "llm-enhanced",
        "gemini": gemini_available(),
    }


@app.post("/materials")
def create_material(request: MaterialRequest) -> dict[str, Any]:
    """Ingest a topic or pasted text and report extraction status."""
    if request.text:
        material = ingest_text(request.text, request.title or "Uploaded material")
    else:
        material = ingest_topic(request.topic or "")
    repository.save_material(material)
    return material.to_dict()


@app.get("/materials/{material_id}")
def get_material(material_id: str) -> dict[str, Any]:
    material = repository.get_material(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return material.to_dict()


# ---------------------------------------------------------------------------
# Lesson planning
# ---------------------------------------------------------------------------


@app.post("/lessons/plan", response_model=LessonPlan)
def create_plan(request: PlanRequest) -> dict[str, Any]:
    """Plan a lesson for this learner, grounded in the chosen material."""
    material = None
    if request.materialId:
        material = repository.get_material(request.materialId)
        if material is None:
            raise HTTPException(status_code=404, detail="Material not found")
    if material is None:
        material = ingest_topic(request.topic)
        repository.save_material(material)

    learner = request.learner.model_dump(exclude_none=True)
    plan = plan_lesson(learner, material, topic=request.topic)

    session = LessonSession(
        lesson_id=plan["id"],
        student_id=request.studentId,
        plan=plan,
        material_id=material.material_id,
    )
    repository.save_session(session)
    return plan


@app.get("/lessons/{lesson_id}", response_model=LessonPlan)
def get_lesson(lesson_id: str) -> dict[str, Any]:
    session = repository.get_session(lesson_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return session.plan


@app.post("/lessons/{lesson_id}/language", response_model=LessonPlan)
def switch_language(lesson_id: str, body: dict[str, str]) -> dict[str, Any]:
    """Re-render the lesson in another language, keeping learner progress.

    Progress lives on the session, not on the plan, so re-planning in a new
    language never resets mastery, attempts or diagnosed misconceptions.
    """
    session = repository.get_session(lesson_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    language = body.get("language")
    if language not in ("english", "hindi", "hinglish"):
        raise HTTPException(status_code=400, detail="Unsupported language")

    material = repository.get_material(session.material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")

    learner = dict(session.plan["learner"])
    learner["language"] = language
    session.plan = plan_lesson(
        learner,
        material,
        topic=session.plan.get("topic", "Ohm's Law"),
        lesson_id=session.lesson_id,
    )
    repository.save_session(session)
    return session.plan


@app.post("/lessons/{lesson_id}/scenes/{scene_id}/complete")
def complete_scene(lesson_id: str, scene_id: str) -> dict[str, Any]:
    """Mark a scene watched so the final report reflects real progress."""
    session = repository.get_session(lesson_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    scene = next((s for s in session.plan["scenes"] if s["id"] == scene_id), None)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")

    session.scenes_completed.add(scene_id)
    concept_id = scene["conceptId"]
    # Mastery is credited for being taught something. A checkpoint is assessed,
    # not taught, so watching one earns nothing -- its concept's mastery is
    # owned by evaluation.
    is_assessment = bool(scene.get("checkpointId")) or concept_id == CHECKPOINT_CONCEPT_ID
    if not is_assessment and concept_id not in session.concept_mastery:
        session.set_mastery(concept_id, TAUGHT_MASTERY)
    repository.save_session(session)

    return {
        "lessonId": lesson_id,
        "sceneId": scene_id,
        "scenesCompleted": len(session.scenes_completed),
        "totalScenes": len(session.plan["scenes"]),
    }


# ---------------------------------------------------------------------------
# Evaluation and adaptation
# ---------------------------------------------------------------------------


@app.post(
    "/lessons/{lesson_id}/checkpoints/{checkpoint_id}/answer",
    response_model=EvaluationResult,
    # Omit null optionals so an "advance" result carries no empty repairScene.
    response_model_exclude_none=True,
)
def answer_checkpoint(
    lesson_id: str, checkpoint_id: str, request: AnswerRequest
) -> dict[str, Any]:
    """Evaluate a checkpoint answer and decide what to teach next."""
    session = repository.get_session(lesson_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    language = request.language or session.plan["learner"]["language"]
    attempt = session.record_attempt(checkpoint_id)
    result = evaluate_answer(
        request.answer, language=language, attempt=attempt, option_id=request.optionId
    )

    session.set_mastery(CHECKPOINT_CONCEPT_ID, result["mastery"])

    if result["nextAction"] == "repair":
        session.checkpoints_failed += 1
        session.note_misconception(result["misconception"], CHECKPOINT_CONCEPT_ID)
    elif result["correct"]:
        session.checkpoints_passed += 1
        # A correct answer after a repair closes the misconception.
        session.resolve_misconceptions()

    repository.save_session(session)

    result["attempt"] = attempt
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _report_for_session(session: LessonSession) -> dict[str, Any]:
    return build_report(
        student_id=session.student_id,
        lesson_id=session.lesson_id,
        concept_mastery=session.concept_mastery,
        misconceptions=list(session.misconceptions.values()),
        scenes_completed=len(session.scenes_completed),
        checkpoints_passed=session.checkpoints_passed,
        checkpoints_failed=session.checkpoints_failed,
        total_time_seconds=session.elapsed_seconds(),
    )


@app.get("/lessons/{lesson_id}/report", response_model=LearningReport)
def lesson_report(lesson_id: str) -> dict[str, Any]:
    session = repository.get_session(lesson_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return _report_for_session(session)


@app.get("/students/{student_id}/report", response_model=LearningReport)
def student_report(student_id: str) -> dict[str, Any]:
    sessions = repository.sessions_for_student(student_id)
    if not sessions:
        raise HTTPException(status_code=404, detail="No lessons for this student")
    return _report_for_session(sessions[-1])


# ---------------------------------------------------------------------------
# Text-to-Speech
# ---------------------------------------------------------------------------

VOICE_MAP = {
    "english": "en-IN-MadhurNeural",
    "hindi": "hi-IN-SwaraNeural",
    "hinglish": "hi-IN-MadhurNeural",
}


@app.post("/tts")
async def text_to_speech(body: dict[str, str]) -> Response:
    """Generate speech audio from text using edge-tts (free, no API key)."""
    text = body.get("text", "").strip()
    language = body.get("language", "hinglish")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    voice = VOICE_MAP.get(language, VOICE_MAP["hinglish"])

    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = tmp.name
        tmp.close()
        await communicate.save(tmp_path)
        return FileResponse(tmp_path, media_type="audio/mpeg", filename="speech.mp3")
    except ImportError:
        raise HTTPException(status_code=503, detail="edge-tts not installed. Run: pip install edge-tts")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(exc)}")


# ---------------------------------------------------------------------------
# File upload for PDF parsing
# ---------------------------------------------------------------------------


@app.post("/upload")
async def upload_material(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a PDF or text file and extract sections for lesson planning."""
    content = await file.read()
    filename = file.filename or "uploaded-file"

    if filename.lower().endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            sections = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    lines = text.strip().splitlines()
                    heading = lines[0].strip()[:80] if lines else f"Page {page_num + 1}"
                    sections.append({
                        "sectionId": f"upload-sec-{page_num + 1}",
                        "pageOrSlide": page_num + 1,
                        "heading": heading,
                        "excerpt": text.strip()[:500],
                        "keywords": _derive_upload_keywords(text),
                    })
            doc.close()
            material_id = f"material-upload-{filename}"
            return {
                "materialId": material_id,
                "documentId": material_id,
                "title": filename,
                "status": "ready",
                "origin": "upload",
                "sectionCount": len(sections),
                "pageCount": len({s["pageOrSlide"] for s in sections}),
                "sections": sections,
            }
        except ImportError:
            raise HTTPException(status_code=503, detail="PyMuPDF not installed. Run: pip install PyMuPDF")
    elif filename.lower().endswith((".txt", ".md")):
        text = content.decode("utf-8", errors="replace")
        material = ingest_text(text, title=filename)
        return material.to_dict()
    else:
        raise HTTPException(status_code=400, detail="Only PDF and text files are supported")


_STOPWORDS_UPLOAD = {
    "the", "a", "an", "of", "to", "and", "is", "are", "in", "on", "for",
    "it", "that", "this", "with", "as", "by", "be", "or", "from", "at",
}

def _derive_upload_keywords(text: str) -> list[str]:
    import re
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    seen: list[str] = []
    for word in words:
        if word not in _STOPWORDS_UPLOAD and word not in seen:
            seen.append(word)
    return seen[:12]


# ---------------------------------------------------------------------------
# Static hosting: web client plus Person 3's ES modules
# ---------------------------------------------------------------------------

# Serving the media/visuals sources lets the browser import the real contract
# modules instead of a reimplementation of them.
app.mount(
    "/vendor/visuals",
    StaticFiles(directory=REPO_ROOT / "services" / "visuals" / "src"),
    name="visuals",
)
app.mount(
    "/vendor/media",
    StaticFiles(directory=REPO_ROOT / "services" / "media" / "src"),
    name="media",
)
app.mount(
    "/fixtures",
    StaticFiles(directory=REPO_ROOT / "demo-fixtures"),
    name="fixtures",
)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
