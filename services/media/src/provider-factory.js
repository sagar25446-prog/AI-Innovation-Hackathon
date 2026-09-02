import { MockTTSProvider } from './mock-tts-provider.js';
import { MockAvatarProvider } from './mock-avatar-provider.js';
import { DefaultSceneRenderer } from './scene-renderer.js';
import { SceneCache } from './scene-cache.js';

/**
 * Factory creating TTS Provider instance based on configuration.
 * @param {Object} [config={}]
 * @returns {import('./interfaces.js').TTSProvider}
 */
export function createTTSProvider(config = {}) {
  return new MockTTSProvider(config);
}

/**
 * Factory creating Avatar Video Provider instance based on configuration.
 * @param {Object} [config={}]
 * @returns {import('./interfaces.js').AvatarProvider}
 */
export function createAvatarProvider(config = {}) {
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
