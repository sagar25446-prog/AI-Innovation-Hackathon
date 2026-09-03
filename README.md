# GuruFlow - AI Teacher of the Future

GuruFlow is a source-grounded, multilingual AI teacher that creates personalized,
adaptive lessons, checks understanding, detects misconceptions, and re-teaches
what it gets wrong. It runs fully offline from the built-in Electricity corpus,
or from **any document you upload** (PDF/DOCX/PPTX/TXT/MD).

## Honest scope: the avatar and "video" reality

A teacher read-along is your avatar. The product renders a **hand-drawn SVG
teacher (blinking eyes, talking mouth) with karaoke captions and a live visual
canvas** -- it does **not** produce a lip-synced D-ID video file out of the box.
A real D-ID integration ships in `services/media/` and is wired for provider
swapping, but the shipped browser uses the SVG teacher by default (a Jupyter/API
key is required for D-ID, and the brief's "talking avatar video" would need that
provisioned). See [the integrated product](docs/INTEGRATED_PRODUCT.md) for the
candid SWOT on this exact trade-off.

## Product loop

`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The focused demo uses a Class 9 Electricity upload and teaches Ohm's Law in Hinglish to a beginner. It visibly shows sources, an avatar plus circuit visual, a wrong answer, misconception recovery, and a final report.

## Run the product

```bash
python -m pip install -r apps/api/requirements.txt
python -m uvicorn apps.api.main:app --port 8077
```

Open <http://127.0.0.1:8077/>. No build step, no database. Tests:
`python -m pytest apps/api/tests -q`.

### Enable the live Gemini brain (recommended for the demo)

Lesson planning, answer evaluation and repair narration call **Gemini Flash
(`gemini-2.5-flash`)** when a key is present, and fall back to the built-in
deterministic engine otherwise. The top-right badge shows the live state.

```bash
# 1. Get a free key at https://aistudio.google.com/apikey
# 2. Create apps/api/.env and add your key (never commit this file):
#    GEMINI_API_KEY=your_key_here
# 3. Restart, then the badge reads "live Gemini brain"
python -m uvicorn apps.api.main:app --port 8077
```

Other optional keys (all independent and fall back cleanly):
`GURUFLOW_TTS_API_KEY`, `GURUFLOW_AVATAR_API_KEY`, `GURUFLOW_LLM_API_KEY`.
Voice always streams real audio via the server's `edge-tts` endpoint.

### Enable full vector RAG

Semantic retrieval (sentence-transformers embeddings + a persistent ChromaDB
index, with exact page-cited sections) is implemented and opt-in. This engages
real vector search on top of the fast keyword fallback:

```bash
# in apps/api/.env
GURUFLOW_VECTOR_RAG=1
```

Requires `pip install sentence-transformers chromadb` (both are in
`apps/api/requirements.txt`). When disabled (default), retrieval uses the
instant keyword path so tests and the core demo stay fast.

Retrieval is also **orchestrated with LangChain** (`langchain-core`): sections
are adapted to LangChain `Document`s and served through a `BaseRetriever`
(`services/rag/langchain_layer.py`). `/health` reports
`"rag": { "langchain": true, "mode": "langchain-orchestrated-..." }` so the
orchestration is visible. It delegates to the same ChromaDB -> embedding ->
keyword waterfall, so it adds no new failure mode and stays fast by default.

### Multi-format material upload and real visual rendering

`POST /upload` extracts page/slide-numbered citation sections from **PDF,
DOCX, PPTX, TXT and MD**, so your own textbook chapter or slide deck feeds the
same grounding pipeline as the bundled corpus — and the returned `materialId`
can be used by `POST /lessons/plan` to learn from that document:

```bash
curl -F "file=@notes.pptx" http://127.0.0.1:8077/upload
# then POST /lessons/plan with {"materialId": "<id from above>", ...}
```

`POST /diagram` renders a scene's visual spec (`circuit`, `equation`, `graph`,
`concept_map`, `water_pipe_analogy`) as a real **PNG** via matplotlib, so the
visual a scene calls for is genuinely generated, not just described:

```bash
curl -X POST http://127.0.0.1:8077/diagram \
  -H "Content-Type: application/json" \
  -d '{"type":"circuit","title":"V = I × R"}' -o diagram.png
```

Backed by `python-docx`, `python-pptx` and `matplotlib` (all pinned in
`apps/api/requirements.txt`).

### Long-term student memory, flashcards and personalities

Beyond a single lesson, GuruFlow **remembers each student across sessions** and
offers review and teaching-style options:

- **Long-term student memory** — every finished lesson is folded into a
  file-backed profile (`apps/api/student_memory.py`). It tracks per-concept
  mastery (running average), recurring misconceptions and a chronological
  lesson history, and survives server restarts. Exposed as
  `GET /students/{studentId}/profile` and `GET /students/{studentId}/history`.
- **Flashcard generation** — `POST /lessons/{lessonId}/flashcards` turns a
  lesson's scenes into review cards (front/back, in the learner's language),
  always including the core Ohm's Law formula card. Filter to the learner's
  weak concepts via `{"conceptIds": [...]}`.
- **Multiple teacher personalities** — a learner can pick a `personality`
  (`patient`, `socratic` or `coach`) in their profile. It reframes narration
  tone and checkpoint feedback without changing what is taught, so the default
  stays the deterministic hero path.
- **Gamified study modes** — a learner can pick `studyMode: lesson`,
  `exam` (assessment-heavy drill centred on the checkpoint + practice) or
  `revision` (a quick spaced recap) when planning.
- **Spaced multi-day revision ("the 7-day rhythm")** —
  `GET /students/{studentId}/study-plan` turns accumulated memory into a
  spaced-repetition calendar across one week (days 1, 2, 4, 7), revising weak
  concepts earliest and most often (`services/planner/study_plan.py`).
- **Learning profile dashboard** — the web app's report screen now links to a
  persistent dashboard (`screen-profile`) that visualizes concept mastery,
  recurring patterns, weak/strong concepts, review flashcards, a 7-day revision
  plan and lesson history, pulled from the profile endpoints.

The web client was also polished for the UI/UX rubric: a hand-drawn SVG teacher
avatar with blinking eyes and a talking mouth, karaoke-style caption
word-highlighting, scene-transition animations, confetti on a correct answer,
proper stacked-fraction equation rendering, and loading spinners.

```bash
curl http://127.0.0.1:8077/students/student-demo/profile
curl http://127.0.0.1:8077/students/student-demo/study-plan
curl -X POST http://127.0.0.1:8077/lessons/LESSON_ID/flashcards \
  -H "Content-Type: application/json" -d '{"conceptIds":["ohms-law"]}'
```

See [the integrated product](docs/INTEGRATED_PRODUCT.md) for the architecture,
the flagship feature and the SWOT analysis.

## Team ownership

| Owner | Directories |
| --- | --- |
| Frontend | `apps/web/` |
| Teacher brain | `apps/api/`, `services/ingestion/`, `services/rag/`, `services/planner/`, `services/evaluation/` |
| Media and contracts | `services/media/`, `services/visuals/`, `packages/contracts/`, `demo-fixtures/` |

Read [team implementation](docs/TEAM_IMPLEMENTATION.md) and the
[integrated product](docs/INTEGRATED_PRODUCT.md) notes before extending the
system. The integration contract is defined by
[packages/contracts/](packages/contracts/README.md). A submission/delivery
checklist lives in [docs/CODEX_TASKS_V2.md](docs/CODEX_TASKS_V2.md).

## First integration milestone

1. Submit learner profile and source/topic.
2. Receive a `LessonPlan` containing `Scene` objects.
3. Render a scene and submit one learner answer.
4. Receive an `EvaluationResult` with `advance` or `repair`.
5. Display a final `LearningReport`.

## Working agreement

- Integrate only through `packages/contracts/`.
- Build against `demo-fixtures/` until a service is live.
- Merge small pull requests into `develop`; reserve `main` for stable demos.
- Never make a breaking contract change without updating fixtures.
