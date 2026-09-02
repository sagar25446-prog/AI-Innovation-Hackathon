# @guruflow/media

Media rendering engine, mock provider infrastructure, fallback guarantees, and deterministic scene caching for GuruFlow AI teacher platform.

## Architecture

This package provides provider-neutral interfaces, resilient multimodal rendering, latency/error simulation, and instant deterministic replay caching for GuruFlow lessons.

### Key Modules

- `src/interfaces.js` — Core JSDoc definitions and abstract classes (`TTSProvider`, `AvatarProvider`, `SceneRenderer`, `MediaResult`).
- `src/mock-tts-provider.js` — Configurable mock TTS provider with word-count based duration calculation, MD5 URL hashing, latency simulation (`latencyMs > 2000ms`), and failure toggling (`shouldFail: true`).
- `src/mock-avatar-provider.js` — Configurable mock avatar video provider with thumbnail generation, duration propagation, latency simulation, and error simulation.
- `src/scene-renderer.js` — `DefaultSceneRenderer` implementing full multimodal rendering with robust null safety, visual canvas pass-through (`circuit`, `equation`, `graph`, `concept_map`, `diagram`), and graceful fallback guarantees:
  - **TTS Failure**: Falls back to text-only captions (`audio.fallback: true`, `audio.url: null`, `status: 'degraded'`).
  - **Avatar Failure**: Falls back to static teacher image placeholder (`video.fallback: true`, `video.thumbnailUrl: 'assets/teacher-placeholder.svg'`, `teacherPanel.type: 'image'`, `status: 'degraded'`).
  - **Dual Failure**: Zero-crash guarantee returning valid `MediaResult` with intact captions and placeholder visual.
- `src/scene-cache.js` — In-memory deterministic descriptor cache (`SceneCache`) with alias normalization, mutation protection, and pre-seeded demo entries.
- `src/cached-descriptors.js` — Pre-generated instant descriptors for demo teaching scenes (`scene-1-intro`, `scene-2-voltage`, `scene-3-resistance`, `scene-5-ohms-law`), advance scene (`scene-advance-circuits`), and 3-in-1 compound repair scene (`scene-repair-ohms-law`) across English, Hindi, and Hinglish with strict mathematical formula invariance ($V=IR$, $I=V/R$, $10/5=2\text{A}$).
- `src/provider-factory.js` — Factory helpers for creating providers, cache, and renderer instances.

## Usage

```javascript
import {
  createTTSProvider,
  createAvatarProvider,
  createSceneRenderer,
  SceneCache,
  getCachedDescriptor
} from '@guruflow/media';

// 1. Instant Cached Lookup
const cachedScene = getCachedDescriptor('scene-5-ohms-law', 'hinglish');
console.log(cachedScene.status); // 'ready'

// 2. Dynamic Scene Rendering with Providers & Fallbacks
const tts = createTTSProvider({ latencyMs: 50 });
const avatar = createAvatarProvider();
const renderer = createSceneRenderer();

const scene = {
  id: "scene-5-ohms-law",
  narration: "Ohm's Law states that V = I * R.",
  visual: {
    type: "circuit",
    data: { voltage: "10V", resistance: "5Ω", current: "2A" }
  },
  durationSeconds: 20
};

const mediaResult = await renderer.renderScene(scene, {
  ttsProvider: tts,
  avatarProvider: avatar,
  language: 'hinglish'
});
```

## Running Tests

Run the built-in Node.js test runner:

```bash
node --test test/*.test.js
```
