/**
 * Interfaces and typedefs for the GuruFlow media rendering engine.
 * @module interfaces
 */

/**
 * @typedef {Object} TeacherPanelResult
 * @property {'video'|'image'} type - Panel display type.
 * @property {string|null} url - Media stream or video URL.
 * @property {string} thumbnailUrl - Poster or static placeholder image URL.
 * @property {boolean} [fallback] - Whether this panel is operating in fallback mode.
 */

/**
 * @typedef {Object} AudioResult
 * @property {string|null} url - Audio URL.
 * @property {number} durationSeconds - Total duration of the audio in seconds.
 * @property {string|null} format - Audio format (e.g., 'mp3', 'wav').
 * @property {string} [language] - Spoken language.
 * @property {boolean} [fallback] - Whether audio is operating in fallback mode.
 */

/**
 * @typedef {Object} VideoResult
 * @property {string|null} url - Video URL.
 * @property {string} thumbnailUrl - Poster/thumbnail URL.
 * @property {string|null} format - Video format (e.g., 'mp4', 'webm').
 * @property {number} durationSeconds - Video duration in seconds.
 * @property {boolean} [fallback] - Whether video is operating in fallback mode.
 */

/**
 * @typedef {Object} VisualCanvasResult
 * @property {string} type - Visual type ('circuit', 'equation', 'graph', 'concept_map', 'diagram', etc.).
 * @property {Object} data - Structured visual specification data for frontend rendering.
 * @property {string} [renderHint] - Rendering mode hint (e.g., 'standard', 'interactive_diagram', 'animated').
 */

/**
 * @typedef {Object} CaptionSegment
 * @property {number} index - Segment sequence index.
 * @property {string} text - Spoken text for this segment.
 * @property {number} startTime - Start time offset in seconds.
 * @property {number} endTime - End time offset in seconds.
 * @property {number} [duration] - Segment duration in seconds.
 * @property {string} [startMarker] - Formatted timestamp (MM:SS.mmm).
 * @property {string} [endMarker] - Formatted timestamp (MM:SS.mmm).
 * @property {string} language - Language of the caption.
 * @property {Array<string>} [mathFormulas] - Extracted invariant math expressions.
 */

/**
 * @typedef {Object} MediaResult
 * @property {string} sceneId - ID of the rendered scene.
 * @property {TeacherPanelResult} teacherPanel - Avatar/teacher panel rendering metadata.
 * @property {AudioResult} [audio] - Audio stream metadata and fallback indicator.
 * @property {VideoResult} [video] - Video stream metadata and fallback indicator.
 * @property {VisualCanvasResult} visualCanvas - Visual component data payload.
 * @property {Array<CaptionSegment>} captions - Timed captions aligned with narration.
 * @property {number} durationSeconds - Total duration in seconds.
 * @property {string} language - Narration and caption language.
 * @property {'ready'|'degraded'|'error'} status - Operational status of the media output.
 * @property {Array<Object>} [citations] - Academic/curriculum source citations.
 * @property {Object} [metadata] - Additional render diagnostics and timestamps.
 */

/**
 * Interface for TTS Providers.
 * @interface TTSProvider
 */
export class TTSProvider {
  /**
   * Synthesizes speech from narration text.
   * @param {string} text - Narration text to synthesize.
   * @param {string} [language='hinglish'] - Target language.
   * @param {string} [voice='default'] - Voice identifier.
   * @returns {Promise<{audioUrl: string, durationSeconds: number, format: string, language: string, text: string, isFallback: boolean}>}
   */
  async synthesize(text, language = 'hinglish', voice = 'default') {
    throw new Error('Method synthesize() not implemented in abstract TTSProvider.');
  }
}

/**
 * Interface for Avatar Video Providers.
 * @interface AvatarProvider
 */
export class AvatarProvider {
  /**
   * Generates talking avatar video aligned with narration audio.
   * @param {string} narration - Narration transcript.
   * @param {string|null} audioUrl - URL to synthesized audio.
   * @param {Object} [options={}] - Additional rendering options (durationSeconds, teacherId, etc.).
   * @returns {Promise<{videoUrl: string, thumbnailUrl: string, format: string, durationSeconds: number, isFallback: boolean}>}
   */
  async generateAvatar(narration, audioUrl, options = {}) {
    throw new Error('Method generateAvatar() not implemented in abstract AvatarProvider.');
  }
}

/**
 * Interface for Scene Renderers.
 * @interface SceneRenderer
 */
export class SceneRenderer {
  /**
   * Renders a full multimodal scene with robust fallback handling.
   * @param {Object} scene - Scene specification conforming to lesson contract.
   * @param {Object} [providers={}] - TTS, Avatar, and Cache providers.
   * @param {Object} [options={}] - Render configuration and caching options.
   * @returns {Promise<MediaResult>}
   */
  async renderScene(scene, providers = {}, options = {}) {
    throw new Error('Method renderScene() not implemented in abstract SceneRenderer.');
  }
}
