# GuruFlow: three-person execution prompts (v2)

## Core strategy

Build a working adaptive teacher, not three disconnected demos. Reuse mature components when they save time; integrate through the existing JSON contract; do not fine-tune an LLM or train an avatar during the hackathon.

### Reuse decision table

| Need | Reuse first | Build ourselves | Decision rule |
| --- | --- | --- | --- |
| Voice UI / WebRTC | LiveKit Agent Starter React | Small WebSocket/text fallback | Reuse only if real-time voice is required today |
| RAG | FastAPI + simple section chunking + pgvector/Chroma | Custom ingestion orchestration | Do not deploy heavy RAGFlow for the MVP |
| Avatar | API adapter or pre-rendered clips | Placeholder teacher panel + TTS/captions | Use local MuseTalk/Wav2Lip only with a verified CUDA GPU and a working demo within 60 minutes |
| Visuals | KaTeX, SVG, Plotly, Manim clips | Subject-specific React/SVG templates | Build deterministic Electricity templates; do not use random images |
| Teaching platform ideas | Open TutorAI / NADOO-Teacher architecture | GuruFlow adaptation logic | Borrow ideas, never fork a full product blindly |

### Fine-tuning decision

Do not fine-tune a foundation model. The evidence of intelligence is: grounded retrieval, structured lesson planning, a learner model, misconception detection, alternative explanations and test coverage. Use prompt templates, JSON schemas, demonstration fixtures and evaluation cases instead.

## Shared rules for every Codex agent

1. Read `AGENTS.md`, `README.md`, `docs/TEAM_IMPLEMENTATION.md`, this file and the shared schema before coding.
2. Work only in the directories assigned in `AGENTS.md`.
3. Start with mock/deterministic mode; provider integrations are optional adapters.
4. Before adding a dependency, inspect its licence, maintenance, hardware requirement and time-to-first-working-demo. Reject it if it cannot improve the judge-visible flow today.
5. Every task ends with: run checks, inspect the end-to-end result, fix actual defects, commit, push feature branch and open/update a PR to `develop`.
6. Never change `main` directly.

## Task 1: combined Day 1 and Day 2 foundation

### Person 1 prompt - frontend foundation

```text
You are Person 1. Read the shared rules above and modify only apps/web/.

Build a clean Next.js TypeScript Tailwind GuruFlow frontend. Use mocks only initially. Implement onboarding, source/topic entry, learner profile, source-analysis card, time-budgeted lesson-plan timeline, classroom shell, captions, teacher/avatar placeholder, progress, evidence drawer and a visual canvas.

Implement deterministic visual components for Scene.visual.type: circuit, equation, graph and fallback concept card. The hero lesson is beginner Hinglish Ohm's Law. Make the UI demonstrate that the lesson was planned from material and is not a chatbot.

Reuse decision: start from a plain Next app. You may adapt LiveKit's React starter only if live voice is already a hard requirement and its setup works in under one hour. Do not make LiveKit required for the mock demo.

Definition of done: a user can click through onboarding -> analysis -> plan -> three teaching scenes -> checkpoint placeholder -> report placeholder with no backend.

Before commit: run lint, typecheck and production build; manually inspect desktop and mobile layout; fix issues found. Commit only apps/web and push feat/frontend.
```

### Person 2 prompt - teacher brain foundation

```text
You are Person 2. Read the shared rules above and modify only apps/api, services/ingestion, services/rag, services/planner and services/evaluation.

Build a modular FastAPI teacher brain in deterministic mode. Add health, material-upload/extraction status, lesson-plan, lesson retrieval, checkpoint-answer and report endpoints. Use Pydantic models compatible with the shared contract.

The planner must output Scene objects, not long chatbot answers. It must adapt lesson order/depth/duration to beginner/intermediate/advanced, English/Hindi/Hinglish and 5/10/20/60 minutes. The Electricity path is Current -> Voltage -> Resistance -> Ohm's Law -> checkpoint -> assessment. Retain page/slide citations in ingestion metadata.

Reuse decision: use lightweight parsers and section-aware chunks. Do not deploy RAGFlow or a large agent framework unless the simple path fails and the alternative works in a one-hour spike. Put future LLM calls behind one provider adapter.

Definition of done: Swagger works; all endpoints return stable fixture data; tests cover Hinglish plan, time adaptation and source citation fields.

Before commit: run tests and an API smoke test; fix defects; commit only owned folders and push feat/teacher-brain.
```

### Person 3 prompt - media and contract foundation

```text
You are Person 3. Read the shared rules above and modify only services/media, services/visuals, packages/contracts and demo-fixtures.

Validate and protect the shared schema. Create provider-neutral TTSProvider, AvatarProvider and SceneRenderer interfaces. Implement no-key mock providers and intentionally polished fallback output: teacher image/video panel, captions and a live visual canvas.

Create deterministic visual specifications and fixtures for circuit, V = IR / I = V/R transformation, a graph where current declines as resistance rises at fixed voltage, and a concept-map fallback. Add scene fixtures for intro, current/voltage, resistance, checkpoint, repair, retry and report.

Reuse decision: use KaTeX/SVG/Plotly or browser-native drawing. Use Manim only for a pre-rendered optional clip. Use MuseTalk/Wav2Lip only after verifying local CUDA capacity and a 60-minute proof; otherwise keep the provider adapter and polished fallback.

Definition of done: Person 1 can render every fixture; Person 2 can consume contract fields unchanged; all fixture JSON validates; no API key is needed for the demo path.

Before commit: validate fixtures, test fallback, fix defects, commit owned folders and push feat/media-contracts.
```

### Task 1 integration gate

All three join after their first PRs are ready. Merge media/contracts first, backend second, frontend third. Test: learner profile -> fixture LessonPlan -> Scene rendering -> checkpoint shell -> report shell. If any field mismatch appears, update the contract and fixtures once, then update consumers. Do not add advanced features until this passes.

## Task 2: adaptive teaching loop

### Person 1 prompt - interaction and repair UI

```text
Modify only apps/web/. Replace checkpoint placeholders with text/MCQ interaction. On submit, call the backend; render evaluating state and EvaluationResult. When nextAction is repair, never say “Wrong.” Show supportive feedback, the misconception explanation, replacement repair Scene and retry control. Show English/Hindi/Hinglish language switch without resetting progress. Use media adapter output if available and fallback otherwise.

Definition of done: the visible demo completes wrong answer -> repair -> correct retry -> advance. Test mock and API mode; fix defects; commit/push feat/frontend and update PR.
```

### Person 2 prompt - evaluation, misconception and memory

```text
Modify only backend-owned directories. Implement checkpoint evaluation and mastery updates. Recognise the required Ohm's Law misconception: learner asserts current rises when resistance rises at fixed voltage. Return correct=false, misconception=direct-proportionality confusion, supportive feedback, nextAction=repair and a schema-valid repair Scene that asks a simpler retry.

Implement correct retry -> advance and a final report containing score, strong concepts, weak concepts, misconception status, revision actions and Series/Parallel Circuits next topic. Persist in memory or a lightweight local store first; expose a repository interface for Postgres/Supabase later.

Definition of done: automated tests prove correct, wrong, repair and retry branches; API response validates against contract; fix defects; commit/push feat/teacher-brain and update PR.
```

### Person 3 prompt - adaptive media branches

```text
Modify only media/contracts directories. Add render descriptors for advance and repair branches. The repair branch must render equation transformation, water-pipe analogy caption and descending graph in a coherent 20-45 second scene. Provide captions in English/Hindi/Hinglish while keeping equations unchanged. Add latency/error states and verify that missing avatar/TTS provider falls back gracefully.

Definition of done: repair Scene is demonstrably different from the original scene; provider failure does not stop the lesson; fixtures stay schema-valid; fix defects; commit/push feat/media-contracts and update PR.
```

### Task 2 integration gate

Run the judge-critical path using real API calls: Upload/topic -> plan -> scene -> deliberately wrong answer -> detected misconception -> repair visual -> correct retry -> final report. Record bugs by contract field, owner and reproduction step. Fix blockers before merging. Reject any “fake adaptation” where the answer does not change the next scene.

## Task 3: judging polish, reliability and differentiation

### Person 1 prompt - judge-ready UX

```text
Modify only apps/web/. Polish loading, upload status, source citations, empty/error states, mobile layout and accessibility. Add an Evidence drawer that shows the material page/slide and excerpt for each source-grounded scene. Make lesson duration visible. Add a demo mode button that reliably loads the Electricity fixture. Do not redesign backend/media contracts.

Definition of done: a judge understands the product without explanation; no broken layout; demo mode succeeds repeatedly; run build and commit/push.
```

### Person 2 prompt - RAG confidence and quality checks

```text
Modify only backend-owned directories. Add retrieval confidence/source-grounding status. If evidence is weak, explicitly flag general-knowledge explanation instead of fabricating citations. Add evaluation logging and test cases for beginner/intermediate, 5/20/60 minutes, English/Hindi/Hinglish, correct/confused/misconception answers. Write deployment and API/model disclosure notes in a new docs file only.

Definition of done: all demo outputs are traceable or clearly labelled; test matrix passes; run tests and commit/push.
```

### Person 3 prompt - media reliability and disclosure

```text
Modify only media/contracts directories. Pre-generate or cache the initial, advance and repair demo scene assets/descriptors. Confirm captions match narration and formulae. Add a third-party component/licence disclosure describing avatar/TTS/visual libraries and fallback. Test with provider keys absent, slow and failed.

Definition of done: demo remains usable with no avatar/TTS network access; visual output is subject-aware; fixture validation passes; commit/push.
```

### Task 3 final gate: inspect, improve, stop

Each person must answer after tests: (1) Is the assigned task demonstrably complete? (2) Is there a concrete defect, reliability risk or small improvement that increases judging score? (3) Can it be fixed within the remaining time without changing the contract or breaking another owner? If yes, fix it and rerun checks. If no, stop adding features and document the limitation.

The team then records a 3-7 minute demo: upload/topic -> plan -> video lesson with dynamic visual -> student interaction -> adaptive repair -> assessment -> learning feedback. Use the stable demo fixture if a provider is unreliable.

