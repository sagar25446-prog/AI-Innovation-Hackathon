# @guruflow/contracts

This package contains the JSON Schema definitions and validation logic for the GuruFlow AI teacher platform.

## Schema Definitions

The schema is defined in `lesson-contract.schema.json`. It includes the following entities:

### `LearnerProfile`
Represents the learner's preferences and constraints.
- `level`: beginner, intermediate, or advanced.
- `language`: english, hindi, or hinglish.
- `availableMinutes`: Available time for the lesson.
- `goal`: What the learner wants to achieve.

### `SourceCitation`
Used to trace AI generated content back to original source materials.
- `documentId`: ID of the source material.
- `pageOrSlide`: Page or slide number.
- `excerpt`: The exact excerpt from the source.

### `VisualSpec`
Specifies what visual element should be displayed alongside the narration.
- `type`: One of circuit, equation, graph, timeline, diagram, code_trace, concept_map.
- `data`: An object containing visual specific data.

### `Scene`
A single block of instruction in a lesson.
- `id`: Unique identifier for the scene.
- `conceptId`: The concept being taught.
- `objective`: The goal of this specific scene.
- `narration`: The script the AI teacher will speak.
- `visual`: A `VisualSpec` object.
- `citations`: An array of `SourceCitation` objects.
- `durationSeconds`: Estimated time to complete the scene.
- `checkpointId`: (Optional) ID of an assessment checkpoint if this scene includes one.

### `LessonPlan`
A complete lesson tailored for a learner.
- `id`: Unique identifier for the lesson.
- `learner`: A `LearnerProfile` object.
- `scenes`: An array of `Scene` objects.

### `EvaluationResult`
The result of evaluating a learner's answer at a checkpoint.
- `correct`: Whether the answer was correct.
- `mastery`: A score between 0 and 1 indicating mastery level.
- `misconception`: (Optional) Identified misconception if the answer was wrong.
- `feedback`: Explanatory feedback for the learner.
- `nextAction`: What to do next (advance, repair, retry).
- `repairScene`: (Optional) A `Scene` object to teach the corrected concept if `nextAction` is `repair`.

## Usage Rules
- All AI generated content must adhere to these schemas to be processed by the media and UI layers.
- Checkpoint evaluations must return a valid `EvaluationResult`.
- Repairs must be full `Scene` objects, capable of being rendered independently.

## Versioning Policy
This package follows SemVer. 
- Major version bumps for breaking changes to the schema.
- Minor version bumps for non-breaking additions (e.g., new visual types).
- Patch version bumps for documentation or validation script updates.
