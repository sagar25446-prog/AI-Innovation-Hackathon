import { TTSProvider } from './interfaces.js';
import crypto from 'node:crypto';

/**
 * Normalizes language string to canonical identifier.
 * @param {string} lang
 * @returns {string}
 */
function normalizeLang(lang) {
  if (!lang || typeof lang !== 'string') return 'hinglish';
  const l = lang.toLowerCase().trim();
  if (l === 'en' || l === 'english' || l === 'eng') return 'english';
  if (l === 'hi' || l === 'hindi' || l === 'hin') return 'hindi';
  if (l === 'hinglish' || l === 'hi-latn' || l === 'hing') return 'hinglish';
  return l;
}

/**
 * Mock TTS Provider with configurable latency and error simulation.
 * @implements {TTSProvider}
 */
export class MockTTSProvider extends TTSProvider {
  /**
   * @param {Object} [options={}]
   * @param {number} [options.latencyMs=0] - Simulated network/synthesis delay in ms.
   * @param {number} [options.delayMs=0] - Alias for latencyMs.
   * @param {boolean} [options.shouldFail=false] - If true, simulates provider failure.
   * @param {string} [options.voice='default'] - Default voice identifier.
   * @param {string} [options.errorMessage] - Custom error message for failure simulation.
   */
  constructor(options = {}) {
    super();
    this.latencyMs = Number(options.latencyMs ?? options.delayMs ?? 0);
    this.shouldFail = Boolean(options.shouldFail);
    this.voice = options.voice || 'default';
    this.errorMessage = options.errorMessage || 'TTS synthesis failed: simulated provider error';
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
   * Synthesize text into mock audio stream.
   * @param {string} text - Narration text to synthesize.
   * @param {string} [language='hinglish'] - Target language.
   * @param {string} [voice=this.voice] - Voice identifier.
   * @returns {Promise<{audioUrl: string, durationSeconds: number, format: string, language: string, text: string, isFallback: boolean}>}
   */
  async synthesize(text, language = 'hinglish', voice = this.voice) {
    // Latency simulation
    if (this.latencyMs > 0) {
      await new Promise(resolve => setTimeout(resolve, this.latencyMs));
    }

    // Error simulation
    if (this.shouldFail) {
      throw new Error(this.errorMessage);
    }

    const cleanText = (typeof text === 'string' ? text : String(text || '')).trim();
    const lang = normalizeLang(language);
    
    // Hash based on clean text and language for deterministic audio URL
    const hash = crypto
      .createHash('md5')
      .update(`${lang}:${cleanText || 'empty'}`)
      .digest('hex')
      .substring(0, 8);

    // Compute duration from word count: ~150 wpm = 2.5 words/sec, minimum 1 second
    const words = cleanText ? cleanText.split(/\s+/).filter(Boolean).length : 0;
    const durationSeconds = words > 0 ? Math.max(1, Math.ceil(words / 2.5)) : 2;

    return {
      audioUrl: `mock://tts/${encodeURIComponent(lang)}/${hash}.mp3`,
      durationSeconds,
      format: 'mp3',
      language: lang,
      text: cleanText,
      voice: voice || this.voice,
      isFallback: false
    };
  }
}
