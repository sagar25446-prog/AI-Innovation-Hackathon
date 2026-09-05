/**
 * Tests for the pre-rendered avatar provider.
 *
 * Style matches services/media/test/mock-providers.test.js (node:test +
 * node:assert/strict). Run with:
 *
 *     node --test apps/web/test/*.test.js
 *
 * The provider's existence check is injectable precisely so these run with no
 * network, no server and no clip files on disk.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import {
  PrerenderedAvatarProvider,
  clipRoleForScene,
  CLIP_ROLES,
  DEFAULT_CLIP_ROLE,
} from '../src/prerendered-avatar-provider.js';

/** Probe stub: only the listed URLs "exist". */
const probeFor = (available = []) => async (url) => available.includes(url);

describe('PrerenderedAvatarProvider', () => {
  describe('clip URL resolution', () => {
    test('builds the documented path from language and role', () => {
      const provider = new PrerenderedAvatarProvider({ probe: probeFor() });
      assert.equal(
        provider.clipUrl('intro', 'hinglish'),
        '/public/avatars/hinglish/intro.mp4'
      );
    });

    test('falls back to idle for an unknown role', () => {
      const provider = new PrerenderedAvatarProvider({ probe: probeFor() });
      assert.equal(
        provider.clipUrl('nonsense', 'english'),
        '/public/avatars/english/idle.mp4'
      );
    });

    test('falls back to the configured language for an unknown one', () => {
      const provider = new PrerenderedAvatarProvider({
        language: 'english',
        probe: probeFor(),
      });
      assert.equal(
        provider.clipUrl('idle', 'klingon'),
        '/public/avatars/english/idle.mp4'
      );
    });

    test('honours a custom basePath without a trailing slash', () => {
      const provider = new PrerenderedAvatarProvider({
        basePath: '/cdn/clips/',
        probe: probeFor(),
      });
      assert.equal(provider.clipUrl('idle', 'hindi'), '/cdn/clips/hindi/idle.mp4');
    });
  });

  describe('generateAvatar', () => {
    test('returns the clip when the file exists', async () => {
      const url = '/public/avatars/english/intro.mp4';
      const provider = new PrerenderedAvatarProvider({ probe: probeFor([url]) });

      const result = await provider.generateAvatar('narration', 'audio.mp3', {
        clipRole: 'intro',
        language: 'english',
        durationSeconds: 12,
      });

      assert.equal(result.videoUrl, url);
      assert.equal(result.format, 'mp4');
      assert.equal(result.isFallback, false);
      assert.equal(result.clipRole, 'intro');
      assert.equal(result.durationSeconds, 12);
    });

    test('THROWS when the clip is absent, rather than returning a broken URL', async () => {
      const provider = new PrerenderedAvatarProvider({ probe: probeFor() });
      await assert.rejects(
        () => provider.generateAvatar('n', null, { clipRole: 'idle' }),
        /No pre-rendered avatar clip/
      );
    });

    test('the thrown error names the folder to drop files into', async () => {
      const provider = new PrerenderedAvatarProvider({ probe: probeFor() });
      await assert.rejects(
        () => provider.generateAvatar('n', null, { clipRole: 'intro', language: 'hindi' }),
        (error) => {
          assert.match(error.message, /apps\/web\/public\/avatars\/hindi\//);
          return true;
        }
      );
    });

    test('defaults to the idle clip when no role is given', async () => {
      const url = '/public/avatars/english/idle.mp4';
      const provider = new PrerenderedAvatarProvider({ probe: probeFor([url]) });
      const result = await provider.generateAvatar('n', null, {});
      assert.equal(result.clipRole, DEFAULT_CLIP_ROLE);
      assert.equal(result.videoUrl, url);
    });

    test('an unknown role resolves to idle rather than throwing', async () => {
      const url = '/public/avatars/english/idle.mp4';
      const provider = new PrerenderedAvatarProvider({ probe: probeFor([url]) });
      const result = await provider.generateAvatar('n', null, { clipRole: 'wat' });
      assert.equal(result.clipRole, DEFAULT_CLIP_ROLE);
    });

    test('a missing clip for one role does not poison another', async () => {
      const intro = '/public/avatars/english/intro.mp4';
      const provider = new PrerenderedAvatarProvider({ probe: probeFor([intro]) });

      await assert.rejects(() =>
        provider.generateAvatar('n', null, { clipRole: 'complete' })
      );
      const ok = await provider.generateAvatar('n', null, { clipRole: 'intro' });
      assert.equal(ok.videoUrl, intro);
    });
  });

  describe('availability caching', () => {
    test('probes each URL once', async () => {
      let calls = 0;
      const provider = new PrerenderedAvatarProvider({
        probe: async () => {
          calls += 1;
          return true;
        },
      });

      await provider.generateAvatar('n', null, { clipRole: 'idle' });
      await provider.generateAvatar('n', null, { clipRole: 'idle' });
      assert.equal(calls, 1, 'second call should use the cached result');
    });

    test('clearing the cache re-probes, so newly added clips are picked up', async () => {
      let exists = false;
      const provider = new PrerenderedAvatarProvider({ probe: async () => exists });

      await assert.rejects(() => provider.generateAvatar('n', null, {}));
      exists = true; // clip dropped in on disk
      provider.clearAvailabilityCache();
      const result = await provider.generateAvatar('n', null, {});
      assert.equal(result.isFallback, false);
    });

    test('a probe that throws is treated as "absent", not a crash', async () => {
      const provider = new PrerenderedAvatarProvider({
        probe: async () => {
          throw new Error('network down');
        },
      });
      await assert.rejects(
        () => provider.generateAvatar('n', null, {}),
        /No pre-rendered avatar clip/
      );
    });
  });

  describe('clipRoleForScene', () => {
    test('first scene is the intro', () => {
      assert.equal(clipRoleForScene({ sceneIndex: 0 }), 'intro');
    });

    test('a repair scene wins over position', () => {
      assert.equal(
        clipRoleForScene({ sceneIndex: 0, isRepair: true }),
        'repair_transition'
      );
    });

    test('the report is complete', () => {
      assert.equal(clipRoleForScene({ isReport: true, sceneIndex: 3 }), 'complete');
    });

    test('a correct answer picks the correct clip', () => {
      assert.equal(clipRoleForScene({ sceneIndex: 4, answeredCorrectly: true }), 'correct');
    });

    test('anything else is idle', () => {
      assert.equal(clipRoleForScene({ sceneIndex: 3 }), DEFAULT_CLIP_ROLE);
      assert.equal(clipRoleForScene(), DEFAULT_CLIP_ROLE);
    });

    test('every returned role is a real role', () => {
      const contexts = [
        { sceneIndex: 0 },
        { isRepair: true },
        { isReport: true },
        { answeredCorrectly: true, sceneIndex: 2 },
        {},
      ];
      for (const context of contexts) {
        assert.ok(CLIP_ROLES.includes(clipRoleForScene(context)));
      }
    });
  });
});

describe('interface conformance', () => {
  test('matches the real AvatarProvider contract', async () => {
    // Imported by relative path (Node-resolvable). The provider itself cannot
    // import this, because media-adapter.js reaches it through the browser-only
    // /vendor mount - hence structural implementation plus this check.
    const { AvatarProvider } = await import(
      '../../../services/media/src/interfaces.js'
    );

    const base = new AvatarProvider();
    const ours = new PrerenderedAvatarProvider();

    assert.equal(typeof base.generateAvatar, 'function');
    assert.equal(typeof ours.generateAvatar, 'function');
    // Same arity, so the renderer can call either interchangeably.
    assert.equal(ours.generateAvatar.length, base.generateAvatar.length);
  });

  test('the abstract base still refuses to be used directly', async () => {
    const { AvatarProvider } = await import(
      '../../../services/media/src/interfaces.js'
    );
    await assert.rejects(() => new AvatarProvider().generateAvatar('n', null, {}));
  });
});

// ---------------------------------------------------------------------------
// Narration must never overlap itself
// ---------------------------------------------------------------------------

describe('speech play tokens', () => {
  /** Minimal stand-in for the token guard in ServerTTSProvider. */
  class Speaker {
    constructor() {
      this._playToken = 0;
      this.played = [];
    }
    stop() {
      this._playToken += 1;
    }
    speak(label, resolveLater) {
      this.stop();
      const token = this._playToken;
      return resolveLater().then(() => {
        if (token !== this._playToken) return 'discarded';
        this.played.push(label);
        return 'played';
      });
    }
  }

  test('a response that arrives after a newer speak is discarded', async () => {
    const s = new Speaker();
    let releaseFirst;
    const first = s.speak('hindi', () => new Promise((r) => { releaseFirst = r; }));
    const second = s.speak('tamil', () => Promise.resolve());

    await second;
    releaseFirst();
    assert.equal(await first, 'discarded');
    assert.deepEqual(s.played, ['tamil'], 'only the newest narration may play');
  });

  test('stop() alone invalidates an in-flight response', async () => {
    const s = new Speaker();
    let release;
    const pending = s.speak('hindi', () => new Promise((r) => { release = r; }));
    s.stop();
    release();
    assert.equal(await pending, 'discarded');
    assert.deepEqual(s.played, []);
  });

  test('an uninterrupted response still plays', async () => {
    const s = new Speaker();
    assert.equal(await s.speak('english', () => Promise.resolve()), 'played');
    assert.deepEqual(s.played, ['english']);
  });
});
