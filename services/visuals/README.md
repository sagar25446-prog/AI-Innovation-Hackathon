# @guruflow/visuals

Visual specification templates and renderers for GuruFlow.

## Modules

### Visual Specs (`src/visual-specs.js`)
Deterministic visual specification templates for various lesson types, especially Ohm's Law.
- `createCircuitSpec(options)`
- `createEquationSpec(options)`
- `createGraphSpec(options)`
- `createConceptMapSpec(options)`
- `createWaterPipeAnalogySpec(options)`

### Render Hints (`src/render-hints.js`)
Generates rendering hints for the frontend based on visual specs.
- `getRenderHint(visualSpec)`

### Caption Generator (`src/caption-generator.js`)
Utilities for generating and timed caption segments while preserving mathematical formulae.
- `generateCaptions(narrationText, language, durationSeconds)`
- `translateCaptionLanguage(captions, targetLanguage)`
