import { TTSProvider } from './interfaces.js';

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
    
    // Deterministic hash for stable audio URL
    const hash = shortHash(`${lang}:${cleanText || 'empty'}`);

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
