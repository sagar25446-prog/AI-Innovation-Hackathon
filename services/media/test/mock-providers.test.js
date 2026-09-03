import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  MockTTSProvider,
  MockAvatarProvider,
  createTTSProvider,
  createAvatarProvider,
  createSceneRenderer,
  createSceneCache,
  createProviderFactory
} from '../src/index.js';

describe('Media Providers Test Suite', () => {
  describe('MockTTSProvider', () => {
    test('synthesizes text to speech with word-count duration and deterministic URL', async () => {
      const provider = new MockTTSProvider();
      const text = "Ohm's Law states that V equals I times R.";
      const result = await provider.synthesize(text, 'english');

      assert.ok(result.audioUrl);
      assert.ok(result.audioUrl.startsWith('mock://tts/english/'));
      assert.ok(result.audioUrl.endsWith('.mp3'));
      assert.equal(result.format, 'mp3');
      assert.equal(result.language, 'english');
      assert.equal(result.text, text);
      assert.equal(result.isFallback, false);
      assert.ok(result.durationSeconds >= 1);
    });

    test('calculates duration proportionally based on word count', async () => {
      const provider = new MockTTSProvider();
      
      // Short phrase: 2 words -> ~1 sec
      const shortResult = await provider.synthesize('Hello students!', 'hinglish');
      assert.equal(shortResult.durationSeconds, 1);

      // 25 words -> ceil(25 / 2.5) = 10 sec
      const words25 = Array(25).fill('word').join(' ');
      const longResult = await provider.synthesize(words25, 'hinglish');
      assert.equal(longResult.durationSeconds, 10);
    });

    test('generates deterministic MD5 hash for identical text and language', async () => {
      const provider = new MockTTSProvider();
      const res1 = await provider.synthesize('Electric current is the rate of charge flow.', 'english');
      const res2 = await provider.synthesize('Electric current is the rate of charge flow.', 'english');
      assert.equal(res1.audioUrl, res2.audioUrl);

      // Different language should result in different URL
      const resHindi = await provider.synthesize('Electric current is the rate of charge flow.', 'hindi');
      assert.notEqual(res1.audioUrl, resHindi.audioUrl);
    });

    test('simulates provider failure when shouldFail is true', async () => {
      const provider = new MockTTSProvider({ shouldFail: true, errorMessage: 'TTS service offline' });
      await assert.rejects(
        async () => {
          await provider.synthesize('Testing failure', 'hinglish');
        },
        {
          name: 'Error',
          message: 'TTS service offline'
        }
      );
    });

    test('supports dynamic toggling of shouldFail flag', async () => {
      const provider = new MockTTSProvider({ shouldFail: false });
      const okResult = await provider.synthesize('Success path', 'english');
      assert.ok(okResult.audioUrl);

      provider.setShouldFail(true, 'Simulated failure');
      await assert.rejects(
        async () => {
          await provider.synthesize('Fail path', 'english');
        },
        /Simulated failure/
      );

      provider.setShouldFail(false);
      const recoveredResult = await provider.synthesize('Recovered', 'english');
      assert.ok(recoveredResult.audioUrl);
    });

    test('simulates latency (>2000ms) correctly without failure', async () => {
      const simulatedLatency = 2050; // > 2000ms
      const provider = new MockTTSProvider({ latencyMs: simulatedLatency });
      
      const startTime = Date.now();
      const result = await provider.synthesize('High latency test narration', 'hinglish');
      const elapsed = Date.now() - startTime;

      assert.ok(result.audioUrl);
      assert.ok(elapsed >= 2000, `Expected elapsed >= 2000ms, got ${elapsed}ms`);
    });
  });

  describe('MockAvatarProvider', () => {
    test('generates avatar video and thumbnail metadata', async () => {
      const provider = new MockAvatarProvider({ teacherId: 'teacher-dr-sharma' });
      const narration = "Think of water flowing through a pipe.";
      const audioUrl = "mock://tts/hinglish/abcdef12.mp3";
      
      const result = await provider.generateAvatar(narration, audioUrl, { durationSeconds: 20 });

      assert.ok(result.videoUrl);
      assert.ok(result.videoUrl.startsWith('mock://avatar/teacher-dr-sharma/'));
      assert.ok(result.videoUrl.endsWith('.mp4'));
      assert.ok(result.thumbnailUrl);
      assert.ok(result.thumbnailUrl.includes('thumb_'));
      assert.equal(result.format, 'mp4');
      assert.equal(result.durationSeconds, 20);
      assert.equal(result.isFallback, false);
    });

    test('generates deterministic URLs based on teacherId, audioUrl, and narration', async () => {
      const provider = new MockAvatarProvider();
      const res1 = await provider.generateAvatar("Same narration", "mock://tts/audio1.mp3");
      const res2 = await provider.generateAvatar("Same narration", "mock://tts/audio1.mp3");
      assert.equal(res1.videoUrl, res2.videoUrl);
      assert.equal(res1.thumbnailUrl, res2.thumbnailUrl);

      const resDifferent = await provider.generateAvatar("Different narration", "mock://tts/audio2.mp3");
      assert.notEqual(res1.videoUrl, resDifferent.videoUrl);
    });

    test('simulates provider failure when shouldFail is true', async () => {
      const provider = new MockAvatarProvider({ shouldFail: true, errorMessage: 'GPU rendering capacity exceeded' });
      await assert.rejects(
        async () => {
          await provider.generateAvatar('Narration', 'mock://tts/1.mp3');
        },
        {
          name: 'Error',
          message: 'GPU rendering capacity exceeded'
        }
      );
    });

    test('supports dynamic toggling of shouldFail and setLatency', async () => {
      const provider = new MockAvatarProvider();
      provider.setShouldFail(true, 'Network disconnect');
      await assert.rejects(
        async () => {
          await provider.generateAvatar('Test', 'mock://audio.mp3');
        },
        /Network disconnect/
      );

      provider.setShouldFail(false);
      provider.setLatency(2050); // > 2000ms
      const startTime = Date.now();
      const res = await provider.generateAvatar('Test latency', 'mock://audio.mp3');
      const elapsed = Date.now() - startTime;

      assert.ok(res.videoUrl);
      assert.ok(elapsed >= 2000, `Expected elapsed >= 2000ms, got ${elapsed}ms`);
    });
  });

  describe('Provider Factory', () => {
    test('creates configured provider instances', () => {
      const tts = createTTSProvider({ latencyMs: 50, shouldFail: false });
      assert.ok(tts instanceof MockTTSProvider);
      assert.equal(tts.latencyMs, 50);

      const avatar = createAvatarProvider({ teacherId: 'custom-teacher' });
      assert.ok(avatar instanceof MockAvatarProvider);
      assert.equal(avatar.teacherId, 'custom-teacher');

      const renderer = createSceneRenderer();
      assert.ok(renderer);

      const cache = createSceneCache({ preSeed: false });
      assert.equal(cache.size, 0);

      const factory = createProviderFactory({
        tts: { latencyMs: 10 },
        avatar: { teacherId: 'prof-gupta' }
      });
      assert.ok(factory.ttsProvider);
      assert.ok(factory.avatarProvider);
      assert.ok(factory.sceneCache);
      assert.ok(factory.sceneRenderer);
    });
  });
});
