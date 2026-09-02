# Team implementation guide

## Ownership

| Person | Branch | Directories | Outcome |
| --- | --- | --- | --- |
| 1 - Frontend | `feat/frontend` | `apps/web/` | Onboarding, classroom player, checkpoints, report |
| 2 - Teacher brain | `feat/teacher-brain` | `apps/api/`, `services/ingestion/`, `services/rag/`, `services/planner/`, `services/evaluation/` | Grounded lesson plan, evaluator, misconception repair, progress |
| 3 - Media/contracts | `feat/media-contracts` | `services/media/`, `services/visuals/`, `packages/contracts/`, `demo-fixtures/` | Avatar, voice, visuals and stable contracts |

## Non-negotiable integration rules

1. `packages/contracts/lesson-contract.schema.json` is the source of truth. Never copy schemas into apps.
2. A contract change updates the schema, fixture and pull-request description; the affected owner must approve it.
3. Frontend uses API/fixtures only - never direct database access.
4. Media receives `Scene` JSON only - never calls RAG or planner internals.
5. Teacher brain returns provider-neutral data - no avatar-provider fields in lesson planning.
6. Merge focused pull requests into `develop` daily. Merge to `main` only after fixture smoke tests pass.

## API lifecycle

`POST /materials or POST /topic -> POST /lessons/plan -> GET /lessons/{lessonId} -> POST /media/render-scene -> POST /lessons/{lessonId}/checkpoints/{checkpointId}/answer -> GET /students/{studentId}/report`

## Contract guarantees

- IDs are opaque strings; times are seconds; mastery is always 0 to 1.
- Every `Scene` is renderable without calling the planner again.
- `repairScene` is present only when `nextAction` is `repair`.
- Unknown visual types fall back to a narrated concept card instead of breaking the UI.

## Delivery checklist

### Day 1
- Contract and fixtures committed.
- Frontend renders plan and scene fixture.
- API returns cited Electricity lesson-plan fixture.
- Avatar/TTS spike produces a scene or fallback.

### Day 2-3
- PDF/DOCX/PPTX extraction retains page/slide locators.
- Planner adapts to level, time and language.
- Classroom player includes avatar, visual canvas, captions and progress.
- Wrong Ohm's Law answer produces a misconception label and repair scene.
- Hindi/Hinglish works without losing context.
- Final report lists score, strengths, weak concepts and next topic.

### Day 4-5
- Test correct, confused, misconception, language switch and provider fallback.
- Document all third-party APIs/models and limitations.
- Record: upload -> plan -> teach -> question -> adapt -> report.
