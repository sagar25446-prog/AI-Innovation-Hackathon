import { MockTTSProvider } from './mock-tts-provider.js';
import { MockAvatarProvider } from './mock-avatar-provider.js';
import { ServerTTSProvider } from './server-tts-provider.js';
import { DIDAvatarProvider } from './did-avatar-provider.js';
import { DefaultSceneRenderer } from './scene-renderer.js';
import { SceneCache } from './scene-cache.js';

/**
 * Factory creating TTS Provider instance based on configuration.
 *
 * Tries a real server-backed provider (`/tts`) first, then simulates with the
 * deterministic mock. Pass `{ server: true }` (or `{ provider: 'server' }`) to
 * force the live endpoint; otherwise defaults to the mock for offline use.
 *
 * @param {Object} [config={}]
 * @returns {import('./interfaces.js').TTSProvider}
 */
export function createTTSProvider(config = {}) {
  const wantServer =
    Boolean(config.server) ||
    config.provider === 'server' ||
    config.provider === 'edge-tts';
  if (wantServer) {
    return new ServerTTSProvider(config);
  }
  return new MockTTSProvider(config);
}

/**
 * Factory creating Avatar Video Provider instance.
 *
 * Prefers the real D-ID cloud API whenever a key is configured (in `config`
 * or `process.env.DID_API_KEY`), otherwise falls back to the deterministic
 * mock that drives the CSS teacher panel.
 *
 * @param {Object} [config={}]
 * @returns {import('./interfaces.js').AvatarProvider}
 */
export function createAvatarProvider(config = {}) {
  if (config.apiKey ?? config.key ?? (typeof process !== 'undefined' && process.env?.DID_API_KEY)) {
    return new DIDAvatarProvider(config);
  }
  return new MockAvatarProvider(config);
}

/**
 * Factory creating Scene Renderer instance based on configuration.
 * @param {Object} [config={}]
 * @returns {import('./interfaces.js').SceneRenderer}
 */
export function createSceneRenderer(config = {}) {
  return new DefaultSceneRenderer(config);
}

/**
 * Factory creating Scene Cache instance based on configuration.
 * @param {Object} [config={}]
 * @returns {SceneCache}
 */
export function createSceneCache(config = {}) {
  return new SceneCache(config);
}

/**
 * Combined factory bundling providers, cache, and renderer.
 * @param {Object} [config={}]
 * @returns {{ ttsProvider: import('./interfaces.js').TTSProvider, avatarProvider: import('./interfaces.js').AvatarProvider, sceneCache: SceneCache, sceneRenderer: import('./interfaces.js').SceneRenderer }}
 */
export function createProviderFactory(config = {}) {
  const ttsProvider = createTTSProvider(config.tts);
  const avatarProvider = createAvatarProvider(config.avatar);
  const sceneCache = createSceneCache(config.cache);
  const sceneRenderer = createSceneRenderer({ ...config.renderer, cache: sceneCache });

  return {
    ttsProvider,
    avatarProvider,
    sceneCache,
    sceneRenderer
  };
}
