# GuruFlow Third-Party Disclosure & Offline Fallback Architecture

**Package / Scope**: Media, Visuals & Contracts (`packages/contracts`, `services/visuals`, `services/media`, `demo-fixtures`)  
**Specification Version**: 1.0.0  
**License**: ISC / MIT  

---

## 1. Executive Summary

GuruFlow is designed with a strict **contract-first, zero-external-dependency, offline-deterministic** architecture. The core demonstration paths—including onboarding, structured lesson planning, multimodal scene rendering, interactive checkpoint evaluation, misconception diagnosis, 3-in-1 remediation, and post-lesson diagnostic reporting—operate completely offline without requiring paid cloud APIs, external network access, or proprietary vendor services.

All contracts, visual generators, media simulation engines, and fixture datasets are self-contained, reproducible, and verifiable via Node.js built-in tools (`node --test`, `node --check`, `node packages/contracts/validate.js`).

---

## 2. Third-Party Library & Dependency Disclosure

### 2.1 Core Runtime & Service Packages

| Component / Package | Version / Source | License | Directory / Module | Purpose | Network Requirement |
|---|---|---|---|---|---|
| **Node.js Native Runtime** (`node:crypto`, `node:test`, `node:fs`, `node:path`, `node:assert`) | Node.js v18+ | MIT / Node.js License | Core (`packages/contracts`, `services/media`, `services/visuals`) | Cryptographic MD5 content hashing, file operations, built-in test runner, and assertion framework. | **None (100% Offline)** |
| **@guruflow/contracts** | `1.0.0` (Internal) | ISC | `packages/contracts/` | Source-of-truth JSON Schema (Draft-07), contract validator CLI, and schema documentation. | **None (Zero npm runtime dependencies)** |
| **@guruflow/visuals** | `1.0.0` (Internal) | ISC | `services/visuals/` | Deterministic visual specification generators (circuits, KaTeX equations, Cartesian graphs, concept maps, water-pipe diagrams), render hints, and multilingual captions. | **None (Zero npm runtime dependencies)** |
| **@guruflow/media** | `1.0.0` (Internal) | ISC | `services/media/` | Provider-neutral TTS/Avatar interfaces, mock providers with latency & failure simulation, deterministic scene descriptor cache, and scene renderer. | **None (Zero npm runtime dependencies)** |

### 2.2 Frontend Client-Side Rendering Libraries (Recommended in Render Hints)

GuruFlow's visual engine produces structured JSON visual specifications (`VisualSpec`) coupled with rendering hints (`render-hints.js`). The frontend visual canvas consumes these specifications using open-source, client-side rendering libraries:

| Library | Version / Scope | License | Recommended By | Role in GuruFlow | Fallback Mechanism |
|---|---|---|---|---|---|
| **KaTeX** | `^0.16.x` | MIT License | `services/visuals/src/render-hints.js` (`getRenderHint`, type: `'equation'`) | Fast, client-side LaTeX mathematical typesetting for step-by-step formula derivations ($V=IR \implies I=V/R$). | Raw text / Unicode mathematical expression display (`rawExpression`, `expression`). |
| **SVG / Web Canvas** | W3C Standard | Open Web Standard | `services/visuals/src/render-hints.js` (types: `'circuit'`, `'diagram'`) | High-resolution scalable vector graphics for circuit schematics, wire routing with orthogonal paths, switch states, and hydraulic analogy diagrams. | Static SVG / HTML table fallback representation. |
| **Chart.js** | `^4.x` | MIT License | `services/visuals/src/render-hints.js` (type: `'graph'`) | Responsive Cartesian coordinate graph rendering with hover tooltips and interactive curve plotting for inverse proportionality ($I = 10/R$). | Pre-computed coordinate points table (`points`, `highlightedOperatingPoints`). |
| **D3.js** | `^7.x` | ISC / BSD-3-Clause | `services/visuals/src/render-hints.js` (types: `'concept_map'`, `'timeline'`) | Hierarchical tree and force-directed graph rendering for curriculum knowledge maps. | Structured node/edge lists with coordinate positioning. |
| **Prism.js** | `^1.29.x` | MIT License | `services/visuals/src/render-hints.js` (type: `'code_trace'`) | Syntax highlighting for code trace and execution visualizations. | Plain monospace `<pre><code>` block. |

---

## 3. Media Provider Architecture & Adapter Interfaces

GuruFlow isolates media synthesis behind provider-neutral abstract interfaces (`TTSProvider`, `AvatarProvider`, `SceneRenderer`), preventing vendor lock-in and guaranteeing flawless offline operation.

```
+-------------------------------------------------------------------------+
|                          GuruFlow Scene Engine                          |
+-------------------------------------------------------------------------+
                                    |
                     +--------------+--------------+
                     |                             |
          +--------------------+         +--------------------+
          |    TTSProvider     |         |   AvatarProvider   |
          | (Abstract Class)   |         |  (Abstract Class)  |
          +--------------------+         +--------------------+
                     |                             |
      +--------------+--------------+              +--------------+--------------+
      |                             |              |                             |
+-----------+                 +-----------+  +-----------+                 +-----------+
|  MockTTS  |                 | Cloud TTS |  |MockAvatar |                 |CloudAvatar|
| Provider  |                 | (Optional)|  | Provider  |                 | (Optional)|
| (Offline) |                 |ElevenLabs/|  | (Offline) |                 |HeyGen/D-ID|
|           |                 |Azure/Web  |  |           |                 |/MuseTalk  |
+-----------+                 +-----------+  +-----------+                 +-----------+
```

### 3.1 `MockTTSProvider`
- **Location**: `services/media/src/mock-tts-provider.js`
- **Capabilities**:
  - Offline deterministic speech metadata generation using MD5 hashes (`mock://tts/{language}/{hash}.mp3`).
  - Realistic audio duration computation based on word counts at natural speaking cadence (~150 WPM = 2.5 words/sec).
  - Programmable network latency simulation (`latencyMs` / `delayMs`, supporting delays $>2000\text{ms}$).
  - Configurable error and exception simulation (`shouldFail: true`, custom error messages) for resilience testing.

### 3.2 `MockAvatarProvider`
- **Location**: `services/media/src/mock-avatar-provider.js`
- **Capabilities**:
  - Deterministic video and poster/thumbnail generation (`mock://avatar/{teacherId}/{hash}.mp4`, `thumb_{hash}.jpg`).
  - Configurable teacher personas (e.g. `teacher-dr-sharma`).
  - Programmable network latency simulation (`latencyMs` / `delayMs`).
  - Configurable error simulation (`shouldFail: true`, custom error messages) for zero-crash fallback verification.

### 3.3 Optional Cloud Provider Adapters (Future Spikes)
GuruFlow's interface contracts support future optional cloud adapters:
- **TTS**: ElevenLabs API, Azure Cognitive Services Speech, Google Cloud Text-to-Speech, Web Speech API (`window.speechSynthesis`).
- **Avatar Video**: HeyGen Streaming API, D-ID Agents API, LiveKit WebRTC Agent Starter, local GPU-backed MuseTalk / Wav2Lip.
- **Decision Policy**: Cloud adapters are strictly opt-in via environment variables. When unconfigured, missing, slow, or returning error codes, the system automatically falls back to offline mock providers and deterministic renderers.

---

## 4. Offline Fallback & Reliability Guarantees

GuruFlow enforces a **Zero-Crash Guarantee**: under no circumstance will a lesson terminate, freeze, or crash due to network unavailability, missing API keys, provider timeouts, or external service errors.

```
                              Scene Request
                                    |
                        +-----------v-----------+
                        |  Cache Check Enabled? |
                        +-----------+-----------+
                                    |
                     +--------------+--------------+
              [YES]  |                             | [NO / Miss]
       +-------------v-------------+               |
       |  Pre-seeded Scene Cache   |               |
       |  (Instant 0ms retrieval)  |               |
       +-------------+-------------+               |
                     |                             |
                     | Hit                         v
                     |                  +---------------------+
                     |                  | Invoke TTS & Avatar |
                     |                  +----------+----------+
                     |                             |
                     |              +--------------+--------------+
                     |              |                             |
                     |       [Both Succeed]             [Either/Both Fail]
                     |              |                             |
                     |     +--------v--------+           +--------v--------+
                     |     | Status: 'ready' |           |Status:'degraded'|
                     |     | Video + Audio + |           | Static Image +  |
                     |     | Timed Captions  |           | Text Captions   |
                     |     +--------+--------+           +--------+--------+
                     |              |                             |
                     +------------->+<----------------------------+
                                    |
                        +-----------v-----------+
                        | Returned MediaResult  |
                        | (Guaranteed Complete) |
                        +-----------------------+
```

### 4.1 Granular Fallback Matrix

| Failure Mode | Affected Layer | GuruFlow Automatic Fallback Behavior | Result Status | User-Visible Impact |
|---|---|---|---|---|
| **No Internet / Offline Mode** | TTS & Avatar Cloud APIs | Automatically utilizes local `MockTTSProvider`, `MockAvatarProvider`, and pre-seeded `SceneCache`. | `ready` | Zero latency, immediate lesson presentation with local mock media assets and synchronized captions. |
| **TTS Provider Failure / Throws Error** | Audio Synthesis | `DefaultSceneRenderer` catches exception. Populates `audio.fallback: true`, `audio.url: null`, and supplies timed text captions synchronized to calculated duration. | `degraded` | Visual canvas and captions remain fully operational; learner reads teacher script without interruption. |
| **Avatar Provider Failure / Throws Error** | Talking Avatar Video | `DefaultSceneRenderer` catches exception. Populates `video.fallback: true`, `video.url: null`, and sets `teacherPanel: { type: 'image', thumbnailUrl: 'assets/teacher-placeholder.svg', fallback: true }`. | `degraded` | UI displays high-quality static teacher persona avatar; audio narration and visual canvas operate normally. |
| **Both TTS & Avatar Fail Concurrently** | Audio & Video Generation | Full graceful degradation. Populates `teacherPanel` with static teacher portrait, provides timed captions, and preserves rich interactive `visualCanvas`. | `degraded` | Fully functional text + interactive visual classroom mode. |
| **Simulated Extreme Latency (>2000ms)** | Remote Network Requests | Pipeline gracefully awaits asynchronous resolution without hanging the event loop or blocking downstream state transitions. | `ready` | Media renders correctly once promise completes; cache prevents repeat latency on subsequent views. |
| **Malformed / Null Scene Object** | Scene Ingestion | Robust null-coalescing and default fallbacks in `DefaultSceneRenderer` prevent `TypeError` exceptions, populating valid fallback `MediaResult`. | `ready` / `degraded` | Graceful fallback container rendered without application crash. |

---

## 5. Deterministic Scene Cache & Instant Demo Playback

To ensure instantaneous and repeatable evaluation during live demonstrations and automated testing, GuruFlow provides a deterministic in-memory scene cache (`SceneCache` & `cached-descriptors.js`):

- **Pre-Seeded Catalog**: Includes pre-rendered multimodal scene descriptors for all 6 demo scenes across English, Hindi, and Hinglish:
  1. `scene-1-intro`: Concept Map hierarchical knowledge graph.
  2. `scene-2-voltage`: Potential difference driving force diagram.
  3. `scene-3-resistance`: Conductor resistance opposition diagram.
  4. `scene-5-ohms-law`: Standard closed circuit schematic with ammeter and $V=IR$ derivation.
  5. `scene-advance-circuits`: Multi-resistor series and parallel combination circuit.
  6. `scene-repair-ohms-law`: Compound 3-in-1 remediation panel (KaTeX step derivation + Water-pipe hydraulic analogy + Descending inverse-proportionality graph).
- **Lookup Performance**: $O(1)$ hash map lookup indexed by canonical key (`${sceneId}::${language}`).
- **Immutability Protection**: Deep cloning (`structuredClone` / serialization) prevents unintended runtime cache mutation.

---

## 6. Multilingual Caption Alignment & Invariant Mathematical Formulas

GuruFlow supports multilingual learning in **English**, **Hindi**, and **Hinglish** while enforcing strict mathematical formula invariance:

### 6.1 Formula Invariance Regex Engine
The regular expression `MATH_TOKEN_REGEX` isolates all mathematical formulas, units, and proportionalities:
```javascript
const MATH_TOKEN_REGEX = /(?:[VIR]\s*=\s*[^\s,!?]+(?:\s*[+\-*/×·÷]\s*[^\s,!?]+)*|\b\d+(?:\.\d+)?\s*(?:V|Ω|A|Amperes|Volts|Ohms|L\/s|W|Psi|mm)\b|\b[VIR]\s*=\s*V\/R\b|\bV\s*=\s*I\s*[×*·]\s*R\b|\bV\s*=\s*IR\b|\bI\s*=\s*V\/R\b|\b\d+\/\d+(?:=\d+A)?\b|\b[VIR]\b)/g;
```

### 6.2 Invariant Verification Across Languages
Mathematical tokens are preserved identically across all translations:

| Concept / Equation | English | Hindi | Hinglish | Formula Invariant |
|---|---|---|---|---|
| **Ohm's Law** | `Ohm's Law states that V = I * R.` | `ओम का नियम कहता है कि V = I * R।` | `Ohm's Law kehta hai ki V = I * R.` | **`V = I * R` / `V = IR`** |
| **Current Derivation** | `If we solve for current, I = V/R.` | `यदि धारा निकालें, तो I = V/R।` | `Agar current nikalein, toh I = V/R hota hai.` | **`I = V/R`** |
| **Numerical Example** | `For example, if V is 10V and R is 5Ω, then I = 10 / 5 = 2A.` | `उदाहरण के लिए, यदि V 10V है और R 5Ω है, तो I = 10 / 5 = 2A।` | `For example, agar V 10V hai aur R 5Ω hai, toh I = 10 / 5 = 2A hoga.` | **`10V`, `5Ω`, `2A`, `10 / 5 = 2A`** |
| **Misconception Repair** | `In the formula I = V/R, when Resistance R in the denominator increases, Current I decreases at constant voltage V = 10V.` | `फॉर्मूला I = V/R में, जब प्रतिरोध R बढ़ता है, तो स्थिर वोल्टेज V = 10V पर धारा I घटती है।` | `Isi tarah formula I = V/R mein, jab Resistance R denominator mein badhta hai, toh Current I ghat'ta hai (at constant V = 10V).` | **`I = V/R`, `V = 10V`, `R`, `I`** |

---

## 7. Verification & Compliance Commands

To independently audit and verify all contracts, visual generators, media providers, fallback handlers, and fixture files:

```bash
# 1. Run Media Service unit tests (Mock providers, error/latency simulation, fallbacks, multilingual invariance, caching)
node --test services/media/test/*.test.js

# 2. Run Visuals Service unit tests (Circuits, KaTeX equations, graphs, concept maps, hydraulic analogy, repair specs, captions)
node --test services/visuals/test/*.test.js

# 3. Run Contracts schema & validator unit tests (Schema Draft-07, types inference, boundary validation, fixture tests)
node --test packages/contracts/test/*.test.js

# 4. Validate all canonical demo JSON fixtures against source-of-truth schema
node packages/contracts/validate.js demo-fixtures/*.json

# 5. Verify JavaScript syntax across all source files
node --check services/media/src/*.js services/visuals/src/*.js packages/contracts/*.js

# 6. Verify structural distinction between 3-in-1 compound repair scene and standard teaching scene
node -e '
const fs = require("fs");
const repair = JSON.parse(fs.readFileSync("demo-fixtures/ohms-law-repair-scene.json", "utf8"));
const plan = JSON.parse(fs.readFileSync("demo-fixtures/ohms-law-beginner-hinglish.json", "utf8"));
const scene5 = plan.scenes.find(s => s.id === "scene-5-ohms-law");
if (repair.visual.type === scene5.visual.type && JSON.stringify(repair.visual.data) === JSON.stringify(scene5.visual.data)) {
  console.error("FAIL: Repair scene is structurally identical to Scene 5!");
  process.exit(1);
} else {
  console.log("SUCCESS: Repair scene is structurally distinct from Scene 5.");
}
'
```
