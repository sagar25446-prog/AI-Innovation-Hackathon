import { AvatarProvider } from './interfaces.js';
import crypto from 'node:crypto';

/**
 * Mock Avatar Provider with configurable latency and error simulation.
 * @implements {AvatarProvider}
 */
export class MockAvatarProvider extends AvatarProvider {
  /**
   * @param {Object} [options={}]
   * @param {number} [options.latencyMs=0] - Simulated network/generation delay in ms.
   * @param {number} [options.delayMs=0] - Alias for latencyMs.
   * @param {boolean} [options.shouldFail=false] - If true, simulates provider failure.
   * @param {string} [options.teacherId='teacher-dr-sharma'] - Teacher persona identifier.
   * @param {string} [options.errorMessage] - Custom error message for failure simulation.
   */
  constructor(options = {}) {
    super();
    this.latencyMs = Number(options.latencyMs ?? options.delayMs ?? 0);
    this.shouldFail = Boolean(options.shouldFail);
    this.teacherId = options.teacherId || 'teacher-dr-sharma';
    this.errorMessage = options.errorMessage || 'Avatar generation failed: simulated provider error';
  }

  /**
   * Dynamically toggle simulated failure.
   * @param {boolean} shouldFail
   * @param {string} [errorMessage]
   */
  setShouldFail(shouldFail, errorMessage) {
    this.shouldFail = Boolean(shouldFail);
    if (errorMessage) {
      this.errorMessage = errorMessage;
    }
  }

  /**
   * Dynamically set latency.
   * @param {number} ms
   */
  setLatency(ms) {
    this.latencyMs = Math.max(0, Number(ms) || 0);
  }

  /**
   * Generates a mock talking avatar video aligned with narration audio.
   * @param {string} narration - Narration transcript.
   * @param {string|null} audioUrl - URL of synthesized audio.
   * @param {Object} [options={}] - Options including durationSeconds.
   * @returns {Promise<{videoUrl: string, thumbnailUrl: string, format: string, durationSeconds: number, isFallback: boolean}>}
   */
  async generateAvatar(narration, audioUrl = null, options = {}) {
    // Latency simulation
    if (this.latencyMs > 0) {
      await new Promise(resolve => setTimeout(resolve, this.latencyMs));
    }

    // Error simulation
    if (this.shouldFail) {
      throw new Error(this.errorMessage);
    }

    const cleanNarration = (typeof narration === 'string' ? narration : String(narration || '')).trim();
    const cleanAudio = audioUrl || '';
    
    // Hash based on audioUrl, narration, and teacherId for deterministic video URL
    const hash = crypto
      .createHash('md5')
      .update(`${this.teacherId}:${cleanAudio}:${cleanNarration || 'avatar'}`)
      .digest('hex')
      .substring(0, 8);

    // Compute duration from options or narration
    let durationSeconds = Number(options.durationSeconds);
    if (!durationSeconds || durationSeconds <= 0) {
      const words = cleanNarration ? cleanNarration.split(/\s+/).filter(Boolean).length : 0;
      durationSeconds = words > 0 ? Math.max(1, Math.ceil(words / 2.5)) : 5;
    }

    return {
      videoUrl: `mock://avatar/${this.teacherId}/${hash}.mp4`,
      thumbnailUrl: `mock://avatar/${this.teacherId}/thumb_${hash}.jpg`,
      format: 'mp4',
      durationSeconds,
      isFallback: false
    };
  }
}
