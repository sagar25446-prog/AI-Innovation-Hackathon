import { MockTTSProvider } from './mock-tts-provider.js';
import { MockAvatarProvider } from './mock-avatar-provider.js';
import { DefaultSceneRenderer } from './scene-renderer.js';

/**
 * Create a TTS Provider
 * @param {Object} config - Configuration options
 * @returns {import('./interfaces.js').TTSProvider}
 */
export function createTTSProvider(config = {}) {
  // If an API key is present in config, we would return a real provider here.
  // For now, we return the mock provider.
  return new MockTTSProvider();
}

/**
 * Create an Avatar Provider
 * @param {Object} config - Configuration options
 * @returns {import('./interfaces.js').AvatarProvider}
 */
export function createAvatarProvider(config = {}) {
  // If an API key is present in config, we would return a real provider here.
  return new MockAvatarProvider();
}

/**
 * Create a Scene Renderer
 * @returns {import('./interfaces.js').SceneRenderer}
 */
export function createSceneRenderer() {
  return new DefaultSceneRenderer();
}
