import { AvatarProvider } from './interfaces.js';
import crypto from 'crypto';

/**
 * Mock Avatar Provider
 * @implements {AvatarProvider}
 */
export class MockAvatarProvider extends AvatarProvider {
  /**
   * Generate an avatar video from narration
   * @param {string} narration - The narration text
   * @param {string} audioUrl - URL of the audio
   * @param {Object} options - Additional options
   * @returns {Promise<{videoUrl: string, thumbnailUrl: string, format: string, durationSeconds: number}>}
   */
  async generateAvatar(narration, audioUrl, options = {}) {
    const hash = crypto.createHash('md5').update(audioUrl || narration).digest('hex').substring(0, 8);
    const durationSeconds = options.durationSeconds || 5;

    return {
      videoUrl: `mock://avatar/${hash}.mp4`,
      thumbnailUrl: `mock://avatar/thumb_${hash}.jpg`,
      format: 'mp4',
      durationSeconds
    };
  }
}
