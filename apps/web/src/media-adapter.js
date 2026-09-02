/**
 * Browser-side media providers.
 *
 * These implement the provider-neutral interfaces owned by `services/media`
 * and are handed to Person 3's `DefaultSceneRenderer`, so the frontend never
 * reimplements scene rendering -- it only supplies the providers.
 *
 * The mock providers shipped in services/media import Node's `crypto`, so they
 * cannot run in a browser. That is exactly the case the interface exists for:
 * a different environment plugs in different providers behind the same shape.
 */

import { DefaultSceneRenderer } from '/vendor/media/scene-renderer.js';
import { AvatarProvider, TTSProvider } from '/vendor/media/interfaces.js';

const VOICE_BY_LANGUAGE = {
  english: 'en-IN',
  hindi: 'hi-IN',
  hinglish: 'hi-IN',
};

/**
 * Speech-synthesis TTS. Uses the browser's built-in voices, so it needs no API
 * key and no network. Reports duration by estimate because the Web Speech API
 * does not expose one up front.
 */
export class BrowserTTSProvider extends TTSProvider {
  constructor() {
    super();
    this.available =
      typeof window !== 'undefined' && 'speechSynthesis' in window;
    this.enabled = false;
  }

  async synthesize(text, language) {
    const words = text.trim().split(/\s+/).length;
    const durationSeconds = Math.max(1, Math.ceil(words / 2.5));

    if (!this.available || !this.enabled) {
      // Not an error: the lesson continues silently with captions.
      return { audioUrl: '', durationSeconds, format: 'none' };
    }

    return {
      audioUrl: `speech://${VOICE_BY_LANGUAGE[language] || 'en-IN'}`,
      durationSeconds,
      format: 'speech-synthesis',
    };
  }

  /** Speak a narration line. Never throws; silence is an acceptable outcome. */
  speak(text, language, { onStart, onEnd } = {}) {
    if (!this.available || !this.enabled) return false;
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
    if (this.available) {
      try { window.speechSynthesis.cancel(); } catch { /* ignore */ }
    }
  }
}

/**
 * Avatar provider that returns no video, which drives the SceneRenderer down
 * its documented fallback path: the polished CSS teacher panel plus captions.
 * A hosted avatar vendor would replace only this class.
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
    this.tts = new BrowserTTSProvider();
    this.avatar = new FallbackAvatarProvider();
    this.renderer = new DefaultSceneRenderer();
  }

  setVoiceEnabled(enabled) {
    this.tts.enabled = Boolean(enabled) && this.tts.available;
    if (!this.tts.enabled) this.tts.stop();
    return this.tts.enabled;
  }

  get voiceAvailable() {
    return this.tts.available;
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
      // A provider failure must never stop the lesson.
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
