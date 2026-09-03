# GuruFlow: rubric-aligned SWOT and video/animation plan

Assessed against **Round 2 Technical Assessment - AI Teacher: Build a Human-Like
AI Educator That Teaches Through Video**, at commit `02d5c1c` (current `main`).

Every claim below was verified by installing, running and driving the product,
not read off the source. Where the verdict is harsh, the evidence is cited.

---

## 0. Naming clash worth fixing first

The repo's `docs/CODEX_TASKS_V2.md` (since removed, once its sprints were
complete) defined its own "Task 1 / Task 2 / Task 3"
as internal team sprints. **These are not the hackathon's Task 1 and Task 2.**

| | Hackathon PDF | Repo `CODEX_TASKS_V2.md` |
| --- | --- | --- |
| Task 1 | **AI Teaching Video** - avatar + natural voice + visuals | Day 1+2 foundation (frontend, backend, contracts) |
| Task 2 | Interactive and adaptive teacher | Adaptive teaching loop |

The team has effectively completed the repo's Task 1 and Task 2, and the
hackathon's **Task 2**. The hackathon's **Task 1 - the teaching video - is the
one that is not done.** That single gap is where most of the lost marks are.

---

## 1. Verified state of the build

| Check | Result |
| --- | --- |
| `pip install -r apps/api/requirements.txt` | **FAILS** - `chroma-hnswlib` has no Windows wheel and needs a C++ compiler. The abort leaves `python-multipart` uninstalled, so **pytest cannot even collect** |
| Tests after installing deps manually (minus chromadb/sentence-transformers) | **98 passed** |
| `POST /tts` (the "real neural voice" path) | **HTTP 500** - `edge-tts` gets `403` from Microsoft's undocumented Bing endpoint |
| Avatar in the running app | Inline **SVG**. `MediaAdapter` hardcodes `FallbackAvatarProvider` with `videoUrl = null`, which always throws |
| D-ID provider | **Unreachable dead code** - nothing imports `provider-factory.js` from the web app, `process.env` does not exist in a browser, and `DID_API_KEY` is absent from `.env.example` |
| `<video>` element anywhere in the frontend | **None.** Even a working avatar would have nowhere to play |
| Status badge a judge sees in the classroom | `DEGRADED - CAPTIONS ONLY` |
| `/health` | `"gemini": false`, `"vectorRag": false` |

The teaching loop itself is genuinely good. The *video* half of the brief is
not implemented, and two of the three things that would deliver it (edge-tts,
D-ID) are currently broken or unwired.

---

## 2. Rubric scoring

Scored as a judge would see it on a fresh clone with no API keys.

| Evaluation area | Weight | Est. | Why |
| --- | --- | --- | --- |
| Human-Like Teaching and Adaptation | 20 | **16** | Full Understand-Plan-Explain-Question-Evaluate-Adapt loop, misconception diagnosis, spliced repair scene, retry, mastery, report. Lost marks: no free-form follow-up Q&A (explicitly required by Task 2), only two misconceptions, one chapter |
| AI/ML and LLM Implementation | 15 | **8** | Gemini 2.5 Flash is wired for planning and evaluation, but it is **optional and off by default**. With no key the product is pure rules and `/health` reports `gemini: false`. With a key: ~12 |
| RAG and Knowledge Grounding | 15 | **11** | Real strength: page-level citations, Evidence drawer, explicit `general_knowledge` labelling instead of fabricated citations. Lost marks: vector RAG is opt-in **and does not install**, so the shipped default is keyword overlap |
| **AI Teaching Video Generation** | 15 | **4** | **No video is generated.** Animated SVG scenes are not video. The UI has no `<video>` element. The brief says a talking avatar over generated text is insufficient - we do not even reach that bar |
| Multilingual Capability | 10 | **6** | English/Hindi/Hinglish with mid-lesson switching that preserves progress, and formulae preserved verbatim - genuinely good. Lost marks: only three languages, and "English textbook to Hindi teaching" is not real translation, it selects hand-authored narration from the catalogue |
| Voice and AI Avatar | 10 | **3** | TTS endpoint returns 500. Avatar is a static SVG with a CSS mouth. No lip sync, no natural voice |
| Innovation and Originality | 5 | **4** | The misconception-repair loop is a real differentiator and is test-guarded |
| User Experience and Interface | 5 | **5** | Polished landing page, learning-path rail, karaoke captions, responsive |
| Documentation and Technical Presentation | 5 | **5** | READMEs, `THIRD_PARTY_DISCLOSURE.md`, `INTEGRATED_PRODUCT.md`. Above hackathon average |
| **Total** | **100** | **~62** | |

**The arithmetic that matters:** Video (15) + Voice/Avatar (10) = **25 marks,
currently earning about 7.** Fixing those two is worth more than every other
possible improvement combined.

---

## 3. SWOT

### Strengths

* **The adaptive loop is real and machine-checked.** A wrong answer splices a
  new repair Scene into the lesson (7 scenes becomes 8) and routes back for a
  retry. `test_answer_changes_the_next_scene` fails the build if adaptation
  degrades into cosmetic feedback. This serves the heaviest rubric line (20
  marks) and is exactly the "genuine AI-driven teaching capability" the jury
  says it will look for.
* **Grounding honesty.** Page-level citations, a visible Evidence drawer, and a
  refusal to cite weak matches. The rubric asks to "minimize unsupported or
  hallucinated information"; the system labels ungrounded content instead of
  inventing sources.
* **Graceful degradation everywhere.** Gemini absent, vector RAG absent, TTS
  down, avatar unconfigured - the lesson still completes. That is why the demo
  never dies mid-presentation.
* **Multilingual switching preserves learner state** - mastery, attempts and
  diagnosed misconceptions survive a language change, and equations are never
  translated.
* **98 automated tests** across planner, evaluation, RAG, memory and the
  end-to-end path, plus JS suites for contracts, media and visuals.
* **Documentation is genuinely strong** - a 5/5 area most teams lose marks on.

### Weaknesses

* **No teaching video. This is the headline weakness** and it is a *mandatory*
  requirement (item 6 of section 17), not an optional one.
* **Voice is broken in practice** - `edge-tts` depends on an undocumented
  Microsoft endpoint that now returns 403. Depending on an unofficial endpoint
  was always fragile.
* **The avatar is decorative, and the D-ID path is dead code** that cannot be
  reached from the browser and is not documented in `.env.example`.
* **The dependency install fails on Windows**, which also breaks the test
  suite. A judge following the setup instructions verbatim hits an error.
* **The LLM is optional and off**, so the default experience is rule-based -
  awkward for a 15-mark "AI/ML and LLM Implementation" line.
* **No free-form follow-up questions.** Task 2 explicitly requires answering
  follow-ups while maintaining lesson context. There is no such affordance.
* **Content is one chapter.** Any other topic degrades to "general knowledge"
  with no real teaching content, which undercuts "teach any topic".
* **PyMuPDF is AGPL-3.0** - correctly disclosed, but a commercial licensing
  landmine.

### Opportunities

* **Programmatic animation is a better fit than any avatar vendor** (section 4).
  It converts the weakest rubric line into a differentiator and costs nothing
  per lesson.
* **A local neural TTS removes the 403 class of failure permanently** and
  strengthens the "runs 100% offline" claim rather than contradicting it.
* **The misconception library is the defensible asset** - a curated
  misconception to diagnostic to alternative-representation map is expensive to
  build, improves with usage, and is far harder to copy than a RAG pipeline.
* **Report data already supports a teacher/class analytics view** - the B2B
  product, needing no new modelling.
* **Adding two or three more Indian languages is cheap** (the catalogue is
  data) and the rubric explicitly awards "additional consideration" for it.

### Threats

* **The jury's stated disqualifier is aimed at our gap.** "A basic chatbot, a
  static video, or a talking avatar reading a generated script will not be
  considered equivalent to an adaptive AI Teacher." We are safe on adaptivity
  and unsafe on video: we have no video at all.
* **Live-demo risk from cloud dependencies.** The D-ID free trial is five
  minutes of video in total; edge-tts is already blocking. Anything cloud-based
  can fail during judging.
* **Competing teams will show a talking avatar.** Even a mediocre one scores on
  two lines where we currently score near zero.
* **Adding an LLM late could break the grounding story** if generation is not
  constrained to retrieved sources.
* **Rule-based diagnosis will not survive real student phrasing at scale.**

---

## 4. How to generate original video and animation, without D-ID

### 4.1 The key judgement: do not use a generative video model for teaching content

Open text-to-video models - **Wan 2.x, HunyuanVideo, LTX-Video, CogVideoX,
Mochi-1**, or **Stable Diffusion + AnimateDiff** - produce short, attractive,
*semantically approximate* clips. They cannot draw a correct circuit, a correct
`I = V/R` curve, or correctly labelled axes. For an AI **teacher**, a
beautiful-but-wrong diagram is worse than no diagram: it silently destroys the
grounding story that is currently our strongest asset.

**Use them only for a decorative three-to-five second intro sting or B-roll,
never for explanatory content.** Say so explicitly in the documentation - a
jury reads that as engineering judgement, not as an absence.

### 4.2 Recommended: Manim renders the lesson, Piper speaks it

Both are free, offline, deterministic and cacheable. This is the highest-ROI
change available.

**Animation - Manim Community Edition** (MIT, Python)

Manim is purpose-built for exactly what this product teaches: equations
transforming step by step, graphs drawing themselves, labelled diagrams. The
`VisualSpec` contract already carries everything a Manim scene needs, so this
is a renderer swap, not a redesign.

| `VisualSpec.type` | Manim construction |
| --- | --- |
| `equation` | `MathTex` per step plus `TransformMatchingTex` between them - the `V = IR` to `I = V/R` transformation animates itself |
| `graph` | `Axes` plus `plot` with `Create`, so the descending I-vs-R curve draws live |
| `circuit` | `VGroup` of shapes with a dot animated along the loop for current flow |
| `concept_map` | Nodes as `RoundedRectangle`, edges as `Arrow`, revealed with `LaggedStart` |
| repair scene | Split screen: equation transform beside the water-pipe analogy narrowing while the flow arrow thins |

That last row matters most. **A repair scene rendered as its own video is the
flagship feature made visible in exactly the deliverable the rubric weighs.**

```bash
pip install manim          # plus ffmpeg on PATH
```

**Voice - Piper TTS** (MIT, rhasspy/piper)

Replaces `edge-tts` and its 403. Small ONNX models, CPU real-time, fully
offline, no key. Ships Hindi (`hi_IN`) and Indian English (`en_IN`) voices;
Hinglish is covered acceptably by running romanised text through the Hindi
voice.

Fallback chain: **Piper, then gTTS (network, robotic), then captions only.**
Keep `edge-tts` last, since it is unofficial and evidently unreliable.

### 4.3 Optional: a real talking head, locally

If a human-like face is wanted for the avatar marks, prefer open models over
D-ID and **pre-render rather than generate live**:

| Model | Licence | Note |
| --- | --- | --- |
| **SadTalker** | Apache-2.0 | One photo plus audio to talking head. Best licence/quality balance. Slow on CPU, so pre-render |
| **LivePortrait** | MIT | Expressive portrait animation, fast |
| **MuseTalk** | Open weights | Near real-time lip sync, needs CUDA |
| **Wav2Lip** | **Check carefully** | Several released weights are research/non-commercial only - a licensing trap |

Practical approach: render **one** twenty-second SadTalker clip per language
for the lesson intro, loop a subtle idle clip elsewhere, and let Manim carry
the teaching. This buys the "human-like avatar" mark without a per-scene cost
or a live-demo dependency.

### 4.4 Proposed pipeline

```
Scene (contract JSON)
  |
  +-- visual    -> Manim scene builder -> scene.mp4   (silent, 1280x720)
  +-- narration -> Piper TTS           -> scene.wav
  +-- captions  -> WebVTT
  |
  +-> ffmpeg mux (video + audio + optional burned-in captions)
        -> demo-assets/<sha256(scene)>.mp4            [cached]
```

Cache on a hash of `{narration, visual, language}` so a scene renders once
ever. `services/media/src/scene-cache.js` already exists for this.

### 4.5 Concrete work items, in priority order

1. **Fix the install.** Move `chromadb` and `sentence-transformers` into an
   optional `requirements-vector.txt` or a pip extra. A fresh clone must
   `pip install` and `pytest` cleanly. *(Blocks everything; ~15 minutes.)*
2. **Replace edge-tts with Piper** behind the existing `TTSProvider` seam,
   keeping the fallback chain. *(Turns a 500 into the voice mark.)*
3. **Add a `<video>` element** to the teacher panel with the SVG avatar as
   `poster`, so video has somewhere to play at all.
4. **Build the Manim renderer** for `equation`, `graph`, `circuit`,
   `concept_map` and the repair scene. Add `GET /scenes/{id}/video`.
5. **Pre-render the seven demo scenes plus the repair scene** into
   `demo-assets/` and commit them. The demo then plays instantly and offline,
   which is also the safest possible live demo.
6. **Delete or wire the D-ID provider.** If kept, add `DID_API_KEY` to
   `.env.example` and reach it through `provider-factory.js`; otherwise remove
   it so reviewers do not find dead code.
7. **Ship with a Gemini key configured** for judging, so `/health` says
   `gemini: true`.
8. **Add free-form follow-up Q&A** grounded in the retrieved sections - closes
   the one explicit Task 2 requirement currently missing.
9. Add two more Indian languages (a data-only change in the concept catalogue).

Items 1-5 plausibly move the score from ~62 to ~80, and items 1-3 alone are
under a day's work.

### 4.6 What to say in the demo video

Lead with the repair moment: wrong answer, named misconception, a *new*
animated scene appearing, correct retry, report. That is the part no competitor
will have. Then open the Evidence drawer to prove grounding. Keep the
"generative video is deliberately not used for explanatory content" line in the
narration - it reads as judgement, not as a missing feature.
