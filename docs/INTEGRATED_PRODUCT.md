# GuruFlow: the integrated product

This document describes the end product after **Task 1 (foundation)** and
**Task 2 (adaptive teaching loop)** were built and integrated, what the
flagship feature is, and an honest SWOT analysis of what we actually have.

Written by the integrator. Per `AGENTS.md` this is a new file; no other
owner's document was rewritten.

---

## 1. What was built

At the start of this work only Person 3's slice existed on `main`
(`services/media`, `services/visuals`, `packages/contracts`, `demo-fixtures`).
Person 1 (frontend) and Person 2 (teacher brain) had not been implemented.

This change delivers both, with Task 2's adaptive loop folded in rather than
bolted on afterwards.

| Area | Task 1 (foundation) | Task 2 (adaptive loop) |
| --- | --- | --- |
| Teacher brain | Ingestion, retrieval, planner, all endpoints, deterministic fixtures | Checkpoint evaluation, misconception diagnosis, mastery memory, repair scenes, report |
| Frontend | Onboarding, source analysis, timed plan, classroom, visuals, evidence drawer | Text + MCQ checkpoint, supportive repair UI, retry, live language switch, report |
| Media/contracts | *(already merged)* | Browser providers + graceful degradation wired to the existing renderer |

### Run it

```bash
python -m pip install -r apps/api/requirements.txt
python -m uvicorn apps.api.main:app --port 8077
```

Open <http://127.0.0.1:8077/> and press **Demo mode**.

```bash
python -m pytest apps/api/tests -q     # 73 passing
```

---

## 2. Architecture

```
Browser (apps/web, zero build)
   |  imports directly
   +---> /vendor/visuals  -> services/visuals  (render hints, specs)
   +---> /vendor/media    -> services/media    (DefaultSceneRenderer)
   |         ^ browser TTS/avatar providers supplied by apps/web
   |
   v  HTTP (contract JSON)
FastAPI (apps/api)
   +-- services/ingestion  topic/upload -> page-numbered sections
   +-- services/rag        keyword retrieval + grounding confidence
   +-- services/planner    concept catalogue -> Scene objects
   +-- services/evaluation answer -> diagnosis -> repair Scene -> report
   +-- apps/api/store.py   LessonRepository seam (in-memory today)

packages/contracts/lesson-contract.schema.json  <- single source of truth
```

Three seams keep the product replaceable rather than rewritten:

* **`LessonRepository`** - swap in Postgres/Supabase without touching routes.
* **`TTSProvider` / `AvatarProvider`** - swap in a real vendor without touching
  scene rendering. The browser already proves this: `services/media`'s own mock
  providers import Node's `crypto` and cannot run in a browser, so `apps/web`
  supplies its own providers to the *same* renderer.
* **`services.rag.score_section`** - swap keyword overlap for embeddings.

### Additive contract fields

The schema was **not** modified. `packages/contracts` belongs to Person 3, and
the contract permits extra properties, so the API adds optional fields that old
consumers can ignore:

| Field | On | Meaning |
| --- | --- | --- |
| `groundingStatus` | Scene | `source_grounded` or `general_knowledge` |
| `isRepair` | Scene | Scene was generated to fix a misconception |
| `topic`, `materialId`, `documentTitle`, `tier`, `estimatedSeconds` | LessonPlan | UI metadata |
| `attempt` | EvaluationResult | 1-based checkpoint attempt |

All six existing fixtures still validate and still render.

---

## 3. Flagship feature

> ### Misconception-driven adaptive repair
>
> GuruFlow does not mark an answer right or wrong. It **names the specific
> false belief behind the answer, splices a brand-new teaching scene into the
> lesson that attacks that belief with a different representation, and then
> re-asks the question.**

The hero case: the learner says *"current increases when resistance
increases."* GuruFlow responds:

1. **Diagnosis** - `direct-proportionality confusion`, not "incorrect".
2. **Supportive feedback** - *"Lagbhag sahi! Lekin yaad rakho..."* The word
   "wrong" never appears; a test asserts this in all three languages.
3. **A new scene** - the lesson visibly grows from 7 scenes to 8. The repair
   scene teaches the same idea a *different* way: the equation transformation
   `I = V/R`, the water-pipe analogy, and the descending current-vs-resistance
   curve, in one 30-second scene.
4. **Retry** - the learner returns to the question. A correct answer now scores
   0.6 rather than 0.75, because it took a second attempt, and the misconception
   is marked `resolved` in the report.

**Why this is the flagship rather than the avatar or the RAG.** Video avatars
and retrieval are commodities; every competitor has them. What almost nothing
in this market does is treat a wrong answer as *diagnostic evidence about the
learner's mental model* and change the syllabus in response. The scene list the
learner experiences is not the scene list the planner produced - and that
difference is machine-checked. `test_answer_changes_the_next_scene` fails the
build if adaptation ever degrades into cosmetic feedback.

Two supporting features make the flagship credible rather than a demo trick:

* **Grounding honesty.** Every scene carries page-level citations, visible in
  the Evidence drawer. When the material does not cover a topic, GuruFlow
  labels the scene `general knowledge` and attaches *no* citations instead of
  inventing plausible ones (`test_unknown_topic_is_flagged_not_fabricated`).
* **Language without losing the learner.** English / Hindi / Hinglish switch
  mid-lesson; mastery, attempts and diagnosed misconceptions survive the
  switch, and formulae are never translated.

---

## 4. SWOT analysis

### Strengths

* **The adaptation is real and test-guarded.** A wrong answer provably changes
  the lesson content, not just the feedback text. This is the hardest claim for
  a competitor demo to make honestly, and the easiest for a judge to verify.
* **Source-grounded with visible evidence.** Page-level citations per scene,
  an Evidence drawer, and an explicit refusal to fabricate citations for
  uncovered topics. Trust is designed in, not asserted.
* **Genuinely multilingual, formula-safe.** Three languages including Hinglish
  (the language Indian students actually study in), with equations preserved
  verbatim across all of them.
* **Demo reliability is a feature.** No API keys, no network, no build step, no
  database. The entire judge-critical path runs offline from one process, and
  degrades to fixtures if the API misbehaves. Most hackathon demos die on a
  missing key or a rate limit.
* **Contract-first with real seams.** Storage, media providers and retrieval
  are each one class away from a production implementation. The browser media
  adapter is live proof the provider abstraction works, not a promise.
* **73 automated tests** covering the planner matrix (3 levels x 3 languages x
  4 time budgets), every evaluation branch, and the end-to-end path.
* **Time-budget adaptation.** 5/10/20/60 minutes produce genuinely different
  lessons, and a plan never overruns the learner's stated budget.

### Weaknesses

* **Content depth is one chapter.** The concept catalogue is hand-authored for
  Class 9 Electricity. A new topic gets the honest "general knowledge" label
  but no real teaching content - the product does not yet generalise.
* **No LLM in the loop.** Everything is deterministic. That is the right
  hackathon call (it is why the demo never fails) but it means the "AI teacher"
  currently *retrieves, plans and diagnoses* rather than *generates*.
* **Misconception detection is rule-based.** Cue-word matching over three
  languages, covering two misconceptions. It handles the tricky
  "resistance badhne se current kam hoga" case correctly, but it is not
  semantic and will not survive the full variety of real student phrasing.
* **Retrieval is keyword overlap, not embeddings.** Adequate for the bundled
  corpus, weak on arbitrary uploads.
* **No persistence, auth, or multi-tenancy.** State is in memory and dies with
  the process. There is no user account, no teacher view, no class.
* **Frontend diverges from the team plan.** It is vanilla ES modules, not
  Next.js + TypeScript + Tailwind, because Node.js was unavailable on the build
  machine. This buys demo reliability and costs type safety and component
  tests. The port path is documented in `apps/web/README.md`.
* **The avatar is a fallback, not an avatar.** A CSS teacher panel with
  captions and optional browser speech. Honest, but not the "video lesson" the
  brief imagines.

### Opportunities

* **The misconception library is the moat.** A curated map of
  *misconception -> diagnostic signal -> alternative representation* per topic
  is expensive to build, improves with usage data, and is far harder to copy
  than a RAG pipeline. This is the asset worth investing in.
* **Teacher and institution analytics.** The report data already contains
  everything needed for a class-level view: which misconceptions are common,
  which concepts are weak, who needs intervention. That is the B2B product, and
  it needs no new modelling.
* **Vernacular, low-connectivity markets.** Hinglish support plus a demo that
  runs with no network is a real fit for Indian tier-2/3 schools and coaching
  institutes, where the incumbents' English-first, bandwidth-heavy products fit
  badly.
* **Provider upgrades are drop-in.** Real TTS, a real avatar vendor, and an LLM
  for narration generation each land behind an existing adapter without a
  rewrite - and the deterministic path stays as the fallback.
* **Scaling content via the catalogue shape.** `services/planner/concepts.py`
  is a data structure, not code. New chapters are authoring work, and could be
  LLM-drafted then human-reviewed - keeping the grounding discipline.

### Threats

* **Incumbents with vastly more content and distribution.** Khanmigo, Google
  LearnLM, BYJU'S. We cannot win on content volume; we can only win on the
  pedagogy of the correction loop.
* **"Good enough" general chatbots.** Many learners will just ask a free
  general-purpose model. Our answer has to be that it cannot tell you *why* you
  are wrong or track it over time - which requires we keep that gap real.
* **Adding an LLM could destroy the trust story.** The moment generation enters
  the loop, fabricated citations and confidently wrong explanations become
  possible. The grounding discipline must be enforced in code, not in prompts.
* **Content licensing.** The bundled corpus quotes NCERT material. Fine for a
  hackathon; a commercial product needs licensed or original content.
* **Unit economics at scale.** Avatar and TTS generation per learner per scene
  is expensive. The current fallback-first design mitigates this, but a
  video-heavy product would not.
* **Rule-based diagnosis will not scale to real classrooms.** The thing that
  makes the demo reliable is also the thing that breaks first under real
  student language. This is the top technical risk to retire next.

### What this SWOT implies

The honest read: **the pedagogy is ahead of the engineering, and the
engineering is deliberately ahead of the AI.** The correction loop is the
defensible idea and it is fully built; the content catalogue and the
rule-based diagnosis are the two things that must generalise next, in that
order. The single highest-value next step is replacing cue-word classification
with a semantic classifier *while keeping the deterministic path as fallback* -
that retires the biggest weakness without giving up the biggest strength.

---

## 5. Verified demo script (3-4 minutes)

Every step below was executed against the running product.

1. **Onboarding** - Topic *Ohm's Law*, beginner, Hinglish, 20 minutes.
2. **Source analysis** - NCERT Class 9 Ch.12, 8 sections, 6 pages,
   `Source-grounded`.
3. **Plan** - 7 scenes, each showing its concept and cited page; the checkpoint
   is marked.
4. **Teaching** - concept map, then an animated circuit with current flow, then
   the `V = IR` equation steps. Open **Evidence** on any scene to show the
   page and the quoted excerpt.
5. **Checkpoint** - *"Agar voltage same rahe, aur hum resistance badha dein,
   toh current ka kya hoga?"* Answer **"Current increases when resistance
   increases."**
6. **The flagship moment** - diagnosis `direct-proportionality confusion`,
   supportive feedback, and the progress counter moves from **Scene 6/7 to
   Scene 7/8**: a new repair scene now exists that did not before.
7. **Repair** - equation transformation, water-pipe analogy, descending graph.
8. **Retry** - answer *"resistance badhne se current kam hoga"*. Accepted as
   correct despite containing an "increase" cue word, because the premise
   clause is stripped before classification.
9. **Report** - 77%, misconception `resolved`, revision actions, next topic
   *Series and Parallel Circuits*.

Optional: switch the language selector to English mid-lesson - the narration
changes, the scene position and all progress are preserved.

---

## 6. Remaining work (Task 3, not attempted here)

Task 3 (judging polish, RAG confidence surfacing, reliability, licence
disclosure) was out of scope for this change. The pieces of it already present
as a by-product are grounding status and the fixture fallback; the rest -
accessibility audit, licence disclosure file, pre-cached demo assets, the wider
test matrix logging - remain open.
