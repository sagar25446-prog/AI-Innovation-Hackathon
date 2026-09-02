import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  generateCaptions,
  translateCaptionLanguage,
  extractMathExpressions,
  formatTimingMarker,
  normalizeLanguageCode
} from '../src/caption-generator.js';

describe('caption-generator suite', () => {
  describe('generateCaptions', () => {
    test('splits narration into timed caption segments', () => {
      const narration = "Hello students! Today we will learn about Electric Current and Ohm's Law. This is the fundamental rule of electricity.";
      const captions = generateCaptions(narration, 'hinglish', 30);

      assert.ok(Array.isArray(captions));
      assert.equal(captions.length, 3);

      // Check first segment
      assert.equal(captions[0].index, 0);
      assert.equal(captions[0].language, 'hinglish');
      assert.equal(captions[0].startTime, 0);
      assert.ok(captions[0].endTime > captions[0].startTime);
      assert.equal(captions[0].text, 'Hello students!');

      // Check monotonic timestamps
      for (let i = 0; i < captions.length; i++) {
        assert.ok(captions[i].startTime < captions[i].endTime);
        if (i > 0) {
          assert.equal(captions[i].startTime, captions[i - 1].endTime);
        }
      }

      // Check final timestamp matches duration
      assert.equal(captions[captions.length - 1].endTime, 30);
    });

    test('does not break sentences on decimal numbers or formulas', () => {
      const narration = 'When V is 10.0V and R is 2.5Ω, current I = 4.0A. That is the answer.';
      const captions = generateCaptions(narration, 'english', 20);

      // Should split on actual sentence period, not on 10.0, 2.5, or 4.0
      assert.equal(captions.length, 2);
      assert.ok(captions[0].text.includes('10.0V'));
      assert.ok(captions[0].text.includes('2.5Ω'));
      assert.ok(captions[0].text.includes('4.0A'));
      assert.equal(captions[1].text, 'That is the answer.');
    });

    test('handles edge cases (empty string, single sentence, null)', () => {
      assert.deepEqual(generateCaptions('', 'english', 10), []);
      assert.deepEqual(generateCaptions(null, 'english', 10), []);
      assert.deepEqual(generateCaptions('   ', 'english', 10), []);

      const single = generateCaptions('Single sentence without period', 'en', 15);
      assert.equal(single.length, 1);
      assert.equal(single[0].startTime, 0);
      assert.equal(single[0].endTime, 15);
    });
  });

  describe('translateCaptionLanguage and mathematical formula preservation', () => {
    test('translates Ohm\'s Law narration across English, Hindi, and Hinglish with strict formula preservation', () => {
      const hinglishNarration = "Ohm's Law kehta hai ki V = I × R. Iska matlab hai Voltage equals Current into Resistance. Agar I nikalna ho, toh I = V/R hota hai. Maan lo V 10 hai aur R 5, toh I hoga 2 Amperes.";
      const initialCaptions = generateCaptions(hinglishNarration, 'hinglish', 60);

      // Translate to English
      const enCaptions = translateCaptionLanguage(initialCaptions, 'english');
      assert.equal(enCaptions[0].language, 'english');

      // Translate to Hindi
      const hiCaptions = translateCaptionLanguage(initialCaptions, 'hindi');
      assert.equal(hiCaptions[0].language, 'hindi');

      // Verify mathematical formulas remain identical across all 3 language versions
      const allTexts = [
        initialCaptions.map(c => c.text).join(' '),
        enCaptions.map(c => c.text).join(' '),
        hiCaptions.map(c => c.text).join(' ')
      ];

      for (const text of allTexts) {
        assert.ok(text.includes('V = I × R'), `Text missing V = I × R: ${text}`);
        assert.ok(text.includes('I = V/R'), `Text missing I = V/R: ${text}`);
        assert.ok(text.includes('2 Amperes'), `Text missing 2 Amperes: ${text}`);
      }
    });

    test('preserves repair scene inverse formulas across languages', () => {
      const repairNarration = "Socho ek pipe mein paani beh raha hai. Agar pipe ko narrow kar do (matlab resistance badhao), toh paani ka flow (matlab current) KAM hoga, zyada nahi! Isi tarah, I = V/R mein, jab R badhta hai toh I GHATTA hai.";
      const initialCaptions = generateCaptions(repairNarration, 'hinglish', 30);

      const enCaptions = translateCaptionLanguage(initialCaptions, 'english');
      const hiCaptions = translateCaptionLanguage(initialCaptions, 'hindi');

      const enText = enCaptions.map(c => c.text).join(' ');
      const hiText = hiCaptions.map(c => c.text).join(' ');

      assert.ok(enText.includes('I = V/R'));
      assert.ok(hiText.includes('I = V/R'));
    });

    test('preserves inline equations in arbitrary sentences', () => {
      const customCaptions = [
        { text: 'Calculate current using I = V/R where V = 10V and R = 5Ω gives I = 2A.', language: 'english' }
      ];

      const hiCaptions = translateCaptionLanguage(customCaptions, 'hindi');
      assert.ok(hiCaptions[0].text.includes('I = V/R'));
      assert.ok(hiCaptions[0].text.includes('V = 10V'));
      assert.ok(hiCaptions[0].text.includes('R = 5Ω'));
      assert.ok(hiCaptions[0].text.includes('I = 2A'));
    });
  });

  describe('helper utilities', () => {
    test('extractMathExpressions extracts mathematical symbols and expressions', () => {
      const text = 'Using V = IR, with V = 10V and R = 5Ω, we find I = V/R = 2A.';
      const matches = extractMathExpressions(text);
      assert.ok(matches.length > 0);
      assert.ok(matches.some(m => m.includes('V = IR')));
      assert.ok(matches.some(m => m.includes('10V')));
      assert.ok(matches.some(m => m.includes('5Ω')));
      assert.ok(matches.some(m => m.includes('2A')));
    });

    test('formatTimingMarker formats timestamps properly', () => {
      assert.equal(formatTimingMarker(0), '00:00.000');
      assert.equal(formatTimingMarker(12.345), '00:12.345');
      assert.equal(formatTimingMarker(75.5), '01:15.500');
    });

    test('normalizeLanguageCode standardizes language inputs', () => {
      assert.equal(normalizeLanguageCode('en'), 'english');
      assert.equal(normalizeLanguageCode('EN'), 'english');
      assert.equal(normalizeLanguageCode('English'), 'english');
      assert.equal(normalizeLanguageCode('hi'), 'hindi');
      assert.equal(normalizeLanguageCode('Hindi'), 'hindi');
      assert.equal(normalizeLanguageCode('hinglish'), 'hinglish');
      assert.equal(normalizeLanguageCode('HI-LATN'), 'hinglish');
    });
  });
});
