import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  DefaultSceneRenderer,
  MockTTSProvider,
  MockAvatarProvider,
  SceneCache
} from '../src/index.js';

describe('DefaultSceneRenderer Test Suite', () => {
  const sampleCircuitScene = {
    id: 'scene-5-ohms-law',
    conceptId: 'ohms-law',
    objective: "Understand V = IR relationship",
    narration: "Ohm's Law states that V = I * R. If we solve for current, I = V/R. For example, if V is 10V and R is 5Ω, then I = 10 / 5 = 2A.",
    visual: {
      type: 'circuit',
      data: {
        title: "Ohm's Law Closed Circuit Schematic",
        voltage: "10V",
        resistance: "5Ω",
        current: "2A",
        components: [
          { id: 'bat-1', type: 'battery', value: 10, unit: 'V' },
          { id: 'res-1', type: 'resistor', value: 5, unit: 'Ω' },
          { id: 'amm-1', type: 'ammeter', value: 2, unit: 'A' }
        ],
        connections: [
          { id: 'wire-1', fromComponent: 'bat-1', toComponent: 'res-1' }
        ]
      }
    },
    citations: [
      { documentId: 'ncert-class9-science-ch12', pageOrSlide: 204, heading: "12.3 Ohm's Law", excerpt: "V = IR." }
    ],
    durationSeconds: 24
  };

  const sampleCompoundRepairScene = {
    id: 'scene-repair-ohms-law',
    conceptId: 'ohms-law',
    objective: "Repair direct proportionality misconception",
    narration: "Think of water flowing through a pipe. If you narrow the pipe (increase resistance R), the water flow (current I) will DECREASE, not increase! In the formula I = V/R, when Resistance R in the denominator increases, Current I decreases at constant voltage V = 10V.",
    visual: {
      type: 'diagram',
      data: {
        composite: true,
        diagramType: 'compound_repair',
        equation: {
          title: "Formula Transformation: I = V / R",
          steps: [
            { stepIndex: 0, latex: "V = I \\cdot R" },
            { stepIndex: 1, latex: "I = \\frac{V}{R}", highlight: true }
          ]
        },
        analogy: {
          title: "Hydraulic Analogy",
          diagramType: "hydraulic_analogy",
          elements: [{ id: "pipe_constriction", formulaSymbol: "R" }]
        },
        graph: {
          title: "Current (I) vs Resistance (R)",
          formula: "I = 10 / R",
          points: [{ x: 5, y: 2 }, { x: 10, y: 1 }]
        }
      }
    },
    citations: [
      { documentId: 'ncert-class9-science-ch12', pageOrSlide: 205, heading: "12.3 Ohm's Law", excerpt: "Current is inversely proportional to resistance." }
    ],
    durationSeconds: 35
  };

  describe('Happy Path Multimodal Rendering', () => {
    test('renders complete MediaResult with video, audio, visualCanvas, and captions', async () => {
      const renderer = new DefaultSceneRenderer();
      const tts = new MockTTSProvider();
      const avatar = new MockAvatarProvider();

      const result = await renderer.renderScene(sampleCircuitScene, {
        ttsProvider: tts,
        avatarProvider: avatar,
        language: 'hinglish'
      });

      assert.equal(result.sceneId, 'scene-5-ohms-law');
      assert.equal(result.status, 'ready');
      assert.equal(result.language, 'hinglish');

      // Teacher Panel & Video
      assert.equal(result.teacherPanel.type, 'video');
      assert.ok(result.teacherPanel.url.startsWith('mock://avatar/'));
      assert.equal(result.teacherPanel.fallback, false);
      assert.equal(result.video.fallback, false);
      assert.ok(result.video.url.startsWith('mock://avatar/'));

      // Audio
      assert.equal(result.audio.fallback, false);
      assert.ok(result.audio.url.startsWith('mock://tts/'));
      assert.equal(result.audio.format, 'mp3');

      // Visual Canvas Pass-through
      assert.equal(result.visualCanvas.type, 'circuit');
      assert.equal(result.visualCanvas.data.voltage, '10V');
      assert.equal(result.visualCanvas.data.components.length, 3);
      assert.equal(result.visualCanvas.renderHint, 'interactive_circuit');

      // Captions & Math Tokens
      assert.ok(Array.isArray(result.captions));
      assert.ok(result.captions.length > 0);
      assert.equal(result.captions[0].language, 'hinglish');
      
      // Citations
      assert.equal(result.citations.length, 1);
      assert.equal(result.citations[0].documentId, 'ncert-class9-science-ch12');
    });

    test('renders composite 3-in-1 repair scene preserving multi-panel specs', async () => {
      const renderer = new DefaultSceneRenderer();
      const result = await renderer.renderScene(sampleCompoundRepairScene, {
        ttsProvider: new MockTTSProvider(),
        avatarProvider: new MockAvatarProvider(),
        language: 'english'
      });

      assert.equal(result.sceneId, 'scene-repair-ohms-law');
      assert.equal(result.status, 'ready');
      assert.equal(result.visualCanvas.type, 'diagram');
      assert.equal(result.visualCanvas.renderHint, 'composite_repair');
      assert.ok(result.visualCanvas.data.composite);
      assert.ok(result.visualCanvas.data.equation);
      assert.ok(result.visualCanvas.data.analogy);
      assert.ok(result.visualCanvas.data.graph);
    });
  });

  describe('Fallback Guarantees', () => {
    test('falls back gracefully to text-only captions when TTS provider fails', async () => {
      const renderer = new DefaultSceneRenderer();
      const failingTTS = new MockTTSProvider({ shouldFail: true, errorMessage: 'TTS quota exceeded' });
      const workingAvatar = new MockAvatarProvider();

      const result = await renderer.renderScene(sampleCircuitScene, {
        ttsProvider: failingTTS,
        avatarProvider: workingAvatar,
        language: 'hinglish'
      });

      // Status should be degraded
      assert.equal(result.status, 'degraded');

      // Audio fallback check
      assert.equal(result.audio.fallback, true);
      assert.equal(result.audio.url, null);

      // Captions must remain intact
      assert.ok(Array.isArray(result.captions));
      assert.ok(result.captions.length > 0);
      assert.ok(result.captions.some(c => c.text.includes("Ohm's Law")));

      // Video still works since Avatar provider succeeded
      assert.equal(result.teacherPanel.type, 'video');
      assert.equal(result.video.fallback, false);
      assert.ok(result.video.url);
    });

    test('falls back gracefully to static teacher image placeholder when Avatar provider fails', async () => {
      const renderer = new DefaultSceneRenderer();
      const workingTTS = new MockTTSProvider();
      const failingAvatar = new MockAvatarProvider({ shouldFail: true, errorMessage: 'Renderer GPU timeout' });

      const result = await renderer.renderScene(sampleCircuitScene, {
        ttsProvider: workingTTS,
        avatarProvider: failingAvatar,
        language: 'hinglish'
      });

      // Status should be degraded
      assert.equal(result.status, 'degraded');

      // Video fallback check
      assert.equal(result.video.fallback, true);
      assert.equal(result.video.url, null);
      assert.equal(result.video.thumbnailUrl, 'assets/teacher-placeholder.svg');

      // Teacher panel fallback check
      assert.equal(result.teacherPanel.type, 'image');
      assert.equal(result.teacherPanel.url, null);
      assert.equal(result.teacherPanel.thumbnailUrl, 'assets/teacher-placeholder.svg');
      assert.equal(result.teacherPanel.fallback, true);

      // Audio is still intact
      assert.equal(result.audio.fallback, false);
      assert.ok(result.audio.url);
    });

    test('guarantees zero-crash when BOTH TTS and Avatar providers fail', async () => {
      const renderer = new DefaultSceneRenderer();
      const failingTTS = new MockTTSProvider({ shouldFail: true });
      const failingAvatar = new MockAvatarProvider({ shouldFail: true });

      const result = await renderer.renderScene(sampleCircuitScene, {
        ttsProvider: failingTTS,
        avatarProvider: failingAvatar
      });

      // Result must be a valid MediaResult, no exception thrown
      assert.ok(result);
      assert.equal(result.sceneId, 'scene-5-ohms-law');
      assert.equal(result.status, 'degraded');

      // Both fallbacks active
      assert.equal(result.audio.fallback, true);
      assert.equal(result.audio.url, null);
      assert.equal(result.video.fallback, true);
      assert.equal(result.video.url, null);
      assert.equal(result.teacherPanel.type, 'image');
      assert.equal(result.teacherPanel.thumbnailUrl, 'assets/teacher-placeholder.svg');

      // Captions and visuals remain completely functional
      assert.ok(result.captions.length > 0);
      assert.equal(result.visualCanvas.type, 'circuit');
      assert.equal(result.visualCanvas.data.voltage, '10V');
    });
  });

  describe('Null Safety & Malformed Scene Resilience', () => {
    test('handles null or undefined scene safely', async () => {
      const renderer = new DefaultSceneRenderer();
      const resultNull = await renderer.renderScene(null);
      assert.ok(resultNull);
      assert.equal(resultNull.sceneId, 'unknown-scene');
      assert.ok(resultNull.visualCanvas);
      assert.ok(Array.isArray(resultNull.captions));

      const resultUndefined = await renderer.renderScene(undefined);
      assert.ok(resultUndefined);
      assert.equal(resultUndefined.sceneId, 'unknown-scene');
    });

    test('handles scene with missing narration, visual, and citations', async () => {
      const renderer = new DefaultSceneRenderer();
      const bareScene = { id: 'bare-scene-1' };
      const result = await renderer.renderScene(bareScene);

      assert.equal(result.sceneId, 'bare-scene-1');
      assert.equal(result.visualCanvas.type, 'concept_card');
      assert.deepEqual(result.visualCanvas.data, {});
      assert.deepEqual(result.captions, []);
      assert.deepEqual(result.citations, []);
      assert.ok(result.durationSeconds > 0);
    });

    test('handles narration as an object { text: ... }', async () => {
      const renderer = new DefaultSceneRenderer();
      const objNarrationScene = {
        id: 'scene-obj-narration',
        narration: { text: "Narration supplied as object property." }
      };
      const result = await renderer.renderScene(objNarrationScene);

      assert.equal(result.sceneId, 'scene-obj-narration');
      assert.ok(result.captions.length > 0);
      assert.equal(result.captions[0].text, "Narration supplied as object property.");
    });
  });

  describe('Cache Integration', () => {
    test('returns cached descriptor when useCache is enabled and descriptor exists', async () => {
      const cache = new SceneCache({ preSeed: true });
      const renderer = new DefaultSceneRenderer({ cache });

      const result = await renderer.renderScene(
        { id: 'scene-5-ohms-law' },
        {},
        { useCache: true, language: 'hinglish', cache }
      );

      assert.ok(result);
      assert.equal(result.sceneId, 'scene-5-ohms-law');
      assert.equal(result.status, 'ready');
      assert.ok(result.metadata.cached);
    });

    test('saves rendered result to cache when saveToCache is true', async () => {
      const customCache = new SceneCache({ preSeed: false });
      const renderer = new DefaultSceneRenderer();

      assert.equal(customCache.has('custom-scene-x', 'hinglish'), false);

      await renderer.renderScene(
        {
          id: 'custom-scene-x',
          narration: "Custom scene narration for caching test.",
          visual: { type: 'equation', data: { eq: 'V=IR' } }
        },
        {},
        { cache: customCache, saveToCache: true, language: 'hinglish' }
      );

      assert.equal(customCache.has('custom-scene-x', 'hinglish'), true);
      const cached = customCache.get('custom-scene-x', 'hinglish');
      assert.equal(cached.sceneId, 'custom-scene-x');
      assert.equal(cached.visualCanvas.type, 'equation');
    });
  });
});
