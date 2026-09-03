/**
 * Pre-rendered avatar provider.
 *
 * Serves short talking-head clips generated **offline** with SadTalker, one per
 * lesson moment, rather than generating video at request time. SadTalker needs
 * a GPU and takes minutes per clip, so nothing is generated live: the clips are
 * rendered once, dropped on disk, and played back.
 *
 * Expected layout, served by the API's static mount:
 *
 *     apps/web/public/avatars/<language>/<role>.mp4
 *       -> /public/avatars/<language>/<role>.mp4
 *
 * Roles: intro, idle, correct, repair_transition, complete.
 * Languages: english, hindi, hinglish.
 *
 * **Until those files exist this provider throws**, by design. The media
 * pipeline treats a throwing avatar provider as "no avatar configured" and
 * falls back to the drawn teacher panel, so the product behaves exactly as it
 * does today until real clips are dropped in. It never returns a URL it has
 * not confirmed, because a broken <video> src is worse than a clean fallback.
 *
 * Portrait rights: the clips must show a face you have the right to use - a
 * synthetic portrait, a licensed stock portrait, or someone who has consented.
 */

/*
 * Note on the missing import.
 *
 * The obvious thing is `import { AvatarProvider } from
 * '/vendor/media/interfaces.js'` and `extends AvatarProvider`, as
 * media-adapter.js does. That path is a *browser* URL served by the API's
 * /vendor mount, so Node resolves it as a filesystem path and the module
 * cannot be imported outside a browser - which makes it untestable.
 *
 * `DefaultSceneRenderer` duck-types its avatar provider (it only ever calls
 * `generateAvatar`), so this class implements the interface structurally
 * instead of by inheritance. `prerendered-avatar-provider.test.js` asserts
 * conformance against the real `AvatarProvider` to keep that honest.
 */

/** Lesson moments a clip can exist for. */
export const CLIP_ROLES = Object.freeze([
  'intro',
  'idle',
  'correct',
  'repair_transition',
  'complete',
]);

export const DEFAULT_CLIP_ROLE = 'idle';

export const SUPPORTED_LANGUAGES = Object.freeze(['english', 'hindi', 'hinglish']);

const DEFAULT_BASE_PATH = '/public/avatars';

/**
 * Default existence probe. A HEAD request is enough to know whether the clip
 * is on disk, and avoids downloading the file just to find out.
 * @param {string} url
 * @returns {Promise<boolean>}
 */
async function headProbe(url) {
  try {
    const response = await fetch(url, { method: 'HEAD' });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Plays pre-rendered SadTalker clips per lesson moment.
 * @implements {import('../../../services/media/src/interfaces.js').AvatarProvider}
 */
export class PrerenderedAvatarProvider {
  /**
   * @param {Object} [options={}]
   * @param {string} [options.basePath='/public/avatars'] - Root the clips are served from.
   * @param {string} [options.language='english'] - Default language when a call omits one.
   * @param {(url: string) => Promise<boolean>} [options.probe] - Existence check; injectable for tests.
   */
  constructor(options = {}) {
    this.basePath = String(options.basePath || DEFAULT_BASE_PATH).replace(/\/$/, '');
    this.language = options.language || 'english';
    this.probe = options.probe || headProbe;
    /** @type {Map<string, boolean>} url -> exists. Avoids re-probing every scene. */
    this.availability = new Map();
  }

  /**
   * Resolve a role to its clip URL. Unknown roles fall back to `idle` rather
   * than 404-ing on a typo.
   * @param {string} role
   * @param {string} language
   * @returns {string}
   */
  clipUrl(role, language) {
    const safeRole = CLIP_ROLES.includes(role) ? role : DEFAULT_CLIP_ROLE;
    const safeLanguage = SUPPORTED_LANGUAGES.includes(language)
      ? language
      : this.language;
    return `${this.basePath}/${safeLanguage}/${safeRole}.mp4`;
  }

  /**
   * Whether a clip is present on disk. Memoised per URL.
   * @param {string} url
   * @returns {Promise<boolean>}
   */
  async isAvailable(url) {
    if (this.availability.has(url)) return this.availability.get(url);
    let exists = false;
    try {
      exists = Boolean(await this.probe(url));
    } catch {
      // A probe that fails means "cannot confirm", which is treated exactly
      // like "absent". A transient network error must degrade to the drawn
      // panel, never propagate out and break the lesson.
      exists = false;
    }
    this.availability.set(url, exists);
    return exists;
  }

  /** Forget cached probe results, so newly added clips are picked up. */
  clearAvailabilityCache() {
    this.availability.clear();
  }

  /**
   * Return the pre-rendered clip for this lesson moment.
   *
   * @param {string} narration - Narration transcript (unused; clips are generic per role).
   * @param {string|null} audioUrl - Narration audio, played alongside by the caller.
   * @param {Object} [options={}]
   * @param {string} [options.clipRole='idle'] - Lesson moment.
   * @param {string} [options.language] - Teaching language.
   * @param {number} [options.durationSeconds=0]
   * @returns {Promise<{videoUrl: string, thumbnailUrl: string, format: string, durationSeconds: number, isFallback: boolean, clipRole: string}>}
   * @throws {Error} When the clip is not on disk, so the caller degrades to the drawn panel.
   */
  async generateAvatar(narration, audioUrl, options = {}) {
    const role = CLIP_ROLES.includes(options.clipRole)
      ? options.clipRole
      : DEFAULT_CLIP_ROLE;
    const language = options.language || this.language;
    const url = this.clipUrl(role, language);

    if (!(await this.isAvailable(url))) {
      // Deliberate: throwing is how the pipeline learns to use the fallback
      // panel. Returning an unverified URL would render a broken player.
      throw new Error(
        `No pre-rendered avatar clip at ${url}. ` +
          `Add ${role}.mp4 under apps/web/public/avatars/${language}/, ` +
          `or leave it absent to keep the drawn teacher panel.`
      );
    }

    return {
      videoUrl: url,
      thumbnailUrl: '',
      format: 'mp4',
      durationSeconds: Number(options.durationSeconds || 0),
      isFallback: false,
      clipRole: role,
    };
  }
}

/**
 * Pick the clip role for a lesson moment.
 *
 * Kept a pure function so the mapping is testable without a running lesson.
 *
 * @param {Object} [context={}]
 * @param {number} [context.sceneIndex] - Zero-based index in the lesson.
 * @param {boolean} [context.isRepair] - Scene is a misconception repair.
 * @param {boolean} [context.isReport] - Learner is on the final report.
 * @param {boolean} [context.answeredCorrectly] - Last checkpoint answer was correct.
 * @returns {string} One of CLIP_ROLES.
 */
export function clipRoleForScene(context = {}) {
  if (context.isReport) return 'complete';
  if (context.isRepair) return 'repair_transition';
  if (context.answeredCorrectly) return 'correct';
  if (context.sceneIndex === 0) return 'intro';
  return DEFAULT_CLIP_ROLE;
}
