# GuruFlow - AI Teacher of the  Future

GuruFlow is a source-grounded, multilingual AI teacher that creates personalized,
adaptive lessons, checks understanding, detects misconceptions, and re-teaches
what it gets wrong. It runs fully offline from the built-in Electricity corpus,
or from **any document you upload** (PDF/DOCX/PPTX/TXT/MD).

## AI teaching video

GuruFlow renders a **narrated teaching video for every scene**, locally and with
no API key: a Manim animation of that scene's own visual, a Microsoft neural
voice (edge-tts) reading the narration, and burned-in captions timed from the
speech. Press **Watch video** in the classroom.

The animation is drawn programmatically rather than sampled from a generative
video model. A text-to-video model cannot be relied on to draw a correct circuit
or a correct `I = V/R` curve, and a plausible-but-wrong diagram would undermine
the source-grounding the whole product rests on. Generative video is therefore
deliberately not used for explanatory content.

The teacher is a drawn avatar by default, so the product runs anywhere with no
GPU. Teams with an NVIDIA card can switch on a **photoreal, lip-synced teacher**
rendered offline with SadTalker - it composites into the video's teacher panel
and needs about 6 GB of VRAM. Setup and measured render times are in
[the talking-head guide](docs/TALKING_HEAD_SETUP.md); everything falls back to
the drawn avatar if it is absent, so it is never required.

See [the integrated product](docs/INTEGRATED_PRODUCT.md) for the full SWOT.

## Product loop

`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The focused demo uses a Class 9 Electricity upload and teaches Ohm's Law in Hinglish to a beginner. It visibly shows sources, an avatar plus circuit visual, a wrong answer, misconception recovery, and a final report.

## Teaching languages

Fifteen. **English, Hindi and Hinglish** are hand-authored end to end; the other
twelve - Bengali, Gujarati, Kannada, Malayalam, Marathi, Nepali, Odia, Punjabi,
Sinhala, Tamil, Telugu, Urdu - are localised on demand by
`services/translation`, using Gemini when a key is present and falling back to
the English source offline so a lesson always renders.

Equations are never translated: the prompt pins numbers, units, variable
letters and expressions, so `I = V/R` is identical in all sixteen.

Switch language mid-lesson and mastery, attempts and diagnosed misconceptions
all survive. See [known limitations](docs/KNOWN_LIMITATIONS.md#6-languages-sixteen-but-only-three-are-hand-authored)
for what "sixteen" does and does not mean.

## Lesson planning: curated first, LLM for the rest

A topic the built-in catalogue covers is planned deterministically - identical
every run, instant, and no API quota. Anything else (an off-catalogue topic, or
your own upload) goes to Gemini.

That split matters for demos: only a reproducible plan can reuse pre-rendered
video, and it keeps the free tier's daily quota for the topics that actually
need generating. `GURUFLOW_PREFER_CURATED=0` forces LLM planning everywhere.

## Run the product

Needs **Python 3.12**. Everything installs from wheels - no compiler, no
database, no build step.

```bash
py -3.12 -m pip install -r apps/api/requirements.txt
```

```bash
py -3.12 -m uvicorn apps.api.main:app --port 8077
```

Open <http://127.0.0.1:8077/> and press **Demo**.

```bash
py -3.12 -m pytest apps/api/tests -q
```

### Use `py -3.12`, not `python`

If you also install Python 3.10 for the optional talking head, it takes over
`python` on PATH in every **new** shell, and GuruFlow's dependencies are not
there - you get `No module named uvicorn`. Naming the version avoids it
entirely. Check with:

```bash
py -3.12 -c "import uvicorn, manim; print('ok')"
```

### Windows PowerShell

PowerShell 5.1 rejects `&&` (`The token '&&' is not a valid statement
separator`). Use `;` between commands, and `$env:NAME="value"` instead of
`set NAME=value`. Or open **Git Bash**, where the commands in this README work
verbatim.

### Enable the live Gemini brain (recommended for the demo)

Lesson planning, answer evaluation and repair narration call **Gemini Flash**
when a key is present, and fall back to the built-in deterministic engine
otherwise. The top-right badge shows the live state.

1. Get a free key at <https://aistudio.google.com/apikey>
2. Put it in **`apps/api/.env`** - create the file if it does not exist:

   ```
   GEMINI_API_KEY=your_key_here
   ```

3. **Restart the server.** `.env` is read once at import, so a key added to a
   running server has no effect.

Then `/health` reports `"gemini": true` and the badge reads *live Gemini brain*.

> **Put the key in `.env`, never in `.env.example`.** `.env.example` is a
> committed template - a key there is pushed to GitHub and lands in history,
> where deleting it later does not help. `.env` is gitignored, and is the only
> file the app actually loads.

**The free tier allows 20 requests per model per day, per project.** Rotating a
key does **not** reset that: the quota belongs to the AI Studio project, not the
key. If you run out, either wait for the daily reset, create a key in a new
project, or enable billing. Which model answers is resolved at runtime from a
candidate list, so a model Google retires does not break planning.

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
the flagship feature and the SWOT analysis, and
**[known limitations](docs/KNOWN_LIMITATIONS.md)** for an honest account of
offline mode vs. an LLM-configured deployment - read that one before demoing.

> **Set `GEMINI_API_KEY` before judging.** Without it GuruFlow teaches the
> built-in Electricity chapter and any electricity document you upload, and
> honestly refuses other topics rather than teaching the wrong subject. With
> it, "teach any topic" actually works. Create `apps/api/.env` with
> `GEMINI_API_KEY=...` (free key: <https://aistudio.google.com/apikey>).

## For contributors

### Getting a working checkout

```bash
git clone https://github.com/sagar25446-prog/AI-Innovation-Hackathon.git
```

```bash
cd AI-Innovation-Hackathon && py -3.12 -m pip install -r apps/api/requirements.txt && py -3.12 -m pytest apps/api/tests -q
```

A green suite means you are set up correctly. Run every command from the
repository root so `services/` resolves.

Semantic vector RAG is deliberately **not** in `requirements.txt`, because
`chroma-hnswlib` needs a C++ toolchain and would break `pip install` for
everyone who does not want it:

```bash
py -3.12 -m pip install -r apps/api/requirements-vector.txt
```

The JavaScript suites need Node and run separately:

```bash
node --test services/media/test/*.test.js services/visuals/test/*.test.js packages/contracts/test/*.test.js apps/web/test/*.test.js
```

### Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `No module named uvicorn` | `python` resolved to another version | Use `py -3.12` |
| `The token '&&' is not a valid statement separator` | PowerShell 5.1 | Use `;`, or Git Bash |
| `command not found` on a `C:\...` path | Git Bash reads `\` as an escape | Use `/c/...` |
| `"gemini": false` after adding a key | Key is in `.env.example`, or the server was not restarted | Put it in `.env`, restart |
| `429 RESOURCE_EXHAUSTED` | Free tier: 20 requests/model/day **per project** | Wait for reset, new project, or billing |
| Video button never enables | Manim or ffmpeg missing | Check `/health` -> `video.available` |
| `talkingHead.usable: false` | Optional feature, off by default | `problems` in `/health` names what is missing |

### Before a demo

Warm the video cache - the first render of a scene takes about two minutes with
the talking head enabled, and you do not want that happening in front of judges:

```bash
curl -X POST http://127.0.0.1:8077/lessons/LESSON_ID/video/prerender
```

Poll `GET /lessons/LESSON_ID/video/status` until `"complete": true`. That
includes both misconception-repair scenes, not just the plan's scenes.

Videos are cached in the system temp directory, so **do not run disk cleanup**
between pre-rendering and demonstrating.

### Repository layout

| Path | What lives there |
| --- | --- |
| `apps/api/` | FastAPI teacher brain, serves the web client too |
| `apps/web/` | Zero-build ES-module frontend |
| `services/` | ingestion, rag, planner, evaluation, llm, voice, video, qa, media, visuals |
| `packages/contracts/` | `lesson-contract.schema.json`, the single source of truth |
| `tools/` | `check_portrait.py` for validating a talking-head portrait |
| `docs/` | Setup guides, known limitations, third-party disclosure |

Integrate through `packages/contracts/`. Read `AGENTS.md` before changing code
outside your own area.


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
checklist lives in [docs/TEAM_IMPLEMENTATION.md](docs/TEAM_IMPLEMENTATION.md).

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
