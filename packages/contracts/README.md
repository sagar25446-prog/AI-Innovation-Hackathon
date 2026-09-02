# @guruflow/contracts

This package contains the authoritative JSON Schema definitions (JSON Schema Draft-07), validation engine, and contract interfaces for the GuruFlow source-grounded multilingual AI teacher platform.

---

## Contract-First Architecture

GuruFlow follows a strict **contract-first integration** model:
1. `lesson-contract.schema.json` is the single source of truth for all data exchange.
2. The AI Teacher Brain (Planner, RAG, Evaluator) produces validated JSON conforming to these definitions.
3. The Media and Visual layers render standard `Scene` and `VisualSpec` payloads independently of backend provider implementations.
4. The Frontend consumes validated `LessonPlan`, `Scene`, `EvaluationResult`, and `LearningReport` data.

---

## Schema Definitions

All definitions reside in `lesson-contract.schema.json`.

### 1. `LearnerProfile`
Represents the learner's preferences, pacing, and pedagogical goals.
- `level` *(enum)*: `"beginner" | "intermediate" | "advanced"`
- `language` *(enum)*: `"english" | "hindi" | "hinglish"`
- `availableMinutes` *(integer, 1..10080)*: Available time duration for the lesson.
- `goal` *(string, minLength: 1)*: Target learning objective.
- `priorKnowledge` *(string, optional)*: Summary of learner's prior knowledge.

### 2. `SourceCitation`
Grounds generated teaching explanations in original source materials (e.g. NCERT textbooks).
- `documentId` *(string, minLength: 1)*: Identifier of the source document (e.g. `"ncert-class9-science-ch12"`).
- `pageOrSlide` *(integer, $\ge 1$)*: Page or slide number in the source material.
- `heading` *(string, optional)*: Section or subsection header.
- `excerpt` *(string, minLength: 1)*: Verbatim text excerpt from the cited source.

### 3. `VisualSpec`
Defines the interactive visual element displayed alongside teacher narration.
- `type` *(enum)*: `"circuit" | "equation" | "graph" | "timeline" | "diagram" | "code_trace" | "concept_map"`
- `data` *(object)*: Type-specific visual payload.

#### Supported Visual Data Schemas:
- **`circuit`**: Includes `components` (batteries, resistors, switches, bulbs, ammeters with positions, coordinates, terminals, ports), `connections` (with waypoints and SVG path data), `currentFlow` (direction, active flag, speed, carrier path), `layout`, `annotations`, and `highlight`.
- **`equation`**: KaTeX-compatible LaTeX steps (`steps` array with `stepIndex`, `expression`, `latex`, `explanation`, `highlightedTerms`), `variables` metadata, and `misconceptionAnnotations`.
- **`graph`**: Cartesian graph specification including `xAxis` (label, unit, min, max, ticks), `yAxis` (label, unit, min, max, ticks), `gridlines`, `series` curves, `points`, `highlightedOperatingPoints`, and `annotations`.
- **`concept_map`**: Hierarchical knowledge graph containing `nodes` (id, label, category, type, symbol, position, level, style) and `edges` (id, from, to, relationType, label, directional, style).
- **`diagram`**: Hydraulic analogy and composite diagrams with `elements`, `flowParticles`, `comparisonMappingTable`, and `scenarioStates`.
- **`timeline`** & **`code_trace`**: Structured sequential stage progressions.

### 4. `Scene`
A discrete instructional unit within a lesson plan.
- `id` *(string, minLength: 1)*: Unique scene identifier (e.g. `"scene-1-intro"`, `"scene-repair-ohms-law"`).
- `conceptId` *(string, minLength: 1)*: Concept being taught (e.g. `"ohms-law"`).
- `objective` *(string, minLength: 1)*: Pedagogical goal of the scene.
- `narration` *(string, minLength: 1)*: Spoken script for teacher avatar and TTS.
- `visual` *(VisualSpec)*: Associated visual specification.
- `citations` *(SourceCitation[])*: Source citations grounding the scene narration.
- `durationSeconds` *(integer, $\ge 1$)*: Estimated duration of the scene.
- `checkpointId` *(string, optional)*: ID of assessment checkpoint if scene prompts a question.

### 5. `LessonPlan`
A complete structured curriculum tailored for a learner profile.
- `id` *(string, minLength: 1)*: Unique lesson identifier.
- `learner` *(LearnerProfile)*: Target learner profile.
- `scenes` *(Scene[], minItems: 1)*: Sequence of instruction scenes.

### 6. `EvaluationResult`
Evaluation output produced by the diagnostic evaluator following a learner's checkpoint response.
- `correct` *(boolean)*: Whether the learner answered correctly.
- `mastery` *(number, 0.0..1.0)*: Estimated concept mastery score.
- `misconception` *(string, optional)*: Diagnosed misconception (e.g. `"direct-proportionality confusion"`).
- `feedback` *(string, minLength: 1)*: Supportive, non-punitive pedagogical feedback.
- `nextAction` *(enum)*: `"advance" | "repair" | "retry"`
- `repairScene` *(Scene, optional)*: 20–45s remediation scene provided when `nextAction === "repair"`.

### 7. `LearningReport`
Post-lesson diagnostic report summarizing progress, mastery, and next steps.
- `studentId` *(string)*: Learner identifier.
- `lessonId` *(string)*: Completed lesson identifier.
- `score` *(number, 0.0..1.0)*: Overall lesson score.
- `strongConcepts` *(string[])*: Mastered concepts.
- `weakConcepts` *(string[])*: Concepts requiring further revision.
- `misconceptions` *(object[])*: Diagnostic log of identified and resolved misconceptions.
- `revisionActions` *(string[])*: Actionable next steps.
- `nextTopic` *(object)*: Suggested follow-up module.
- `totalTimeSeconds` *(integer)*: Total time spent.
- `scenesCompleted` *(integer)*: Count of completed scenes.
- `checkpointsPassed` *(integer)*: Checkpoints answered correctly.
- `checkpointsFailed` *(integer)*: Checkpoints requiring remediation.

### 8. `CheckpointSubmission`
Represents a student's answer submission at an interactive checkpoint.
- `lessonId` *(string, optional)*: Lesson identifier.
- `checkpointId` *(string, minLength: 1)*: Checkpoint identifier.
- `studentAnswer` *(string, minLength: 1)*: Learner's response text.
- `expectedEvaluation` *(EvaluationResult, optional)*: Expected evaluation outcome in demo fixtures.

---

## Validation Tooling

### CLI Usage

Validate demo fixtures or any JSON files:
```bash
# Validate all demo fixtures
node packages/contracts/validate.js demo-fixtures/*.json

# Or using npm script
npm run validate
```

### Programmatic API

```javascript
const {
  validateData,
  validateFixture,
  validateAgainstSchema,
  inferType,
  getSchema,
  getDefinitions
} = require('@guruflow/contracts');

// Validate a JSON file directly from disk
const result = validateFixture('path/to/fixture.json');
console.log(result.valid); // true / false
console.log(result.type);  // 'LessonPlan' | 'Scene' | 'EvaluationResult' | etc.
console.log(result.errors); // Array of validation error strings

// Validate a JavaScript object against inferred or explicit schema type
const evalResult = validateData(myObject, 'EvaluationResult');
if (!evalResult.valid) {
  console.error('Validation errors:', evalResult.errors);
}
```

---

## Unit Testing

Run contract validation unit tests:
```bash
npm test
# or: node --test test/*.test.js
```

---

## Versioning Policy

This package follows **Semantic Versioning (SemVer)**:
- **Major**: Breaking changes to schema definitions (e.g. changing required fields or renaming types).
- **Minor**: Backward-compatible schema additions (e.g. new optional fields, new visual types).
- **Patch**: Documentation updates, validator optimizations, and test additions.
