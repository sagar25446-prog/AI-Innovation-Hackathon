import { cachedDescriptors, normalizeLanguage, normalizeSceneId } from './cached-descriptors.js';

/**
 * High-performance deterministic scene descriptor cache for GuruFlow.
 * Supports instant demo retrieval, pre-seeding, and runtime mutation.
 */
export class SceneCache {
  /**
   * @param {Object} [options={}]
   * @param {boolean} [options.preSeed=true] - Whether to pre-seed with cachedDescriptors.
   * @param {Array<[string, Object]>|Map<string, Object>} [options.initialEntries] - Custom entries.
   */
  constructor(options = {}) {
    this._store = new Map();

    const preSeed = options.preSeed !== false;
    if (preSeed) {
      for (const [key, value] of cachedDescriptors.entries()) {
        this._store.set(key, structuredClone ? structuredClone(value) : JSON.parse(JSON.stringify(value)));
      }
    }

    if (options.initialEntries) {
      const entries = options.initialEntries instanceof Map
        ? options.initialEntries.entries()
        : options.initialEntries;
      for (const [k, v] of entries) {
        this._store.set(k, v);
      }
    }
  }

  /**
   * Generates canonical cache key.
   * @param {string} sceneId
   * @param {string} [language='hinglish']
   * @returns {string}
   */
  _buildKey(sceneId, language = 'hinglish') {
    const s = normalizeSceneId(sceneId);
    const l = normalizeLanguage(language);
    return `${s}::${l}`;
  }

  /**
   * Retrieves a descriptor from cache.
   * @param {string} sceneId
   * @param {string} [language='hinglish']
   * @returns {Object|null}
   */
  get(sceneId, language = 'hinglish') {
    if (!sceneId) return null;
    const key = this._buildKey(sceneId, language);
    const item = this._store.get(key);
    if (!item) return null;
    // Return a clone to prevent external mutation
    return structuredClone ? structuredClone(item) : JSON.parse(JSON.stringify(item));
  }

  /**
   * Sets a descriptor in the cache.
   * @param {string} sceneId
   * @param {string} language
   * @param {Object} descriptor
   */
  set(sceneId, language = 'hinglish', descriptor) {
    if (!sceneId || !descriptor) return;
    const key = this._buildKey(sceneId, language);
    this._store.set(key, structuredClone ? structuredClone(descriptor) : JSON.parse(JSON.stringify(descriptor)));
  }

  /**
   * Checks if a scene descriptor exists in cache.
   * @param {string} sceneId
   * @param {string} [language='hinglish']
   * @returns {boolean}
   */
  has(sceneId, language = 'hinglish') {
    if (!sceneId) return false;
    const key = this._buildKey(sceneId, language);
    return this._store.has(key);
  }

  /**
   * Deletes an entry from cache.
   * @param {string} sceneId
   * @param {string} [language='hinglish']
   * @returns {boolean}
   */
  delete(sceneId, language = 'hinglish') {
    if (!sceneId) return false;
    const key = this._buildKey(sceneId, language);
    return this._store.delete(key);
  }

  /**
   * Clears all cache entries.
   */
  clear() {
    this._store.clear();
  }

  /**
   * Returns current count of cached descriptors.
   * @returns {number}
   */
  get size() {
    return this._store.size;
  }

  /**
   * Returns array of all cache keys.
   * @returns {Array<string>}
   */
  keys() {
    return Array.from(this._store.keys());
  }

  /**
   * Returns array of all cached descriptors.
   * @returns {Array<Object>}
   */
  getAll() {
    return Array.from(this._store.values()).map(item =>
      structuredClone ? structuredClone(item) : JSON.parse(JSON.stringify(item))
    );
  }
}
