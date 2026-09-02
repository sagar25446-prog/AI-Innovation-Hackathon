import { TTSProvider } from './interfaces.js';
import crypto from 'crypto';

/**
 * Mock TTS Provider
 * @implements {TTSProvider}
 */
export class MockTTSProvider extends TTSProvider {
  /**
   * Synthesize text to speech
   * @param {string} text - The text to synthesize
   * @param {string} language - The language (e.g., 'english', 'hindi', 'hinglish')
   * @param {string} voice - Voice identifier
   * @returns {Promise<{audioUrl: string, durationSeconds: number, format: string}>}
   */
  async synthesize(text, language, voice = 'default') {
    const hash = crypto.createHash('md5').update(text).digest('hex').substring(0, 8);
    const words = text.trim().split(/\s+/).length;
    // Estimate ~150 words per minute -> 2.5 words per second
    const durationSeconds = Math.max(1, Math.ceil(words / 2.5));
    
    return {
      audioUrl: `mock://tts/${language}/${hash}.mp3`,
      durationSeconds,
      format: 'mp3'
    };
  }
}
