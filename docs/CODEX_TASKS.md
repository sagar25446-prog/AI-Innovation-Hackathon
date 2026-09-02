# Ready-to-paste Codex tasks

All teammates: clone the repository, create your assigned branch from `develop`, read `AGENTS.md`, and make changes only in your owned folders. Run tests/build, commit focused changes, push the branch and open a PR to `develop`.

## Person 1 - Frontend
Paste to Codex:
```
Read AGENTS.md, README.md, docs/TEAM_IMPLEMENTATION.md and packages/contracts/lesson-contract.schema.json. You are Person 1; modify only apps/web/.

Create a Next.js TypeScript Tailwind GuruFlow UI with mock data in apps/web/src/mocks and one API client. It must work without backend. Implement onboarding (upload/topic, level, English/Hindi/Hinglish, time, goal), source analysis + timed lesson plan, classroom with avatar placeholder/captions/progress/evidence drawer, circuit/equation/graph rendering from Scene JSON, checkpoint UI, supportive repair UI for direct-proportionality confusion using I = V/R plus water-pipe graph, and final progress report. No database, RAG, backend or media-provider logic. Run typecheck/build. Commit only apps/web with message feat(frontend): add GuruFlow adaptive lesson experience; push feat/frontend and open a PR to develop.
```

## Person 2 - Teacher brain
Paste to Codex:
```
Read AGENTS.md, README.md, docs/TEAM_IMPLEMENTATION.md and packages/contracts/lesson-contract.schema.json. You are Person 2; modify only apps/api, services/ingestion, services/rag, services/planner and services/evaluation.

Build a FastAPI backend with deterministic fixtures first: health, POST /materials, POST /lessons/plan, GET /lessons/{lessonId}, POST /lessons/{lessonId}/checkpoints/{checkpointId}/answer, GET /students/{studentId}/report. Return schema-compatible LessonPlan and EvaluationResult. Plan Current -> Voltage -> Resistance -> Ohm's Law for beginner/intermediate/advanced, English/Hindi/Hinglish, 5/10/20/60 minutes. Wrong current-vs-resistance answer must identify direct-proportionality confusion, return repair Scene and retry; correct answer advances. Add Pydantic models, CORS, .env.example, README and tests. No paid APIs initially. Commit owned folders with message feat(teacher): add lesson planning and adaptive evaluation API; push feat/teacher-brain and open PR to develop.
```

## Person 3 - Media and visuals
Paste to Codex:
```
Read AGENTS.md, README.md, docs/TEAM_IMPLEMENTATION.md, packages/contracts/lesson-contract.schema.json and demo-fixtures/ohms-law-misconception.json. You are Person 3; modify only services/media, services/visuals, packages/contracts and demo-fixtures.

Create provider-neutral TTSProvider, AvatarProvider and SceneRenderer interfaces. Add a no-key mock provider and an intentional fallback: teacher image/video panel, captions and live visual canvas. Build deterministic VisualSpec templates for circuit, V = IR / I = V/R equation steps, descending current-vs-resistance graph, and concept-map fallback. Add fixtures for intro, teaching scenes, checkpoint, misconception repair, retry and report. Validate fixtures against schema and preserve formulae across English/Hindi/Hinglish. Do not add backend routes, planner, RAG or UI pages. Commit owned folders with message feat(media): add visual scenes and adaptive demo fixtures; push feat/media-contracts and open PR to develop.
```
