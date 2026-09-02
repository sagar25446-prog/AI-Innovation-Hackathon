import { TTSProvider } from './interfaces.js';

/**
 * Server-backed TTS provider.
 *
 * Calls the GuruFlow FastAPI `/tts` endpoint (which streams real edge-tts
 * audio) so the media library can produce genuine neural voice, not a mock
 * buffer. Falls back to a typed 'none' result if the server is unreachable.
 *
 * Only used when the caller opts in via `createTTSProvider({ server: true })`
 * or instantiates `ServerTTSProvider` directly; the deterministic mocks remain
 * available for offline/unit-test use.
 *
 * @implements {TTSProvider}
 */
export class ServerTTSProvider extends TTSProvider {
  /**
   * @param {Object} [options={}]
   * @param {string} [options.baseUrl=''] - Server origin (e.g. 'http://127.0.0.1:8077'). Empty = same-origin.
   * @param {number} [options.timeoutMs=20000] - Request timeout.
   */
  constructor(options = {}) {
    super();
    this.baseUrl = (options.baseUrl || '').replace(/\/$/, '');
    this.timeoutMs = Number(options.timeoutMs ?? 20000);
    this.serverAvailable = true;
  }

  /**
   * Synthesize narration into a real MP3 served by the backend.
   * @param {string} text
   * @param {string} [language='hinglish']
   * @returns {Promise<{audioUrl:string, durationSeconds:number, format:string, language:string, text:string, isFallback:boolean}>}
   */
  async synthesize(text, language = 'hinglish', voice = 'default') {
    const cleanText = (typeof text === 'string' ? text : String(text || '')).trim();
    const words = cleanText ? cleanText.split(/\s+/).filter(Boolean).length : 0;
    const durationSeconds = words > 0 ? Math.max(1, Math.ceil(words / 2.5)) : 2;

    if (!this.serverAvailable) {
      return { audioUrl: '', durationSeconds, format: 'none', language, text: cleanText, isFallback: true };
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await fetch(`${this.baseUrl}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cleanText, language }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`TTS HTTP ${response.status}`);
      const blob = await response.blob();
      return {
        audioUrl: URL.createObjectURL(blob),
        durationSeconds,
        format: 'mp3',
        language,
        text: cleanText,
        isFallback: false,
      };
    } catch (error) {
      this.serverAvailable = false;
      return { audioUrl: '', durationSeconds, format: 'none', language, text: cleanText, isFallback: true };
    } finally {
      clearTimeout(timer);
    }
  }
}
