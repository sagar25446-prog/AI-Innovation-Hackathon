import { AvatarProvider } from './interfaces.js';

/**
 * Deterministic 8-char hex hash from a string. Portable (browser + Node),
 * avoids a hard dependency on the Node-only `crypto` module so these mock
 * providers can run in the frontend bundle.
 * @param {string} input
 * @returns {string}
 */
function shortHash(input) {
  const str = String(input === undefined || input === null ? '' : input);
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  const n = 4294967296 * (h2 >>> 0) + (h1 >>> 0);
  return Math.abs(n).toString(16).padStart(8, '0').substring(0, 8);
}

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
    
    // Deterministic hash for stable video URL
    const hash = shortHash(`${this.teacherId}:${cleanAudio}:${cleanNarration || 'avatar'}`);

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
