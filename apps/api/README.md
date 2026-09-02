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

Open <http://127.0.0.1:8077/> for the product, `/docs` for Swagger.

Run from the repository root so `services/` resolves.

## Tests

```bash
python -m pytest apps/api/tests -q
```

73 tests cover the planner, the evaluation branches and the judge-critical API
path, including a guard against "fake adaptation" (a test that fails if the
learner's answer does not change what is taught next).

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness and mode |
| POST | `/materials` | Ingest a topic or pasted text into cited sections |
| GET | `/materials/{materialId}` | Extraction status |
| POST | `/lessons/plan` | Plan a lesson for a learner profile |
| GET | `/lessons/{lessonId}` | Re-fetch a plan |
| POST | `/lessons/{lessonId}/language` | Re-render in another language, keeping progress |
| POST | `/lessons/{lessonId}/scenes/{sceneId}/complete` | Mark a scene watched |
| POST | `/lessons/{lessonId}/checkpoints/{checkpointId}/answer` | Evaluate and adapt |
| GET | `/lessons/{lessonId}/report` | Learning report for one lesson |
| GET | `/students/{studentId}/report` | Learning report for a student |

## Modules

| Module | Responsibility |
| --- | --- |
| `services/ingestion` | Topic/text -> page-numbered sections (built-in NCERT Ch.12 corpus) |
| `services/rag` | Keyword retrieval + grounding confidence |
| `services/planner` | Concept catalogue -> `Scene` objects adapted to level/language/time |
| `services/evaluation` | Answer classification, misconception diagnosis, repair scene, report |
| `apps/api/store.py` | `LessonRepository` seam + in-memory implementation |
| `apps/api/models.py` | Pydantic projection of the JSON contract |

## Configuration

Copy `.env.example` to `.env`. Every value is optional; the demo path needs
none of them.

## Deliberate limits

* Retrieval is keyword overlap, not embeddings. Enough for the bundled corpus;
  a real deployment should swap `services.rag.score_section`.
* State is in memory. `LessonRepository` is the seam for Postgres/Supabase;
  restarting the server clears sessions.
* Answer classification is rule-based (see `services/evaluation/misconceptions.py`).
  It handles English, Hindi and Hinglish cue words but is not semantic.
