# GuruFlow - AI Teacher of the Future

GuruFlow is a source-grounded, multilingual AI teacher that creates personalized video lessons, checks understanding, detects misconceptions, and adapts what it teaches next.

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

### Multi-format material upload and real visual rendering

`POST /upload` extracts page/slide-numbered citation sections from **PDF,
DOCX, PPTX, TXT and MD**, so your own textbook chapter or slide deck feeds the
same grounding pipeline as the bundled corpus:

```bash
curl -F "file=@notes.pptx" http://127.0.0.1:8077/upload
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

See [the integrated product](docs/INTEGRATED_PRODUCT.md) for the architecture,
the flagship feature and the SWOT analysis.

## Team ownership

| Owner | Directories |
| --- | --- |
| Frontend | `apps/web/` |
| Teacher brain | `apps/api/`, `services/ingestion/`, `services/rag/`, `services/planner/`, `services/evaluation/` |
| Media and contracts | `services/media/`, `services/visuals/`, `packages/contracts/`, `demo-fixtures/` |

Read [team ownership](docs/TEAM_OWNERSHIP.md), [integration contract](docs/INTEGRATION_CONTRACT.md), and [delivery checklist](docs/DELIVERY_CHECKLIST.md) before coding.

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
