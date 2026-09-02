import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  DefaultSceneRenderer,
  MockTTSProvider,
  MockAvatarProvider,
  SceneCache,
  getCachedDescriptor
} from '../src/index.js';

describe('Multilingual & Formula Invariance Test Suite', () => {
  const languages = ['english', 'hindi', 'hinglish'];

  describe('Multilingual Scene Rendering & Captions Alignment', () => {
    test('renders scene in English, Hindi, and Hinglish with language-aligned captions', async () => {
      const renderer = new DefaultSceneRenderer();

      const testScenes = {
        english: {
          id: 'scene-5-ohms-law',
          narration: "Ohm's Law states that V = I * R. If we solve for current, I = V/R. For example, if V is 10V and R is 5Ω, then I = 10 / 5 = 2A."
        },
        hindi: {
          id: 'scene-5-ohms-law',
          narration: "ओम का नियम कहता है कि V = I * R। यदि धारा निकालें, तो I = V/R। उदाहरण के लिए, यदि V 10V है और R 5Ω है, तो I = 10 / 5 = 2A।"
        },
        hinglish: {
          id: 'scene-5-ohms-law',
          narration: "Ohm's Law kehta hai ki V = I * R. Agar current nikalein, toh I = V/R hota hai. For example, agar V 10V hai aur R 5Ω hai, toh I = 10 / 5 = 2A hoga."
        }
      };

      for (const lang of languages) {
        const scene = testScenes[lang];
        const result = await renderer.renderScene(scene, {
          ttsProvider: new MockTTSProvider(),
          avatarProvider: new MockAvatarProvider(),
          language: lang
        });

        assert.equal(result.status, 'ready');
        assert.equal(result.language, lang);
        assert.ok(Array.isArray(result.captions));
        assert.ok(result.captions.length > 0);

        // Verify caption segments match narration language
        for (const cap of result.captions) {
          assert.equal(cap.language, lang);
          assert.ok(cap.text.length > 0);
        }

        // Full caption text reconstructed should match words from narration
        const combinedCaptionText = result.captions.map(c => c.text).join(' ');
        if (lang === 'english') {
          assert.ok(combinedCaptionText.includes("Ohm's Law"));
        } else if (lang === 'hindi') {
          assert.ok(combinedCaptionText.includes("ओम का नियम"));
        } else if (lang === 'hinglish') {
          assert.ok(combinedCaptionText.includes("Ohm's Law kehta hai"));
        }
      }
    });
  });

  describe('Strict Mathematical Formula Invariance Across Languages', () => {
    test('preserves core mathematical formulas unchanged across English, Hindi, and Hinglish in Ohm\'s Law scene', () => {
      const en = getCachedDescriptor('scene-5-ohms-law', 'english');
      const hi = getCachedDescriptor('scene-5-ohms-law', 'hindi');
      const hinglish = getCachedDescriptor('scene-5-ohms-law', 'hinglish');

      assert.ok(en && hi && hinglish);

      const requiredMathTokens = [
        'V = I * R',
        'I = V/R',
        '10V',
        '5Ω',
        '2A'
      ];

      for (const token of requiredMathTokens) {
        assert.ok(en.narration.includes(token), `English narration missing math token: ${token}`);
        assert.ok(hi.narration.includes(token), `Hindi narration missing math token: ${token}`);
        assert.ok(hinglish.narration.includes(token), `Hinglish narration missing math token: ${token}`);

        const enHasToken = en.captions.some(c => c.text.includes(token) || (c.mathFormulas && c.mathFormulas.some(m => m.includes(token))));
        const hiHasToken = hi.captions.some(c => c.text.includes(token) || (c.mathFormulas && c.mathFormulas.some(m => m.includes(token))));
        const hinglishHasToken = hinglish.captions.some(c => c.text.includes(token) || (c.mathFormulas && c.mathFormulas.some(m => m.includes(token))));

        assert.ok(enHasToken, `English captions missing math token: ${token}`);
        assert.ok(hiHasToken, `Hindi captions missing math token: ${token}`);
        assert.ok(hinglishHasToken, `Hinglish captions missing math token: ${token}`);
      }
    });

    test('preserves formulas (I = V/R, V = 10V, R, I) across all language variants of the repair scene', () => {
      const enRepair = getCachedDescriptor('scene-repair-ohms-law', 'english');
      const hiRepair = getCachedDescriptor('scene-repair-ohms-law', 'hindi');
      const hinglishRepair = getCachedDescriptor('scene-repair-ohms-law', 'hinglish');

      assert.ok(enRepair && hiRepair && hinglishRepair);

      const repairMathTokens = ['I = V/R', 'V = 10V'];

      for (const token of repairMathTokens) {
        assert.ok(enRepair.narration.includes(token), `English repair missing: ${token}`);
        assert.ok(hiRepair.narration.includes(token), `Hindi repair missing: ${token}`);
        assert.ok(hinglishRepair.narration.includes(token), `Hinglish repair missing: ${token}`);
      }
    });

    test('maintains identical visual data structures across languages for all cached demo scenes', () => {
      const demoScenes = [
        'scene-1-intro',
        'scene-2-voltage',
        'scene-3-resistance',
        'scene-5-ohms-law',
        'scene-advance-circuits',
        'scene-repair-ohms-law'
      ];

      for (const sId of demoScenes) {
        const en = getCachedDescriptor(sId, 'english');
        const hi = getCachedDescriptor(sId, 'hindi');
        const hinglish = getCachedDescriptor(sId, 'hinglish');

        assert.equal(en.visualCanvas.type, hi.visualCanvas.type);
        assert.equal(en.visualCanvas.type, hinglish.visualCanvas.type);

        // Visual specifications are identical across language variants
        assert.deepEqual(en.visualCanvas.data, hi.visualCanvas.data);
        assert.deepEqual(en.visualCanvas.data, hinglish.visualCanvas.data);
      }
    });
  });

  describe('3-in-1 Composite Repair Scene Across All Languages', () => {
    test('repair scene contains equation, analogy, and graph panels in all languages', () => {
      for (const lang of languages) {
        const repair = getCachedDescriptor('scene-repair-ohms-law', lang);
        assert.ok(repair, `Missing repair scene for ${lang}`);
        assert.equal(repair.visualCanvas.type, 'diagram');
        assert.equal(repair.visualCanvas.renderHint, 'composite_repair');

        const vData = repair.visualCanvas.data;
        assert.ok(vData.composite);
        assert.equal(vData.diagramType, 'compound_repair');

        // 1. Equation panel
        assert.ok(vData.equation);
        assert.ok(Array.isArray(vData.equation.steps));
        assert.equal(vData.equation.steps[0].latex, "V = I \\cdot R");
        assert.equal(vData.equation.steps[1].latex, "I = \\frac{V}{R}");

        // 2. Analogy panel
        assert.ok(vData.analogy);
        assert.equal(vData.analogy.diagramType, 'hydraulic_analogy');
        assert.ok(Array.isArray(vData.analogy.elements));
        const pipe = vData.analogy.elements.find(e => e.id === 'pipe_constriction');
        assert.ok(pipe);
        assert.equal(pipe.formulaSymbol, 'R');

        // 3. Graph panel
        assert.ok(vData.graph);
        assert.equal(vData.graph.graphType, 'inverse_proportionality');
        assert.equal(vData.graph.formula, 'I = 10 / R');
        assert.ok(Array.isArray(vData.graph.series));
        assert.ok(vData.graph.series[0].points.length > 0);
      }
    });
  });
});
