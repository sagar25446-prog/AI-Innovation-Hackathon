# Session record - GuruFlow work

Local copy of the repo with full git history and remotes intact. Branch:
`feat/video-generation-and-rubric-fixes`.

## What was done, in order

### 1. Built the missing half of the product (PR #2)

Only Person 3's slice (`services/media`, `services/visuals`,
`packages/contracts`, `demo-fixtures`) existed. Person 1 (frontend) and Person 2
(teacher brain) had never been implemented. Both were built, with Task 2's
adaptive loop folded in rather than bolted on:

* `services/ingestion`, `services/rag`, `services/planner`, `services/evaluation`
* `apps/api` - FastAPI, all endpoints, `LessonRepository` seam
* `apps/web` - onboarding, plan, classroom, evidence drawer, checkpoint, repair
  UI, report

Two bugs found by actually running it: an infinite repair<->checkpoint loop
after a correct retry, and a checkpoint scene earning "taught" mastery just for
being watched.

*(Superseded - the team merged a great deal more afterwards.)*

### 2. Rubric-aligned assessment (PR #6)

Assessed the product against the Round 2 PDF by installing and running it.
Scored it at roughly **62/100**. Key finding: the repo's
`CODEX_TASKS_V2.md` "Task 1/2" are internal sprints and are **not** the
hackathon's Task 1/2 - the hackathon's Task 1 is the *AI Teaching Video*, and
that was the thing not done.

See `docs/RUBRIC_SWOT_AND_VIDEO_PLAN.md`.

### 3. Fixed the gaps and built the video (PR #7)

| Area | Before | After |
| --- | --- | --- |
| Teaching video | None. No `<video>` element existed | Narrated MP4 per scene, rendered locally |
| Voice | `POST /tts` returned 500 | Works; `edge-tts` was pinned to a version Microsoft now rejects with 403 |
| Install | `pip install -r requirements.txt` failed; pytest could not collect | Installs from wheels everywhere |
| Follow-up Q&A | Missing (an explicit Task 2 requirement) | `POST /lessons/{id}/ask`, grounded with citations |
| D-ID | Unreachable, undocumented dead code | Documented as optional and not wired |
| Tests | 98 | 115 (+ a real render test behind a flag) |

## Running it

```bash
cd "C:\AI Innovation Hackathon 2026\GuruFlow"
python -m pip install -r apps/api/requirements.txt
python -m uvicorn apps.api.main:app --port 8077
```

Open <http://127.0.0.1:8077/>, press **Demo**, then **Watch video** in the
classroom.

```bash
python -m pytest apps/api/tests -q                       # 115 passing
set GURUFLOW_RUN_SLOW_TESTS=1 && python -m pytest apps/api/tests -q   # + real render
set GURUFLOW_VIDEO_QUALITY=low                           # faster renders
```

Videos cache to `%TEMP%\guruflow_videos` (override with `GURUFLOW_VIDEO_CACHE`).
They are not committed: `AGENTS.md` forbids committing large generated media.

## Still open

* `gemini: false` by default - set `GEMINI_API_KEY` before judging, or the
  15-mark LLM criterion scores on the deterministic path alone.
* Content is still one chapter (Class 9 Electricity). Other topics are taught
  but honestly marked as ungrounded.
* Misconception detection is rule-based unless a Gemini key is present; two
  misconceptions are modelled.
* Only three languages.
* `PyMuPDF` is AGPL-3.0 - fine for a hackathon, a licensing question for a
  product.

## Sample output

`../sample-videos/` holds a few rendered scenes, including the repair scene,
so the output can be reviewed without running a render.
