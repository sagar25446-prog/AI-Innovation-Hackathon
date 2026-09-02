# @guruflow/media

This package contains the media and contracts layer for GuruFlow, an AI teacher platform. It provides provider-neutral interfaces and mock implementations for Text-to-Speech (TTS), Avatar generation, and Scene Rendering.

## Structure

- `src/interfaces.js` - Defines the JSDoc interfaces for `TTSProvider`, `AvatarProvider`, `SceneRenderer`, and the `MediaResult` type.
- `src/mock-tts-provider.js` - Mock implementation of `TTSProvider`. Generates mock audio URLs and estimates duration based on text length.
- `src/mock-avatar-provider.js` - Mock implementation of `AvatarProvider`. Generates mock video and thumbnail URLs.
- `src/scene-renderer.js` - Orchestrates the generation of scenes, producing a complete `MediaResult`. Contains fallback logic in case of provider failure.
- `src/provider-factory.js` - Factory functions to instantiate providers.

## Usage

```javascript
import { createTTSProvider, createAvatarProvider, createSceneRenderer } from '@guruflow/media';

const tts = createTTSProvider();
const avatar = createAvatarProvider();
const renderer = createSceneRenderer();

const scene = {
  narration: { text: "Hello, world!", language: "english" },
  visual: { type: "equation", data: { eq: "E=mc^2" } }
};

renderer.renderScene(scene, { ttsProvider: tts, avatarProvider: avatar })
  .then(result => console.log(result));
```

## Adding Real Providers

To add a real provider (e.g., ElevenLabs for TTS, HeyGen for Avatars), create a new class implementing the respective interface and update `createTTSProvider` or `createAvatarProvider` in `provider-factory.js` to return the real implementation when API keys are provided in the configuration.
