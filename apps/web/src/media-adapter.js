/**
 * Browser-side media providers.
 *
 * These implement the provider-neutral interfaces owned by `services/media`
 * and are handed to Person 3's `DefaultSceneRenderer`, so the frontend never
 * reimplements scene rendering -- it only supplies the providers.
 *
 * The server provides real TTS via edge-tts. The browser falls back to
 * Web Speech API if the server is unreachable.
 */

import { DefaultSceneRenderer } from '/vendor/media/scene-renderer.js';
import { AvatarProvider, TTSProvider } from '/vendor/media/interfaces.js';
import {
  PrerenderedAvatarProvider,
  clipRoleForScene,
} from './prerendered-avatar-provider.js';

// BCP-47 tags for the browser SpeechSynthesis fallback. The server's edge-tts
// voices are the primary path; these only matter when /tts is unreachable.
// Hinglish uses the Hindi tag because it is romanised Hindi, not English.
const VOICE_BY_LANGUAGE = {
  english: 'en-IN',
  hindi: 'hi-IN',
  hinglish: 'hi-IN',
  bengali: 'bn-IN',
  // No Bhojpuri voice exists; Devanagari read by the Hindi voice.
  bhojpuri: 'hi-IN',
  gujarati: 'gu-IN',
  kannada: 'kn-IN',
  malayalam: 'ml-IN',
  marathi: 'mr-IN',
  nepali: 'ne-NP',
  odia: 'or-IN',
  punjabi: 'pa-IN',
  sinhala: 'si-LK',
  tamil: 'ta-IN',
  telugu: 'te-IN',
  urdu: 'ur-IN',
};

/**
 * Server-backed TTS provider. Calls POST /tts to get real audio from edge-tts.
 * Falls back to browser SpeechSynthesis if the server is unreachable.
 */
export class ServerTTSProvider extends TTSProvider {
  constructor() {
    super();
    this.browserAvailable =
      typeof window !== 'undefined' && 'speechSynthesis' in window;
    this.enabled = false;
    this.serverAvailable = true;
    this._currentAudio = null;
    // Bumped on every speak() and stop(). A TTS fetch that resolves after its
    // token is superseded is discarded rather than played - without this,
    // switching language mid-scene left the previous language's request in
    // flight, and both narrations played over each other once it arrived.
    this._playToken = 0;
    this._inFlight = null;
  }

  async synthesize(text, language) {
    const words = text.trim().split(/\s+/).length;
    const durationSeconds = Math.max(1, Math.ceil(words / 2.5));

    if (!this.enabled) {
      return { audioUrl: '', durationSeconds, format: 'none' };
    }

    // Try server TTS first
    if (this.serverAvailable) {
      try {
        const response = await fetch('/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, language }),
        });
        if (response.ok) {
          const blob = await response.blob();
          const audioUrl = URL.createObjectURL(blob);
          return { audioUrl, durationSeconds, format: 'mp3' };
        }
      } catch {
        this.serverAvailable = false;
      }
    }

    // Fallback to browser speech
    if (this.browserAvailable) {
      return {
        audioUrl: `speech://${VOICE_BY_LANGUAGE[language] || 'en-IN'}`,
        durationSeconds,
        format: 'speech-synthesis',
      };
    }

    return { audioUrl: '', durationSeconds, format: 'none' };
  }

  speak(text, language, { onStart, onEnd } = {}) {
    // Stop any current playback. This also invalidates any request still in
    // flight, so a slow response for the *previous* scene or language can
    // never start playing on top of this one.
    this.stop();
    const token = this._playToken;

    if (this.serverAvailable) {
      const controller =
        typeof AbortController !== 'undefined' ? new AbortController() : null;
      this._inFlight = controller;

      fetch('/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language }),
        signal: controller ? controller.signal : undefined,
      })
        .then((response) => {
          if (!response.ok) throw new Error('TTS failed');
          return response.blob();
        })
        .then((blob) => {
          // Superseded while we waited: drop it, and free the blob rather than
          // leaking one object URL per abandoned scene.
          if (token !== this._playToken) return;

          const audioUrl = URL.createObjectURL(blob);
          const audio = new Audio(audioUrl);
          this._currentAudio = audio;

          const release = () => {
            URL.revokeObjectURL(audioUrl);
            if (this._currentAudio === audio) this._currentAudio = null;
          };

          audio.onplay = () => {
            // A late play on a stale token still gets silenced.
            if (token !== this._playToken) {
              audio.pause();
              release();
              return;
            }
            if (onStart) onStart();
          };
          audio.onended = () => {
            release();
            if (token === this._playToken && onEnd) onEnd();
          };
          audio.onerror = () => {
            release();
            if (token !== this._playToken) return;
            this._fallbackBrowserSpeak(text, language, { onStart, onEnd });
          };
          audio.play().catch(() => {
            release();
            if (token !== this._playToken) return;
            this._fallbackBrowserSpeak(text, language, { onStart, onEnd });
          });
        })
        .catch((error) => {
          // An abort is us cancelling deliberately, not a server failure -
          // treating it as one would wrongly disable server TTS for the rest
          // of the session.
          if (error && error.name === 'AbortError') return;
          if (token !== this._playToken) return;
          this.serverAvailable = false;
          this._fallbackBrowserSpeak(text, language, { onStart, onEnd });
        });
      return true;
    }

    return this._fallbackBrowserSpeak(text, language, { onStart, onEnd });
  }

  _fallbackBrowserSpeak(text, language, { onStart, onEnd } = {}) {
    if (!this.browserAvailable) return false;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = VOICE_BY_LANGUAGE[language] || 'en-IN';
      utterance.rate = 0.95;
      if (onStart) utterance.onstart = onStart;
      if (onEnd) {
        utterance.onend = onEnd;
        utterance.onerror = onEnd;
      }
      window.speechSynthesis.speak(utterance);
      return true;
    } catch {
      return false;
    }
  }

  stop() {
    // Invalidate anything in flight *first*, so a response that arrives during
    // this call is already stale by the time it tries to play.
    this._playToken += 1;

    if (this._inFlight) {
      try { this._inFlight.abort(); } catch { /* already settled */ }
      this._inFlight = null;
    }
    if (this._currentAudio) {
      try { this._currentAudio.pause(); this._currentAudio.currentTime = 0; } catch {}
      this._currentAudio = null;
    }
    if (this.browserAvailable) {
      try { window.speechSynthesis.cancel(); } catch {}
    }
  }
}

/**
 * Avatar provider that tries the server endpoint, then falls back to
 * the CSS teacher panel.
 */
export class FallbackAvatarProvider extends AvatarProvider {
  constructor({ videoUrl = null } = {}) {
    super();
    this.videoUrl = videoUrl;
  }

  async generateAvatar(narration, audioUrl, options = {}) {
    if (!this.videoUrl) {
      throw new Error('No avatar provider configured; using fallback panel.');
    }
    return {
      videoUrl: this.videoUrl,
      thumbnailUrl: '',
      format: 'mp4',
      durationSeconds: options.durationSeconds || 0,
    };
  }
}

/** Media pipeline wired from the contract's own renderer. */
export class MediaAdapter {
  constructor(options = {}) {
    this.tts = new ServerTTSProvider();
    // Pre-rendered SadTalker clips when they exist on disk. Until then this
    // throws, which the renderer treats as "no avatar configured" and falls
    // back to the drawn teacher panel - the behaviour shipped today.
    this.avatar = new PrerenderedAvatarProvider(options.avatar);
    // Kept as an explicit revert path: assign this to `adapter.avatar` to go
    // back to the previous behaviour without touching the pipeline.
    this.fallbackAvatar = new FallbackAvatarProvider();
    this.renderer = new DefaultSceneRenderer();
  }

  /**
   * Revert to the previous avatar behaviour.
   * Kept deliberately simple so it can be done from the console mid-demo.
   */
  useFallbackAvatar() {
    this.avatar = this.fallbackAvatar;
  }

  setVoiceEnabled(enabled) {
    this.tts.enabled = Boolean(enabled) && (this.tts.serverAvailable || this.tts.browserAvailable);
    if (!this.tts.enabled) this.tts.stop();
    return this.tts.enabled;
  }

  get voiceAvailable() {
    return this.tts.serverAvailable || this.tts.browserAvailable;
  }

  /**
   * Render a Scene through services/media.
   * Returns a MediaResult, degraded rather than failed if a provider is down.
   */
  /**
   * Render a Scene through services/media.
   * @param {Object} scene
   * @param {string} language
   * @param {Object} [context={}] - Lesson-moment hints used to pick an avatar clip.
   */
  async render(scene, language, context = {}) {
    try {
      const clipRole = clipRoleForScene({
        isRepair: Boolean(scene.isRepair),
        ...context,
      });
      // services/media's renderer forwards a fixed option set to
      // generateAvatar and does not know about clipRole. Rather than edit
      // Person 3's module, bind the role with a stateless per-call wrapper -
      // the renderer only ever calls generateAvatar, so duck typing is enough.
      const avatarProvider = {
        generateAvatar: (narration, audioUrl, opts = {}) =>
          this.avatar.generateAvatar(narration, audioUrl, { ...opts, clipRole }),
      };

      const result = await this.renderer.renderScene(
        { ...scene, language },
        { ttsProvider: this.tts, avatarProvider, language }
      );
      return result;
    } catch (error) {
      return {
        teacherPanel: { type: 'fallback', url: '', thumbnailUrl: '' },
        visualCanvas: { type: scene.visual?.type, data: scene.visual?.data || {}, renderHint: 'standard' },
        captions: [{ text: scene.narration, startTime: 0, endTime: scene.durationSeconds, language }],
        durationSeconds: scene.durationSeconds,
        status: 'degraded',
        error: String(error && error.message ? error.message : error),
      };
    }
  }
}
