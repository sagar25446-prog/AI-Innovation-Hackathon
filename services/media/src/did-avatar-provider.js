/**
 * D-ID Avatar Provider for GuruFlow.
 *
 * Uses the D-ID free trial API to generate lip-synced talking avatar videos.
 * Falls back gracefully if no API key is configured.
 *
 * Free tier: 5 minutes of video. Sign up at https://www.d-id.com
 *
 * Usage:
 *   const provider = new DIDAvatarProvider({ apiKey: 'your-key' });
 *   const result = await provider.generateAvatar(narration, audioUrl, opts);
 */

const DID_API_BASE = 'https://api.d-id.com';

// Default presenter images (publicly available D-ID stock)
const PRESENTERS = {
  default: 'https://create-images-results.d-id.com/DefaultPresenters/Noelle_f/image.jpeg',
  male: 'https://create-images-results.d-id.com/DefaultPresenters/Amos_f/image.jpeg',
  female: 'https://create-images-results.d-id.com/DefaultPresenters/Noelle_f/image.jpeg',
};

const VOICE_MAP = {
  english: 'en-IN-MadhurNeural',
  hindi: 'hi-IN-SwaraNeural',
  hinglish: 'hi-IN-MadhurNeural',
};

export class DIDAvatarProvider {
  constructor({ apiKey = null, presenter = 'default' } = {}) {
    this.apiKey = apiKey || (typeof process !== 'undefined' && process.env?.DID_API_KEY) || null;
    this.presenter = PRESENTERS[presenter] || PRESENTERS.default;
    this.cache = new Map();
  }

  get isConfigured() {
    return Boolean(this.apiKey);
  }

  async generateAvatar(narration, audioUrl, options = {}) {
    if (!this.apiKey) {
      throw new Error('D-ID API key not configured');
    }

    const cacheKey = `${narration}:${options.language || 'hinglish'}`;
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    const voice = VOICE_MAP[options.language] || VOICE_MAP.hinglish;
    const durationSeconds = options.durationSeconds || Math.max(5, Math.ceil(narration.split(/\s+/).length / 2.5));

    try {
      // Create a talk
      const createResponse = await fetch(`${DID_API_BASE}/talks`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${this.apiKey}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          script: {
            type: 'text',
            input: narration,
            provider: {
              type: 'microsoft',
              voice_id: voice,
            },
          },
          source_url: this.presenter,
          config: {
            fluent: true,
            pad_audio: 0.5,
            result_format: 'mp4',
          },
        }),
      });

      if (!createResponse.ok) {
        const errorText = await createResponse.text();
        throw new Error(`D-ID API error ${createResponse.status}: ${errorText.slice(0, 200)}`);
      }

      const { id } = await createResponse.json();

      // Poll for completion
      let result = null;
      for (let i = 0; i < 30; i++) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        const pollResponse = await fetch(`${DID_API_BASE}/talks/${id}`, {
          headers: {
            'Authorization': `Basic ${this.apiKey}`,
            'Accept': 'application/json',
          },
        });
        if (!pollResponse.ok) continue;
        result = await pollResponse.json();
        if (result.status === 'done') break;
        if (result.status === 'error') throw new Error('D-ID generation failed');
      }

      if (!result || result.status !== 'done' || !result.result_url) {
        throw new Error('D-ID generation timed out');
      }

      const avatarResult = {
        videoUrl: result.result_url,
        thumbnailUrl: result.result_url?.replace('.mp4', '.jpg') || '',
        format: 'mp4',
        durationSeconds,
        isFallback: false,
      };

      this.cache.set(cacheKey, avatarResult);
      return avatarResult;
    } catch (error) {
      throw new Error(`D-ID avatar failed: ${error.message}`);
    }
  }
}
