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

const VOICE_BY_LANGUAGE = {
  english: 'en-IN',
  hindi: 'hi-IN',
  hinglish: 'hi-IN',
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
    // Stop any current playback
    this.stop();

    // Try server TTS first
    if (this.serverAvailable) {
      fetch('/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language }),
      })
        .then((response) => {
          if (!response.ok) throw new Error('TTS failed');
          return response.blob();
        })
        .then((blob) => {
          const audioUrl = URL.createObjectURL(blob);
          const audio = new Audio(audioUrl);
          this._currentAudio = audio;
          audio.onplay = () => { if (onStart) onStart(); };
          audio.onended = () => {
            this._currentAudio = null;
            if (onEnd) onEnd();
          };
          audio.onerror = () => {
            this._currentAudio = null;
            this._fallbackBrowserSpeak(text, language, { onStart, onEnd });
          };
          audio.play().catch(() => {
            this._currentAudio = null;
            this._fallbackBrowserSpeak(text, language, { onStart, onEnd });
          });
        })
        .catch(() => {
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
  constructor() {
    this.tts = new ServerTTSProvider();
    this.avatar = new FallbackAvatarProvider();
    this.renderer = new DefaultSceneRenderer();
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
  async render(scene, language) {
    try {
      const result = await this.renderer.renderScene(
        { ...scene, language },
        { ttsProvider: this.tts, avatarProvider: this.avatar, language }
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
