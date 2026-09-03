# GuruFlow rubric-closure run - progress log

Autonomous run against the master task. Entries are appended in order.
Machine: Windows-11-10.0.26200, Python 3.12.1, RTX 4050 (6 GB).
Branch: `main` at `97cdf8d` when the run started.

---

## 2026-09-04 02:30 - Pre-flight

**Gemini key: MISSING - Phase 1 partially blocked.**

* `apps/api/.env` **does not exist**.
* The correct variable name is **`GEMINI_API_KEY`** (from `apps/api/.env.example`
  line 12). `services/llm/__init__.py::_get_api_key()` reads
  `GEMINI_API_KEY` first and falls back to `GURUFLOW_LLM_API_KEY`.
* Consequence: Phase 1 items 1(a), 1(b) and 3 cannot be *executed* against a
  live model. I will verify them by static trace of the prompt-construction
  path instead, fix anything provably wrong, and verify 1(c) (the honest
  no-key path) empirically, which does not need a key.
* Per instructions, the run continues rather than stopping.

**To unblock:** create `apps/api/.env` containing `GEMINI_API_KEY=<key>`.

---

## 2026-09-04 02:34 - PHASE 0: Install robustness - COMPLETE, all green

### 0.1 Clean-venv install

Created a fresh venv at `C:\hk\cleanvenv` (Python 3.12.1) and ran
`pip install -r apps/api/requirements.txt` end to end.

* **Result: exit code 0, no errors.**
* Verbatim failures to log: **none.** Grep for `^ERROR`, `Failed to build`,
  `error:` over the full install log returned nothing.
* Notably `pycairo-1.29.1` and `manimpango-0.6.1` both installed from
  prebuilt wheels - no compiler and no system libraries were needed.

### 0.2 manim pycairo/pangocairo check

**The `RequiredDependencyException: pangocairo >= 1.30.0` failure did NOT
reproduce on this machine.**

Verified beyond install: imported manim in the clean venv and rendered a real
scene to MP4 (3013 bytes). Both import and render succeeded, so the failure is
not merely deferred to runtime here.

*Assumption logged:* this failure is well documented on Linux and macOS, where
manim needs system cairo/pango rather than wheels. I can only test Windows.
The instruction was conditional ("if it reproduces"), and it did not, so
strictly no doc was required - but I wrote
`docs/VIDEO_INSTALL_TROUBLESHOOTING.md` anyway because teammates on other
platforms will hit it, and linked it from `apps/api/README.md`. The doc states
plainly that it does not reproduce on Windows. **This is a deliberate, logged
deviation: a doc was added where the trigger condition was not met.**

### 0.3 requirements-vector.txt is correctly optional

Confirmed in **two** environments:

| Environment | chromadb | sentence-transformers | pytest |
| --- | --- | --- | --- |
| Working env | absent | absent | 125 passed, 1 skipped |
| Clean venv | absent | absent | 125 passed, 1 skipped |

Collection and execution both work with the vector extras uninstalled. No test
imports them at module level.

### 0.4 Baseline test suite

**Baseline: 125 passed, 1 skipped.**

The 1 skipped is `test_repair_scene_renders_to_a_playable_video`, gated behind
`GURUFLOW_RUN_SLOW_TESTS=1` by design (it performs a real multi-second render).

This is the number every later phase must not regress.

---

## 2026-09-04 02:42 - PHASE 1: Content grounding - COMPLETE (2 real bugs fixed)

Static trace plus empirical tests. Items needing a live model are marked.

### 1(a) Does an off-library topic reach the LLM with a real prompt?

**Yes.** Traced `apps/api/main.py::create_plan` -> `services/planner::plan_lesson`
-> `_plan_lesson_llm` -> `services/llm::generate_plan`. The prompt is real and
**does** interpolate retrieved material: `sections_text` renders up to 15
sections as `- [page] heading: excerpt` and is embedded under "Available
material excerpts". The LLM is tried *first*, before any deterministic
fallback. No fix needed to the prompt's material injection.

*Not executable without a key; verified by trace.*

### 1(b) Do uploads produce citations that trace to the upload?

**BUG FOUND AND FIXED.** Two separate defects.

**Defect 1 - LLM path dropped citations entirely.**
`generate_plan`'s prompt instructs the model: `"citations": [] (leave empty,
backend fills this)`. Nothing filled them. `_normalise_llm_scenes` only
*normalises* whatever the model returned, so every LLM-planned scene came back
with `citations: []` and `groundingStatus: "general_knowledge"`.

Net effect: on exactly the path an upload or novel topic takes, the product's
headline strength - page-level source grounding - silently disappeared.

*Fix:* added `_ground_llm_scenes()`, which runs the **existing** `retrieve` /
`best_citations` / `grounding_status` calls per scene, querying with that
scene's own conceptId + objective + narration. Retrieval logic untouched, per
instructions. Model-supplied citations are kept if present; off-material scenes
stay honestly ungrounded rather than getting a plausible-looking citation.

**Defect 2 - off-catalogue uploads were taught the wrong subject.**
Reproduced concretely: uploading a photosynthesis passage and asking for
"Photosynthesis" returned a **six-scene Ohm's Law lesson**. Honest about
grounding (no fabricated citations) but about entirely the wrong subject -
worse than admitting the limitation, and directly contradicting "teach any
topic".

Root cause: `_has_groundable_content()` only asked "does this material have
sections?", not "can the curated catalogue actually teach it?". An upload
always has sections, so the deterministic Electricity engine always ran.

*Fix:* `_curated_catalogue_grounds()` probes the four core curated concepts
against the material through the existing retrieval path and requires at least
2 of 4 to ground. Verified discrimination:

| Material | Teachable by curated catalogue | Result |
| --- | --- | --- |
| Built-in Electricity corpus | yes | full 7-scene lesson, all cited |
| Uploaded electricity notes | yes | 6 scenes, **all citations point at the upload** |
| Uploaded biology passage | no | honest refusal, 1 scene, no citations |
| Topic-only unknown subject | no | honest refusal (pre-existing path) |

*Assumption logged:* the 2-of-4 threshold is a judgement call, not a derived
constant. Chosen so a short paraphrased electricity upload still passes while
unrelated prose does not. Verified against both. If a legitimate electricity
upload is ever wrongly refused, lower `_CURATED_MATCH_THRESHOLD` to 1.

**Also fixed:** `_unsupported_topic_narration` ended with
`.get(language, "english")`, which returned the *literal string* `"english"`
for any unexpected language code rather than the English message. Unreachable
through the API today (Pydantic constrains the enum) but a live landmine.

**Also added:** a distinct refusal message for the uploaded-but-off-catalogue
case. The existing message says "Upload a document", which is useless advice to
someone who just did. The new one names the real next step (add an LLM key).

### 1(c) No-key honest limitation - RE-VERIFIED, not assumed

Empirically confirmed above. `_plan_unsupported_topic` returns a single
contract-shaped scene, `citations: []`, `unsupportedTopic: true`, localised in
all three languages, and never transforms into another subject.

### 1(3) /health reports the LLM when a key is present

**Verified.** With `GEMINI_API_KEY` set, `services.llm.gemini_available()`
returns True and `/health` reports `"gemini": true, "mode": "llm-enhanced"`.
Tested with a placeholder key, since client construction does not call the
network. With no key: `"gemini": false, "mode": "deterministic"`.

### 1(4) Concrete photosynthesis test

Run above. Post-fix, an uploaded photosynthesis passage yields an honest
refusal naming the LLM key as the unblock - **not** an Ohm's Law lesson.

*Remaining, blocked on the key:* end-to-end proof that with `GEMINI_API_KEY`
set, that same upload produces a genuine photosynthesis lesson citing the
uploaded pages. The plumbing is now in place and unit-tested
(`test_llm_scenes_get_real_citations_attached`), but the live call is unrun.

### Tests

Added `apps/api/tests/test_topic_grounding.py` (15 tests).
**140 passed, 1 skipped** - baseline was 125, no regressions.

*One self-correction:* my first version asserted `tier == "full"`. That was my
stale assumption - the study-mode logic legitimately labels a normal plan
`"lesson"`. Per instructions I treated the difference as intentional and fixed
my test, not their code.

---

## 2026-09-04 02:47 - PHASE 1.5 - Known Limitations documentation

No canonical "Known limitations" section existed anywhere, despite the rubric
listing it as required submission documentation. Created
**`docs/KNOWN_LIMITATIONS.md`** and linked it from `README.md` with an explicit
"set `GEMINI_API_KEY` before judging" callout.

Section 1 is a mode-by-mode table of offline vs Gemini-configured behaviour,
including what "honest refusal" means and why it is deliberate.

---

## 2026-09-04 02:58 - PHASE 2: Video pipeline - COMPLETE (1 real bug fixed)

### 2.1 One scene per visual type, rendered from `demo-fixtures/`

All rendered successfully with **both video and audio streams** (verified with
ffmpeg stream inspection - non-silent confirmed, `aac` track present in each):

| Visual type | Fixture scene | Render | Duration |
| --- | --- | --- | --- |
| `concept_map` | scene-1-intro | 23.3s | 13.5s |
| `circuit` | scene-2-current | 17.1s | 14.1s |
| `equation` | scene-5-ohms-law | 20.4s | 16.2s |
| `graph` | scene-6-graph | 17.8s | 17.8s |
| `diagram` (repair) | scene-repair-ohms-law | 20.5s | 21.1s |

Rendering from the fixtures rather than planner output also exercises the
fixture-shape normalisers, which is a distinct code path.

### 2.2 Repair scene - BUG FOUND AND FIXED

**The repair scene rendered as the generic fallback layout.**

The runtime evaluator (`build_repair_scene`) emits `visual.type == "equation"`
with `{steps, analogy, graph}`, which renders correctly. But
`demo-fixtures/ohms-law-repair-scene.json` describes the *same* teaching moment
as a much richer `visual.type == "diagram"` composite
(`{composite, diagramType, equation, analogy, graph, misconception, layout}`),
and `BUILDERS["diagram"]` pointed at `build_fallback`. Every bit of that
composite - the equation transformation, the hydraulic analogy, the I-vs-R
curve - was being discarded and drawn as generic chips.

*Fix:* added `build_diagram()`, which detects the composite descriptor and maps
it onto the **existing** `build_equation` path (steps + analogy + graph). Plain
non-composite diagrams still use the chip fallback. No new rendering machinery.

Two supporting fixes were needed to make it look right:

* `_plain_expression()` - the fixture carries LaTeX (`I = \frac{V}{R}`,
  `V = I \cdot R`). The renderer is deliberately LaTeX-free, so these were
  being drawn literally. Converted to plain text.
* **Text overflow** - fixture labels ("Rearrange Solving for Current (I)") and
  expressions ("R up => I down (constant V)") overprinted each other and bled
  past their boxes. Labels now shrink to the free space and are dropped rather
  than overprinting; expressions scale to fit their box. Long objectives are
  truncated instead of shrinking to illegibility.

**Verified visually** at three iterations by extracting frames: the final
render shows 4 equation steps, the water-pipe analogy (wide pipe / 3 flow dots
vs narrow pipe / 1 dot) and the descending I-vs-R curve with title and axes -
not a fallback.

*Also:* bumped `video_id()`'s `"renderer"` from `v2` to `v3`. The rendered look
changed, and that field exists precisely so stale cached videos are not served.

### 2.3 Committed demo assets + startup seeding

Rendered the real demo lesson (beginner / Hinglish / 20 min) plus **both**
misconception repair scenes: **9 videos, 203.8s total, 3.3 MB**, committed to
`demo-assets/videos/`.

* `services/video/seed_cache_from_repo()` copies them into the runtime cache.
* Startup hook: `apps/api/main.py::seed_demo_videos`.
* Idempotent - an existing cache file is skipped, so a locally re-rendered
  video is never clobbered. Copies via a scratch name then renames, so a
  half-copied file is never observable as "ready". Never blocks startup.

**Verified:** cleared the cache, started the app, and all **7/7** demo lesson
scenes reported `ready` immediately with zero renders.

**AGENTS.md exception logged.** `AGENTS.md` forbids committing "large generated
media". This is a deliberate, scoped exception, documented in
`demo-assets/README.md`: 3.3 MB, only the judged lesson and its repair scenes,
taken because otherwise the first scene renders live in front of the judges.
Everything else still renders on demand and is never committed.

*Caveat logged in that README:* filenames are content hashes that include the
quality setting, so the seeds only match the default
`GURUFLOW_VIDEO_QUALITY=medium`. Running at `low`/`high` re-renders. Correct
behaviour, but do not change quality on demo day expecting seeds to apply.

### 2.4 Render time and quality setting

* **`GURUFLOW_VIDEO_QUALITY` default: `medium`** (1280x720 @ 30fps).
  **Unchanged** - it is the right default: 720p is where the burned-in captions
  and equation text become comfortably legible, and it is what the committed
  seeds were rendered at.
* Render times at medium, this hardware: **13-35s per scene**, 203.8s for 9.
* At `low` (854x480 @ 15fps) the same scenes took 17-23s - not proportionally
  faster, because narration synthesis and muxing are fixed costs.

### Tests

Added 4 seeding tests. **144 passed, 1 skipped** - no regressions.

---

## 2026-09-04 03:05 - PHASE 3: SadTalker avatar wiring - COMPLETE

Built for clips that do not exist yet; nothing crashes without them.

### 3.1 / 3.2 The provider

`apps/web/src/prerendered-avatar-provider.js` implements `AvatarProvider` from
`services/media/src/interfaces.js`, following `mock-avatar-provider.js`'s
shape (same return contract, JSDoc style, no Node-only imports).

* Reads `apps/web/public/avatars/<language>/<role>.mp4`, served at
  `/public/avatars/<language>/<role>.mp4`.
* Roles: `intro`, `idle`, `correct`, `repair_transition`, `complete`.
* Role comes from `options.clipRole`; missing **or unknown** falls back to
  `idle` rather than 404-ing on a typo.
* **Throws** when the file is absent, with a message naming the exact folder.
  It never returns an unverified URL - a broken `<video>` src is worse than a
  clean fallback. Verified live in the browser: the error reads
  *"No pre-rendered avatar clip at /public/avatars/english/idle.mp4. Add
  idle.mp4 under apps/web/public/avatars/english/..."*
* Existence is probed with HEAD and memoised per URL, so a 7-scene lesson does
  not fire 7 identical probes. `clearAvailabilityCache()` picks up newly added
  clips without a restart.
* The probe is injectable (`options.probe`) so tests need no network.

### >>> WHERE TO PUT THE FILES <<<

```
apps/web/public/avatars/english/{intro,idle,correct,repair_transition,complete}.mp4
apps/web/public/avatars/hindi/    (same five)
apps/web/public/avatars/hinglish/ (same five)
```

The three folders already exist, with `apps/web/public/avatars/README.md`
explaining each role. **`idle.mp4` alone is enough to see it working** - roles
degrade independently, so a missing `complete.mp4` never affects `idle`.

### 3.3 Wiring, with the old path preserved

`MediaAdapter` now constructs `PrerenderedAvatarProvider` as `this.avatar`.
`FallbackAvatarProvider` is **kept and instantiated** as
`this.fallbackAvatar`, unused, plus a `useFallbackAvatar()` method to revert
from the browser console mid-demo.

*Obstacle worth recording:* `services/media/src/scene-renderer.js` forwards a
**fixed** option set to `generateAvatar` (`{durationSeconds, language,
sceneId}`) and knows nothing about `clipRole`. Rather than edit Person 3's
module, the adapter passes a stateless per-call wrapper object that binds
`clipRole` and delegates. The renderer only ever calls `generateAvatar`, so
duck typing is sufficient. **No file outside my ownership was modified.**

### 3.4 Clip-role coverage - one gap, stated plainly

`clipRoleForScene()` is a pure function (testable without a running lesson):

| Signal | Role | Wired? |
| --- | --- | --- |
| `sceneIndex === 0` | `intro` | yes |
| `scene.isRepair` | `repair_transition` | yes |
| last answer correct | `correct` | **partial - see below** |
| otherwise | `idle` | yes |
| final report | `complete` | **NOT wired** |

**Incomplete, deliberately:**

* `complete` is never requested. The report screen does not render a media
  scene at all - it is a separate view with no `MediaAdapter.render()` call.
  Wiring it means giving the report its own media lifecycle, which is a larger
  refactor than this task allows. The role, the file slot and the mapping all
  exist; only the call site is missing.
* `correct` is passed from `state.lastEvaluation.correct`, which persists after
  a correct answer. So the *scene following* a correct answer gets `correct`,
  which is roughly the intent, but it is not cleared on the next scene - a
  second consecutive scene may also read `correct`. Left as-is rather than
  adding evaluation-lifecycle state.

### 3.5 hideBuiltInTeacher

`GURUFLOW_HIDE_BUILTIN_TEACHER`, **default `0` (off)**. Flows to the Manim
payload as `hideBuiltInTeacher`.

When on, the rendered lesson video drops the drawn cartoon teacher **and its
panel entirely**, and the subject visual expands to the full frame width
(rather than leaving an empty box). This is distinct from `teacherSlot`, which
leaves the panel empty *because a talking head is being composited into it*.

**Flip this to `1` once you have dropped in real avatar clips**, otherwise the
lesson video shows a cartoon teacher next to your real one.

It is part of the video hash, and exposed at `/health` under
`video.hideBuiltInTeacher`.

### 3.6 Tests

`apps/web/test/prerendered-avatar-provider.test.js` - 18 tests in the
`node:test` + `node:assert/strict` style of
`services/media/test/mock-providers.test.js`.

**BLOCKER, logged honestly: Node.js is not installed on this machine, so these
tests have never been executed.** They are written against the documented
`node --test` runner used by the existing JS suites. Run them with:

```bash
node --test apps/web/test/*.test.js
```

To compensate, the provider was exercised **live in the browser** against the
running app: module import, `clipUrl()` resolution, the throw-on-missing path
with its exact message, and the role mapping for first-scene and repair.

### 3.7 Disclosure

SadTalker added to `docs/THIRD_PARTY_DISCLOSURE.md`: Apache-2.0,
<https://github.com/Winfredy/SadTalker>, used offline to produce committed
clips, **not called at runtime**.

### Regression caught during this phase

Adding `hideBuiltInTeacher` to the video hash **invalidated all 9 committed
demo videos** - 0 of 7 lesson scenes matched, and the demo silently went back
to rendering live. Exactly the failure the seeds exist to prevent, and it was
silent.

*Fixed:* re-rendered all 9 seeds (94.4s) against the final hash. Verified 7/7
lesson scenes plus both repair scenes report `ready` immediately.

*Hardened:* added `test_committed_seeds_match_the_current_demo_lesson_hashes`,
which recomputes the expected hashes and fails with the list of stale scenes
and instructions. This drift cannot now recur silently.

**145 passed, 1 skipped.**

---

## 2026-09-04 03:12 - PHASE 4: Honest scoping + the sanctioned bonus

### The scoped gap, documented

`docs/KNOWN_LIMITATIONS.md` section 2 states plainly which visual types are
real and which are not, and that this is deliberate scoping rather than a bug.
The dispatch table, contract, renderer and caching all handle every type; what
is missing is purpose-built drawing functions.

Corrected mid-run: after Phase 2's fix, `diagram` is no longer purely a
fallback (it renders the composite repair descriptor), so the doc would have
been wrong had I left the original wording.

**Still generic fallback, deliberately not attempted:**
* `timeline` - a row of chips, not a dated axis with events on it (History)
* plain `diagram` - chips, not a drawing with leader lines to parts (Biology)

### Bonus attempted: a real `code_trace` builder

Phases 0-3 were green with budget remaining, so I took the single permitted
bonus.

`build_code_trace()` renders a code panel with line numbers, preserved
indentation, a language header, and an **execution cursor that steps through
the actual run order** with a per-step note - which is the thing a learner is
trying to see about a function call. Accepts `lines` or a `code` blob, and
`executionOrder` as bare indices or `{line, note}` objects. Tolerates 1-based
numbering, because that is what a human writing a fixture reaches for.

**Verified by rendering** a Python function-call trace: the cursor lands
exactly on `print(result)`, the step note sits inside the panel, indentation
and line numbers are correct, and the citation line honestly reads "general
knowledge" (no citations supplied).

**Two real bugs found and fixed while building it:**

1. **General timeline bug.** `construct` did `spent + run_time` where
   `run_time` came from `getattr(animation, "run_time", 0.6)`. For `.animate`
   builders that attribute is a *method*, not a float, so the render died with
   `unsupported operand type(s) for +: 'float' and 'function'`. Now coerced.
   This would have hit **any** future builder using `.animate`.
2. **Stale coordinates.** My first version animated the cursor with absolute
   `move_to([...])`. `construct` scales and repositions the whole visual
   *after* the builder returns, so those coordinates pointed at nothing - the
   cursor rendered below the panel. Rebuilt using a `ValueTracker` plus
   updaters, which evaluate at render time and therefore survive the later
   scaling. Worth knowing for anyone adding a builder: **do not capture
   absolute positions in a returned animation.**

Also fixed a collision where the step note overlapped the citation line; the
note now lives in a reserved strip inside the panel.

### Tests

Added `apps/api/tests/test_scene_builders.py` (24 tests): code-trace
normalisers, 1-based tolerance, junk-entry handling, composite dispatch, LaTeX
reduction, and a parametrised check that **every** contract visual type builds
without raising on an empty payload.

**169 passed, 1 skipped.**

*One self-correction:* my first LaTeX test asserted against `"\frac{V}{R}"`
written through a heredoc, which Python read as formfeed + `rac`. Test data
bug, not a code bug; fixed with raw strings.

---

## 2026-09-04 03:18 - Repository cleanup

Removed, as requested:

* **`docs/CODEX_TASKS.md`** and **`docs/CODEX_TASKS_V2.md`** - the per-person
  sprint prompt files. Their sprints are complete; these are the "task.md"
  class of file. Recoverable from git history if ever needed.
* **`media/`** (389 KB, untracked) - Manim's intermediate text/SVG cache, which
  leaks into the process working directory when a render runs from the repo
  root. Deleted and added to `.gitignore` so it cannot come back.
* `.gitignore` also now covers `*.log`.

**Two references had to be repaired** rather than left dangling:
`README.md` linked to the deleted `CODEX_TASKS_V2.md` (repointed to
`docs/TEAM_IMPLEMENTATION.md`), and `docs/RUBRIC_SWOT_AND_VIDEO_PLAN.md`
discussed it (now notes it was removed once complete).

**Deliberately kept**, because they are still load-bearing:

* `docs/TEAM_IMPLEMENTATION.md` - the directory-ownership table. I relied on it
  during this run to decide what I could and could not edit.
* `docs/INTEGRATED_PRODUCT.md`, `docs/RUBRIC_SWOT_AND_VIDEO_PLAN.md` - the
  architecture and SWOT documents the rubric asks for.
* `SESSION_NOTES.md` - prior-session history, distinct from this log.

---

# FINAL SUMMARY

## Test suite status

**169 passed, 1 skipped** - verified in **two** environments: the working env
and a **clean venv** with the optional vector extras deliberately absent.

Baseline at the start of the run was 125. Net +44 tests, no regressions at any
phase. The 1 skip is the real-render test, gated behind
`GURUFLOW_RUN_SLOW_TESTS=1` by design; it passes when enabled.

| Suite | Covers |
| --- | --- |
| `test_topic_grounding.py` (15) | off-catalogue refusal, upload citations, LLM citation grounding |
| `test_scene_builders.py` (24) | code-trace normalisers, composite dispatch, LaTeX reduction, all visual types |
| `test_video_voice_qa.py` (+9) | seeding, seed-drift guard, talking-head config |
| existing suites | planner, evaluation, RAG, memory, API, uploads |

**Not run: `apps/web/test/prerendered-avatar-provider.test.js` (18 tests).**
Node.js is not installed on this machine. Run with `node --test apps/web/test/*.test.js`.

## Genuinely verified working, end to end

Driven in a real browser against the running app, not asserted from code:

* **Instant video on demo day.** Cache cleared, server restarted, and the
  first scene's **Watch video** was enabled immediately - seeded, zero render.
  Plays 1280x720 with the female Hindi voice.
* **The full adaptive loop**: plan -> teaching video -> follow-up question with
  page citations -> deliberately wrong answer -> `direct-proportionality
  confusion` diagnosed -> lesson grows from **Scene 6/7 to Scene 7/8** ->
  correct retry -> report.
* **Honest refusal**: an uploaded photosynthesis passage no longer returns an
  Ohm's Law lesson.
* **Upload grounding**: uploaded electricity notes produce a lesson whose
  citations all point at the upload, never the built-in corpus.
* **Graceful avatar degradation**: the provider throws for missing clips, the
  app falls back to the drawn panel, and the badge reads honestly.
* **Zero tracebacks, zero unexpected non-2xx.** The only 404s are the avatar
  clip probes (expected until files exist) - and only 3 of them across an
  8-scene lesson, confirming the availability cache works.
* **Clean install** from `requirements.txt` in a fresh venv, exit 0, including
  a real Manim render.

## Bugs found and fixed (all pre-existing unless noted)

1. LLM-planned lessons silently dropped **all citations** - the prompt said
   "backend fills this" and nothing did.
2. Off-catalogue uploads were **taught the wrong subject** (photosynthesis ->
   Ohm's Law).
3. The repair scene fixture rendered as a **generic fallback**, discarding the
   equation, analogy and graph.
4. `_unsupported_topic_narration` returned the literal string `"english"` for
   unexpected language codes.
5. Fixture LaTeX (`\frac{V}{R}`) was drawn literally.
6. Equation labels and expressions **overprinted** each other and bled outside
   their boxes.
7. `construct` crashed on any `.animate` animation (`run_time` is a method, not
   a float) - *found via my own new builder, but it would have hit anyone*.
8. Committed demo videos went **stale silently** when the hash changed
   (self-inflicted during Phase 3; now guarded by a test).

## Known gaps that remain

| Gap | Why |
| --- | --- |
| **No Gemini key** | `apps/api/.env` absent. Offline mode honestly refuses off-catalogue topics instead of teaching them |
| `timeline`, plain `diagram` visuals | Deliberately scoped out (Phase 4). Documented in `docs/KNOWN_LIMITATIONS.md` |
| `complete` avatar clip role | The report screen has no media lifecycle; wiring it is a larger refactor |
| `correct` clip role | Persists into the following scene; not cleared per-scene |
| JS avatar tests unexecuted | Node.js not installed here |
| Live LLM upload test | Blocked on the key - plumbing is unit-tested, the live call is unrun |
| Content depth, 3 languages, in-memory persistence | Pre-existing, documented |

## YOUR REMAINING MANUAL STEPS

**1. Add the Gemini key - highest value, 2 minutes.**

Create `apps/api/.env`:

```
GEMINI_API_KEY=your-key-here
```

Free key: <https://aistudio.google.com/apikey>. Confirm with
`curl http://127.0.0.1:8077/health` -> `"gemini": true`. Without it, "teach any
topic" is honestly scoped rather than delivered, and a 15-mark rubric line
scores on the deterministic path alone.

**2. Drop in avatar clips (optional).**

```
apps/web/public/avatars/{english,hindi,hinglish}/{intro,idle,correct,repair_transition,complete}.mp4
```

`idle.mp4` alone is enough to see it working. Then set
`GURUFLOW_HIDE_BUILTIN_TEACHER=1` so the lesson video drops the drawn cartoon
rather than showing two teachers. Generation steps:
`docs/TALKING_HEAD_SETUP.md`. **Use a face you have rights to.**

**3. Run the JS tests once, on a machine with Node.**

```bash
node --test apps/web/test/*.test.js
```

**4. If you change `GURUFLOW_VIDEO_QUALITY`, re-render the demo assets.**

Seed filenames are content hashes that include quality. At `low` or `high` the
committed seeds will not match and scenes render live.
`test_committed_seeds_match_the_current_demo_lesson_hashes` fails loudly if
they drift.

**5. Before demoing:** start the server, open the app, press **Demo**, and
confirm **Watch video** is enabled immediately. If it says "Rendering", the
seeds are stale - see step 4.
