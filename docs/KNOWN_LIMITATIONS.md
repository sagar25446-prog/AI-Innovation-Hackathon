# Known limitations

An honest account of what GuruFlow does and does not do today. Written to be
read before a demo, not after a surprise.

---

## 1. Offline mode vs. Gemini-configured mode

GuruFlow runs in two quite different modes, and the difference matters more
than any other single fact about the product.

| | Offline (no `GEMINI_API_KEY`) | Gemini configured |
| --- | --- | --- |
| Built-in Class 9 Electricity chapter | Full lesson, page-cited | Full lesson, page-cited |
| Uploaded document **about electricity** | Full lesson, cited to **your upload** | Same, with richer narration |
| Uploaded document on **any other subject** | **Honest refusal** - see below | Real lesson on that subject, cited to your upload |
| Topic request outside the curated library | **Honest refusal** | Real lesson generated for that topic |
| Misconception detection | Rule-based, two misconceptions | Semantic, model-assisted |
| Follow-up questions (`/ask`) | Extractive - quotes the cited passage | Generated answer, constrained to retrieved passages |

### What "honest refusal" means

Offline, the curated teaching content covers **one chapter**: Class 9
Electricity. Ask for photosynthesis, or upload a biology passage, and GuruFlow
returns a single scene saying it has no grounded material for that topic and
naming the next step - it does **not** quietly serve an Ohm's Law lesson under
a photosynthesis heading.

This is deliberate. Teaching the wrong subject confidently is a worse failure
for a teaching product than admitting a gap, and it is the failure mode a judge
is most likely to catch.

The check is a retrieval probe: the four core curated concepts are matched
against the material, and at least two must ground. A short paraphrased
electricity upload passes; unrelated prose does not.

### The practical consequence

**Set `GEMINI_API_KEY` before judging.** Create `apps/api/.env`:

```
GEMINI_API_KEY=your-key-here
```

Without it, "teach any topic" is honestly scoped rather than delivered, and
`/health` reports `"gemini": false`. Free keys: <https://aistudio.google.com/apikey>.

---

## 2. Subject-specific visuals: implemented, but schematic

`services/video/scenes.py` now has a purpose-built animated builder for
**every** visual type in the contract - nothing falls through to a generic
layout:

| Visual type | Subject | What it draws |
| --- | --- | --- |
| `equation` | Maths / Physics | Stepped rows, final step highlighted |
| `graph` | Maths / Physics | Drawn axes, plotted curve, markers |
| `circuit` | Physics | Battery, load, animated charge flow |
| `concept_map` | Any | Hierarchy with connecting edges |
| `code_trace` | Programming | Code with line numbers and an execution cursor stepping through the run order |
| `timeline` | History | Directional dated axis, events alternating above and below so labels cannot collide |
| `diagram` | Biology / Physics | Labelled schematic with leader lines; also renders the composite repair descriptor |

### The honest caveat

The Biology diagram is a **schematic, not an illustration.** It draws a generic
body with an interior structure and points labelled leader lines at distinct
positions on it. That is the *structure* of a labelled diagram, and it is far
more useful than a row of chips - but the label positions are assigned by
order, not by anatomy. It will not show you where the chloroplast actually sits
in a plant cell.

Drawing anatomically correct diagrams needs per-subject artwork, not a generic
builder. The scene titles say "(schematic)" for this reason. Treat these as
structural aids, not reference figures.

Similarly, the timeline places events evenly along the axis in the order given,
not proportionally by date. Free-text dates ("c. 1500 BCE", "1947") cannot be
reliably parsed into positions, and guessing would misinform; trusting the
author's ordering does not.

## 3. Content depth

The curated catalogue is one chapter, hand-authored. Breadth beyond it depends
entirely on the LLM path (limitation 1).

## 4. Misconception library

Two misconceptions are modelled: direct-proportionality confusion and
constant-current confusion. Offline detection is cue-word matching across
English, Hindi and Hinglish - it handles the tricky
"resistance badhne se current kam hoga" case correctly, but it is not semantic
and will not survive the full variety of real student phrasing at scale.

## 5. Avatar

The teacher is a drawn figure with procedural mouth movement, not a photoreal
lip-synced human. A SadTalker integration ships behind
`GURUFLOW_TALKING_HEAD=1` (see `docs/TALKING_HEAD_SETUP.md`) and needs a GPU
plus a portrait you have rights to. Off by default; every failure path falls
back to the drawn avatar.

## 6. Languages: fifteen, but only three are hand-authored

**English, Hindi and Hinglish** have hand-written narration, feedback,
flashcards and depth notes throughout the concept catalogue. These are the
languages the product was designed in, and they are the best experience.

**Twelve more** - Bengali, Gujarati, Kannada, Malayalam, Marathi, Nepali, Odia,
Punjabi, Sinhala, Tamil, Telugu and Urdu - are localised on demand by
`services/translation`. What that means in practice:

* **With a Gemini key:** a real translation, produced once and cached. The
  prompt forbids touching numbers, units, variable letters and equations, so
  `I = V/R` survives every language exactly.
* **Offline:** the canonical English string is returned unchanged. A Tamil
  learner still gets a complete lesson, voice and video - narrated in English.
  That is a deliberate degradation, not a failure: a working English lesson
  beats a blank scene or a crash.

So "fifteen languages" is honest about *coverage*, not about *authoring depth*.
Do not claim fifteen hand-written curricula.

### Voice

Thirteen of the fifteen have a female edge-tts neural voice. **Odia and
Punjabi have none**, and fall back to gTTS or captions-only. This is asserted
in the tests so it cannot regress silently.

## 7. Persistence

Lesson state is in memory and dies with the process. `LessonRepository` is the
seam for Postgres/Supabase; nothing else needs to change.

## 8. Licensing

`PyMuPDF` is AGPL-3.0, and the bundled corpus quotes NCERT material. Fine for a
hackathon; both need addressing before anything commercial.
