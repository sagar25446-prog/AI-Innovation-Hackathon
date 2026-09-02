# GuruFlow team rules

Read this file before making any change.

## Product
GuruFlow is a source-grounded multilingual AI teacher. The demo must show: upload/topic -> personalised lesson plan -> avatar/video plus relevant visual -> checkpoint -> misconception repair -> final report.

Hero flow: teach Ohm's Law to a beginner in Hinglish. If the learner says current increases when resistance increases at constant voltage, diagnose direct-proportionality confusion, teach I = V/R, use a water-pipe analogy and graph, then retry.

## Ownership
| Role | Exclusive directories |
| --- | --- |
| Person 1 - frontend | apps/web/ |
| Person 2 - teacher brain | apps/api/, services/ingestion/, services/rag/, services/planner/, services/evaluation/ |
| Person 3 - media/contracts | services/media/, services/visuals/, packages/contracts/, demo-fixtures/ |

Do not edit outside your owned directories. In docs/, add a new file rather than rewriting another owner's file.

## Contract-first integration
- packages/contracts/lesson-contract.schema.json is the source of truth.
- Do not copy type definitions into multiple applications.
- Contract changes must be backward-compatible, update fixtures, and be described in the pull request.
- Frontend never talks to the database; it calls APIs or uses fixtures.
- Media renders a Scene; it never knows retrieval/planner internals.
- Backend returns provider-neutral JSON; it never assumes a particular avatar vendor.

## Delivery rules
- Implement deterministic demo behaviour before paid APIs.
- Keep secrets in .env, never commit them.
- Do not add model training, Kubernetes, microservices, custom avatar training, or large generated media.
- Run relevant tests/build before committing.
- Keep commits focused and open a pull request to develop, never directly to main.
