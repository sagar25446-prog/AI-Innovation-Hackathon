# GuruFlow teacher brain (apps/api)

FastAPI service that plans lessons, evaluates checkpoint answers, diagnoses
misconceptions and produces the learning report. It also serves the web client
and the media/visual ES modules, so the whole product runs from one process.

Deterministic by default: **no API keys, no network, no database.**

## Run

```bash
python -m pip install -r apps/api/requirements.txt
python -m uvicorn apps.api.main:app --reload --port 8077
```

Everything in `requirements.txt` installs from wheels on Windows, macOS and
Linux with no compiler. Semantic vector RAG is deliberately optional because
`chroma-hnswlib` needs a C++ toolchain:

```bash
python -m pip install -r apps/api/requirements-vector.txt   # optional
set GURUFLOW_VECTOR_RAG=1
```

Open <http://127.0.0.1:8077/> for the product, `/docs` for Swagger.

Run from the repository root so `services/` resolves.

## Tests

```bash
python -m pytest apps/api/tests -q
```

98 tests cover the planner, the evaluation branches, multi-format upload (PDF /
DOCX / PPTX / TXT), real diagram rendering, long-term student memory, flashcards,
gamified study modes, spaced multi-day revision planning and the judge-critical
API path. Two of the suites are end-to-end regression guards: **upload -> plan**
(an uploaded material must be persistable and reusable by `/lessons/plan`) and
**unknown topic** (asking for an unsupported topic must return an honest refusal,
never a silently mislabelled Electricity lesson). The API path also includes a
guard against "fake adaptation" (a test that fails if the learner's answer does
not change what is taught next).

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness and mode |
| POST | `/materials` | Ingest a topic or pasted text into cited sections |
| GET | `/materials/{materialId}` | Extraction status |
| POST | `/upload` | Upload a PDF / DOCX / PPTX / TXT / MD, persist it, and return a plan-able `materialId` |
| POST | `/lessons/plan` | Plan a lesson for a learner profile (`studyMode`: lesson/exam/revision) |
| GET | `/lessons/{lessonId}` | Re-fetch a plan |
| POST | `/lessons/{lessonId}/language` | Re-render in another language, keeping progress |
| POST | `/lessons/{lessonId}/scenes/{sceneId}/complete` | Mark a scene watched |
| POST | `/lessons/{lessonId}/checkpoints/{checkpointId}/answer` | Evaluate and adapt |
| GET | `/lessons/{lessonId}/report` | Learning report for one lesson |
| GET | `/students/{studentId}/report` | Learning report for a student |
| POST | `/lessons/{lessonId}/ask` | Answer a follow-up, grounded in the material |
| POST | `/video/render` | Render a scene's teaching video (background) |
| GET | `/video/{videoId}/status` | Poll a render |
| GET | `/video/{videoId}.mp4` | Serve the video (supports HTTP Range) |
| POST | `/lessons/{lessonId}/video/prerender` | Warm the whole lesson's video cache |
| GET | `/lessons/{lessonId}/video/status` | Per-scene render status |
| POST | `/tts` | Narration audio for a line of text |
| GET | `/students/{studentId}/profile` | **Long-term learning profile (persistent)** |
| GET | `/students/{studentId}/history` | Chronological lesson history |
| GET | `/students/{studentId}/study-plan` | **Spaced 7-day revision schedule from memory** |
| POST | `/lessons/{lessonId}/flashcards` | Generate review flashcards (optionally for weak concepts) |
| GET | `/diagram` | Render a circuit/equation/graph PNG |

## Modules

| Module | Responsibility |
| --- | --- |
| `services/ingestion` | Topic/text -> page-numbered sections (built-in NCERT Ch.12 corpus) |
| `services/rag` | Keyword + LangChain retrieval, grounding confidence |
| `services/planner` | Concept catalogue -> `Scene` objects adapted to level/language/time/personality |
| `services/planner/flashcards` | Deterministic review-card generation from scenes |
| `services/planner/persona` | Multiple teacher personalities (patient / socratic / coach) |
| `services/planner/study_plan` | Spaced multi-day revision scheduling ("the 7-day rhythm") |
| `services/evaluation` | Answer classification, misconception diagnosis, repair scene, report |
| `apps/api/store.py` | `LessonRepository` seam + in-memory implementation |
| `apps/api/student_memory.py` | File-backed long-term student memory |
| `apps/api/models.py` | Pydantic projection of the JSON contract |
| `services/voice` | Narration: edge-tts -> gTTS -> captions-only fallback chain |
| `services/video` | Manim animation + narration + ffmpeg mux, cached by content hash |
| `services/qa` | Follow-up questions answered from the lesson's own material |

## Configuration

Copy `.env.example` to `.env`. Every value is optional; the demo path needs
none of them.

## Teaching video

Each scene renders to a narrated MP4: a Manim animation of the scene's own
`VisualSpec`, a neural voice track, and burned-in captions timed from the
speech. Rendering happens in a background thread and is cached on a hash of the
scene, so a scene renders once; the UI keeps showing the interactive view until
the file exists.

The visuals are drawn programmatically rather than sampled from a generative
video model. A text-to-video model cannot be relied on to draw a correct
circuit or a correct `I = V/R` curve, and a plausible-but-wrong diagram would
undermine the grounding the product is built on.

Videos are cached outside the repo (`GURUFLOW_VIDEO_CACHE`, default temp dir)
because `AGENTS.md` forbids committing large generated media.

```bash
# Faster renders for a demo on a slow machine
set GURUFLOW_VIDEO_QUALITY=low
```

## Deliberate limits

* Retrieval is keyword overlap, not embeddings. Enough for the bundled corpus;
  a real deployment should swap `services.rag.score_section`.
* State is in memory. `LessonRepository` is the seam for Postgres/Supabase;
  restarting the server clears sessions.
* Answer classification is rule-based (see `services/evaluation/misconceptions.py`)
  unless `GEMINI_API_KEY` is set. It handles English, Hindi and Hinglish cue
  words but is not semantic on its own.
* The first video of a lesson takes a few seconds to render. Hit
  `POST /lessons/{id}/video/prerender` (the web client does this automatically
  when a lesson starts) to warm the cache before demonstrating.
