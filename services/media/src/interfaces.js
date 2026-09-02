/**
 * @typedef {Object} MediaResult
 * @property {Object} teacherPanel
 * @property {string} teacherPanel.type
 * @property {string} teacherPanel.url
 * @property {string} teacherPanel.thumbnailUrl
 * @property {Object} visualCanvas
 * @property {string} visualCanvas.type
 * @property {Object} visualCanvas.data
 * @property {string} visualCanvas.renderHint
 * @property {Array<{text: string, startTime: number, endTime: number, language: string}>} captions
 * @property {number} durationSeconds
 * @property {string} status
 */

/**
 * Interface for TTS Provider
 * @interface TTSProvider
 */
export class TTSProvider {
  /**
   * Synthesize text to speech
   * @param {string} text - The text to synthesize
   * @param {string} language - The language (e.g., 'english', 'hindi', 'hinglish')
   * @param {string} voice - Voice identifier
   * @returns {Promise<{audioUrl: string, durationSeconds: number, format: string}>}
   */
  async synthesize(text, language, voice) {
    throw new Error('Method not implemented.');
  }
}

/**
 * Interface for Avatar Provider
 * @interface AvatarProvider
 */
export class AvatarProvider {
  /**
   * Generate an avatar video from narration
   * @param {string} narration - The narration text
   * @param {string} audioUrl - URL of the audio
   * @param {Object} options - Additional options
   * @returns {Promise<{videoUrl: string, thumbnailUrl: string, format: string, durationSeconds: number}>}
   */
  async generateAvatar(narration, audioUrl, options) {
    throw new Error('Method not implemented.');
  }
}

/**
 * Interface for Scene Renderer
 * @interface SceneRenderer
 */
export class SceneRenderer {
  /**
   * Render a scene
   * @param {Object} scene - Scene object from contract schema
   * @param {Object} providers - Providers to use
   * @param {TTSProvider} providers.ttsProvider - TTS provider
   * @param {AvatarProvider} providers.avatarProvider - Avatar provider
   * @returns {Promise<MediaResult>}
   */
  async renderScene(scene, providers) {
    throw new Error('Method not implemented.');
  }
}
