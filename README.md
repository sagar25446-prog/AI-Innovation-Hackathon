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

Open <http://127.0.0.1:8077/> and press **Demo mode**. No API keys, no build
step, no database. Tests: `python -m pytest apps/api/tests -q`.

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
