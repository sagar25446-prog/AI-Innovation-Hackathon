import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  SceneCache,
  cachedDescriptors,
  getCachedDescriptor,
  normalizeLanguage,
  normalizeSceneId
} from '../src/index.js';

describe('SceneCache Test Suite', () => {
  describe('Basic Cache CRUD Operations', () => {
    test('stores and retrieves descriptors with language indexing', () => {
      const cache = new SceneCache({ preSeed: false });
      const sampleDescriptor = {
        sceneId: 'test-scene-1',
        language: 'hinglish',
        status: 'ready'
      };

      assert.equal(cache.has('test-scene-1', 'hinglish'), false);
      assert.equal(cache.get('test-scene-1', 'hinglish'), null);

      cache.set('test-scene-1', 'hinglish', sampleDescriptor);

      assert.equal(cache.has('test-scene-1', 'hinglish'), true);
      const retrieved = cache.get('test-scene-1', 'hinglish');
      assert.ok(retrieved);
      assert.equal(retrieved.sceneId, 'test-scene-1');
      assert.equal(retrieved.language, 'hinglish');
      assert.equal(cache.size, 1);
    });

    test('deletes descriptors and clears cache', () => {
      const cache = new SceneCache({ preSeed: false });
      cache.set('scene-a', 'english', { id: 'scene-a' });
      cache.set('scene-b', 'hindi', { id: 'scene-b' });
      assert.equal(cache.size, 2);

      const deleted = cache.delete('scene-a', 'english');
      assert.equal(deleted, true);
      assert.equal(cache.size, 1);
      assert.equal(cache.has('scene-a', 'english'), false);

      cache.clear();
      assert.equal(cache.size, 0);
      assert.deepEqual(cache.keys(), []);
      assert.deepEqual(cache.getAll(), []);
    });

    test('protects cache against mutation via object cloning', () => {
      const cache = new SceneCache({ preSeed: false });
      const original = { sceneId: 'test-mut', data: { value: 42 } };
      cache.set('test-mut', 'english', original);

      const retrieved = cache.get('test-mut', 'english');
      retrieved.data.value = 999;

      const secondRetrieval = cache.get('test-mut', 'english');
      assert.equal(secondRetrieval.data.value, 42);
    });

    test('normalizes language and sceneId aliases', () => {
      const cache = new SceneCache({ preSeed: true });

      // English aliases: 'en', 'ENG', 'english'
      assert.ok(cache.get('scene-5-ohms-law', 'en'));
      assert.ok(cache.get('scene-5-ohms-law', 'ENG'));
      assert.ok(cache.get('scene-5-ohms-law', 'english'));

      // Hindi aliases: 'hi', 'HINDI', 'hin'
      assert.ok(cache.get('scene-5-ohms-law', 'hi'));
      assert.ok(cache.get('scene-5-ohms-law', 'hindi'));

      // Scene aliases: 'scene-5', 'scene-5-ohms-law', 'scene-ohms-law'
      assert.ok(cache.get('scene-5', 'hinglish'));
      assert.ok(cache.get('scene-5-ohms-law', 'hinglish'));
      assert.ok(cache.get('scene-ohms-law', 'hinglish'));

      // Repair scene aliases: 'scene-repair', 'scene-repair-ohms-law', 'ohms-law-repair-scene'
      assert.ok(cache.get('scene-repair', 'hinglish'));
      assert.ok(cache.get('scene-repair-ohms-law', 'hinglish'));
      assert.ok(cache.get('ohms-law-repair-scene', 'hinglish'));
    });
  });

  describe('Pre-seeded Hero Demo Lookups', () => {
    test('contains pre-seeded descriptors for all 6 demo scenes across 3 languages', () => {
      const cache = new SceneCache({ preSeed: true });
      assert.ok(cache.size >= 18, `Expected at least 18 pre-seeded items, found ${cache.size}`);

      const demoScenes = [
        'scene-1-intro',
        'scene-2-voltage',
        'scene-3-resistance',
        'scene-5-ohms-law',
        'scene-advance-circuits',
        'scene-repair-ohms-law'
      ];

      const languages = ['english', 'hindi', 'hinglish'];

      for (const sId of demoScenes) {
        for (const lang of languages) {
          const item = cache.get(sId, lang);
          assert.ok(item, `Missing cached descriptor for ${sId} in ${lang}`);
          assert.equal(item.status, 'ready');
          assert.ok(item.teacherPanel);
          assert.ok(item.audio);
          assert.ok(item.video);
          assert.ok(item.visualCanvas);
          assert.ok(Array.isArray(item.captions));
          assert.ok(item.captions.length > 0);
          assert.ok(item.durationSeconds > 0);
        }
      }
    });

    test('getCachedDescriptor standalone function retrieves pre-seeded items', () => {
      const itemHinglish = getCachedDescriptor('scene-5-ohms-law', 'hinglish');
      assert.ok(itemHinglish);
      assert.equal(itemHinglish.sceneId, 'scene-5-ohms-law');
      assert.equal(itemHinglish.language, 'hinglish');

      const itemHindi = getCachedDescriptor('scene-repair-ohms-law', 'hindi');
      assert.ok(itemHindi);
      assert.equal(itemHindi.sceneId, 'scene-repair-ohms-law');
      assert.equal(itemHindi.language, 'hindi');

      const nonExistent = getCachedDescriptor('non-existent-scene', 'english');
      assert.equal(nonExistent, null);
    });
  });

  describe('Helper Normalization Functions', () => {
    test('normalizeLanguage handles variations', () => {
      assert.equal(normalizeLanguage('en'), 'english');
      assert.equal(normalizeLanguage('ENGLISH'), 'english');
      assert.equal(normalizeLanguage('hi'), 'hindi');
      assert.equal(normalizeLanguage('hindi'), 'hindi');
      assert.equal(normalizeLanguage('hinglish'), 'hinglish');
      assert.equal(normalizeLanguage('hi-latn'), 'hinglish');
      assert.equal(normalizeLanguage(null), 'hinglish');
    });

    test('every supported language keeps its own identity', () => {
      // The regression that made language switching look broken: anything
      // outside the original three collapsed to 'hinglish', so all thirteen
      // extended languages shared one cache slot. A Tamil lesson asked for
      // scene-1::hinglish, got the Hinglish descriptor, and replayed it.
      for (const language of [
        'bengali', 'bhojpuri', 'gujarati', 'kannada', 'malayalam', 'marathi',
        'nepali', 'odia', 'punjabi', 'sinhala', 'tamil', 'telugu', 'urdu',
      ]) {
        assert.equal(normalizeLanguage(language), language);
        assert.equal(normalizeLanguage(language.toUpperCase()), language);
      }
    });

    test('only genuinely unusable input falls back to hinglish', () => {
      assert.equal(normalizeLanguage('klingon'), 'hinglish');
      assert.equal(normalizeLanguage(''), 'hinglish');
      assert.equal(normalizeLanguage(42), 'hinglish');
    });

    test('normalizeSceneId handles variations', () => {
      assert.equal(normalizeSceneId('scene-1'), 'scene-1-intro');
      assert.equal(normalizeSceneId('scene-1-current'), 'scene-1-intro');
      assert.equal(normalizeSceneId('scene-2'), 'scene-2-voltage');
      assert.equal(normalizeSceneId('scene-3'), 'scene-3-resistance');
      assert.equal(normalizeSceneId('scene-5'), 'scene-5-ohms-law');
      assert.equal(normalizeSceneId('scene-advance'), 'scene-advance-circuits');
      assert.equal(normalizeSceneId('ohms-law-repair-scene'), 'scene-repair-ohms-law');
    });
  });
});

// ---------------------------------------------------------------------------
// The cache must not let one language answer for another
// ---------------------------------------------------------------------------

test('SceneCache keeps languages apart', async (t) => {
  const { SceneCache } = await import('../src/scene-cache.js');

  await t.test('a descriptor stored for one language is not served for another', () => {
    const cache = new SceneCache();
    cache.set('scene-x-topic', 'tamil', { sceneId: 'scene-x-topic', language: 'tamil' });

    assert.equal(cache.get('scene-x-topic', 'tamil').language, 'tamil');
    // Before the fix both of these returned the Tamil descriptor, because
    // every extended language normalised to 'hinglish'.
    assert.equal(cache.get('scene-x-topic', 'bengali'), null);
    assert.equal(cache.get('scene-x-topic', 'hinglish'), null);
  });

  await t.test('each language gets its own slot for the same scene', () => {
    const cache = new SceneCache();
    const languages = ['tamil', 'bengali', 'bhojpuri', 'odia', 'hinglish'];
    languages.forEach((language) => {
      cache.set('scene-y-topic', language, { sceneId: 'scene-y-topic', language });
    });
    languages.forEach((language) => {
      assert.equal(cache.get('scene-y-topic', language).language, language);
    });
  });

  await t.test('re-teaching a topic in a new language does not replay the old one', () => {
    // The reported bug: finish Ohm's Law in Hinglish, start it again in Tamil,
    // and the lesson came back in Hinglish because the scene ids are identical
    // between runs and the cache key ignored the language.
    const cache = new SceneCache();
    cache.set('scene-5-ohms-law-x', 'hinglish', { captions: ['Ohm ka niyam'] });
    assert.equal(cache.has('scene-5-ohms-law-x', 'tamil'), false);
  });
});
