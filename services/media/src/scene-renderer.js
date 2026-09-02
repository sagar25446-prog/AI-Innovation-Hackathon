import { SceneRenderer } from './interfaces.js';
import { MockTTSProvider } from './mock-tts-provider.js';
import { MockAvatarProvider } from './mock-avatar-provider.js';
import { SceneCache } from './scene-cache.js';
import { normalizeLanguage, normalizeSceneId } from './cached-descriptors.js';

// Default singleton cache instance for fast lookup
let defaultCacheInstance = null;
function getDefaultCache() {
  if (!defaultCacheInstance) {
    defaultCacheInstance = new SceneCache({ preSeed: true });
  }
  return defaultCacheInstance;
}

/**
 * Regex identifying mathematical equations, formulas, units, and numeric quantities.
 * Invariant across language translations.
 */
const MATH_TOKEN_REGEX = /(?:[VIR]\s*=\s*[^\s,!?]+(?:\s*[+\-*/×·÷]\s*[^\s,!?]+)*|\b\d+(?:\.\d+)?\s*(?:V|Ω|A|Amperes|Volts|Ohms|L\/s|W|Psi|mm)\b|\b[VIR]\s*=\s*V\/R\b|\bV\s*=\s*I\s*[×*·]\s*R\b|\bV\s*=\s*IR\b|\bI\s*=\s*V\/R\b|\b\d+\/\d+(?:=\d+A)?\b|\b[VIR]\b)/g;

/**
 * Extract math tokens from text string.
 * @param {string} text
 * @returns {Array<string>}
 */
function extractMathFormulas(text) {
  if (!text || typeof text !== 'string') return [];
  const matches = text.match(MATH_TOKEN_REGEX);
  return matches ? Array.from(new Set(matches.map(m => m.trim()))) : [];
}

/**
 * Robust sentence segmenter that avoids splitting on decimals (e.g. 10.0V, 2.5Ω, 4.0A).
 * @param {string} text
 * @returns {Array<string>}
 */
function splitIntoSentences(text) {
  if (!text || typeof text !== 'string') return [];
  const clean = text.trim();
  if (!clean) return [];

  const rawSegments = [];
  const sentenceRegex = /(?:[^.!?\n]|\d+\.\d+)+[.!?]+(?:\s+|$)|(?:[^.!?\n]|\d+\.\d+)+$/g;
  let match;

  while ((match = sentenceRegex.exec(clean)) !== null) {
    const seg = match[0].trim();
    if (seg.length > 0) {
      rawSegments.push(seg);
    }
  }

  return rawSegments.length > 0 ? rawSegments : [clean];
}

/**
 * Generates timed caption segments for a scene narration.
 * @param {string} narrationText
 * @param {string} language
 * @param {number} totalDuration
 * @returns {Array<Object>}
 */
function generateTimedCaptions(narrationText, language, totalDuration) {
  if (!narrationText || typeof narrationText !== 'string') {
    return [];
  }

  const clean = narrationText.trim();
  if (!clean) return [];

  const segments = splitIntoSentences(clean);
  const wordCounts = segments.map(s => {
    const words = s.split(/\s+/).filter(Boolean);
    return Math.max(1, words.length);
  });
  const totalWords = wordCounts.reduce((sum, count) => sum + count, 0);

  let currentStartTime = 0;
  return segments.map((segText, index) => {
    const weight = wordCounts[index] / totalWords;
    let segDuration = weight * totalDuration;

    if (segDuration < 1.0 && segments.length > 1) {
      segDuration = Math.min(segDuration, totalDuration / segments.length);
    }

    const startTime = parseFloat(currentStartTime.toFixed(2));
    let endTime = parseFloat((currentStartTime + segDuration).toFixed(2));

    if (index === segments.length - 1 || endTime > totalDuration) {
      endTime = parseFloat(totalDuration.toFixed(2));
    }

    currentStartTime = endTime;
    const duration = parseFloat((endTime - startTime).toFixed(2));

    return {
      index,
      text: segText,
      language,
      startTime,
      endTime,
      duration,
      mathFormulas: extractMathFormulas(segText)
    };
  });
}

/**
 * Production-ready DefaultSceneRenderer with zero-crash fallback guarantees,
 * cache integration, rich visual pass-through, and multimodal rendering.
 * @implements {SceneRenderer}
 */
export class DefaultSceneRenderer extends SceneRenderer {
  /**
   * @param {Object} [config={}]
   * @param {SceneCache} [config.cache]
   * @param {string} [config.defaultTeacherId='teacher-dr-sharma']
   * @param {string} [config.placeholderImage='assets/teacher-placeholder.svg']
   */
  constructor(config = {}) {
    super();
    this.cache = config.cache || null;
    this.defaultTeacherId = config.defaultTeacherId || 'teacher-dr-sharma';
    this.placeholderImage = config.placeholderImage || 'assets/teacher-placeholder.svg';
  }

  /**
   * Renders a full multimodal scene.
   * @param {Object} rawScene - Scene specification from contract schema.
   * @param {Object} [providers={}] - Injected providers.
   * @param {import('./interfaces.js').TTSProvider} [providers.ttsProvider]
   * @param {import('./interfaces.js').AvatarProvider} [providers.avatarProvider]
   * @param {SceneCache} [providers.sceneCache]
   * @param {string} [providers.language]
   * @param {Object} [options={}] - Additional rendering & caching options.
   * @param {boolean} [options.useCache=false]
   * @param {SceneCache} [options.cache]
   * @param {string} [options.language]
   * @returns {Promise<import('./interfaces.js').MediaResult>}
   */
  async renderScene(rawScene, providers = {}, options = {}) {
    // 1. Robust null-safe scene parsing
    const scene = (rawScene && typeof rawScene === 'object') ? rawScene : {};
    const sceneId = scene.id ? String(scene.id) : 'unknown-scene';

    // Narration text normalization
    let narrationText = '';
    if (typeof scene.narration === 'string') {
      narrationText = scene.narration.trim();
    } else if (scene.narration && typeof scene.narration.text === 'string') {
      narrationText = scene.narration.text.trim();
    }

    // Language normalization
    const language = normalizeLanguage(
      options.language || scene.language || providers.language || 'hinglish'
    );

    // 2. Cache check
    const cacheInstance = options.cache || providers.sceneCache || this.cache || (options.useCache ? getDefaultCache() : null);
    if ((options.useCache || options.cache || providers.sceneCache || this.cache) && cacheInstance && sceneId !== 'unknown-scene') {
      const cached = cacheInstance.get(sceneId, language);
      if (cached) {
        return cached;
      }
    }

    // Provider resolution
    const ttsProvider = providers.ttsProvider || new MockTTSProvider();
    const avatarProvider = providers.avatarProvider || new MockAvatarProvider({ teacherId: this.defaultTeacherId });

    // Duration estimation
    const words = narrationText ? narrationText.split(/\s+/).filter(Boolean).length : 0;
    let durationSeconds = Number(scene.durationSeconds);
    if (!durationSeconds || durationSeconds <= 0) {
      durationSeconds = words > 0 ? Math.max(1, Math.ceil(words / 2.5)) : 5;
    }

    // 3. Audio Synthesis (with graceful fallback on failure)
    let audioResult = null;
    let audioSuccess = false;
    let audioErrorMessage = null;

    if (narrationText) {
      try {
        audioResult = await ttsProvider.synthesize(narrationText, language);
        if (audioResult && audioResult.audioUrl) {
          audioSuccess = true;
          if (audioResult.durationSeconds && audioResult.durationSeconds > 0) {
            durationSeconds = audioResult.durationSeconds;
          }
        }
      } catch (err) {
        audioSuccess = false;
        audioErrorMessage = err?.message || 'TTS synthesis failed';
      }
    }

    // 4. Avatar Video Generation (with graceful fallback on failure)
    let avatarResult = null;
    let avatarSuccess = false;
    let avatarErrorMessage = null;

    try {
      avatarResult = await avatarProvider.generateAvatar(
        narrationText,
        audioSuccess && audioResult ? audioResult.audioUrl : null,
        { durationSeconds, language, sceneId }
      );
      if (avatarResult && avatarResult.videoUrl) {
        avatarSuccess = true;
        if (avatarResult.durationSeconds && avatarResult.durationSeconds > 0) {
          durationSeconds = Math.max(durationSeconds, avatarResult.durationSeconds);
        }
      }
    } catch (err) {
      avatarSuccess = false;
      avatarErrorMessage = err?.message || 'Avatar video generation failed';
    }

    // 5. Captions Generation
    const captions = generateTimedCaptions(narrationText, language, durationSeconds);

    // 6. Visual Canvas Pass-Through & Preparation
    const rawVisual = (scene.visual && typeof scene.visual === 'object') ? scene.visual : { type: 'concept_card', data: {} };
    const visualType = rawVisual.type || 'concept_card';
    const visualData = (rawVisual.data && typeof rawVisual.data === 'object') ? rawVisual.data : {};
    
    // Determine render hint
    let renderHint = rawVisual.renderHint || 'standard';
    if (visualData.composite || visualData.diagramType === 'compound_repair') {
      renderHint = 'composite_repair';
    } else if (visualType === 'circuit') {
      renderHint = 'interactive_circuit';
    } else if (visualType === 'graph') {
      renderHint = 'interactive_graph';
    } else if (visualType === 'equation') {
      renderHint = 'step_equation';
    } else if (visualType === 'diagram') {
      renderHint = 'diagram_viewer';
    }

    // 7. Status determination: 'ready' when both providers succeed, 'degraded' when either/both fail
    const isDegraded = !audioSuccess || !avatarSuccess;
    const status = isDegraded ? 'degraded' : 'ready';

    // 8. Build complete MediaResult
    const mediaResult = {
      sceneId,
      language,
      teacherPanel: avatarSuccess && avatarResult ? {
        type: 'video',
        url: avatarResult.videoUrl,
        thumbnailUrl: avatarResult.thumbnailUrl || this.placeholderImage,
        fallback: false
      } : {
        type: 'image',
        url: null,
        thumbnailUrl: this.placeholderImage,
        fallback: true
      },
      audio: audioSuccess && audioResult ? {
        url: audioResult.audioUrl,
        durationSeconds: audioResult.durationSeconds || durationSeconds,
        format: audioResult.format || 'mp3',
        language,
        fallback: false
      } : {
        url: null,
        durationSeconds,
        format: null,
        language,
        fallback: true,
        ...(audioErrorMessage ? { error: audioErrorMessage } : {})
      },
      video: avatarSuccess && avatarResult ? {
        url: avatarResult.videoUrl,
        thumbnailUrl: avatarResult.thumbnailUrl || this.placeholderImage,
        format: avatarResult.format || 'mp4',
        durationSeconds: avatarResult.durationSeconds || durationSeconds,
        fallback: false
      } : {
        url: null,
        thumbnailUrl: this.placeholderImage,
        format: null,
        durationSeconds,
        fallback: true,
        ...(avatarErrorMessage ? { error: avatarErrorMessage } : {})
      },
      visualCanvas: {
        type: visualType,
        data: visualData,
        renderHint
      },
      captions,
      durationSeconds,
      status,
      citations: Array.isArray(scene.citations) ? scene.citations : [],
      metadata: {
        renderedAt: new Date().toISOString(),
        ttsFallback: !audioSuccess,
        avatarFallback: !avatarSuccess,
        isDegraded
      }
    };

    // Save to cache if requested
    if (options.saveToCache && cacheInstance && sceneId !== 'unknown-scene') {
      cacheInstance.set(sceneId, language, mediaResult);
    }

    return mediaResult;
  }
}
