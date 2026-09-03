const { test, describe } = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const {
  validateData,
  validateAgainstSchema,
  validateFixture,
  inferType,
  getSchema,
  getDefinitions
} = require('../validate');

describe('contracts schema and validator suite', () => {
  describe('schema and definitions', () => {
    test('loads schema with Draft-07 specification and valid definitions', () => {
      const schema = getSchema();
      assert.ok(schema);
      assert.equal(schema.title, 'GuruFlow lesson contract');
      assert.ok(schema.definitions || schema.$defs);

      const defs = getDefinitions();
      assert.ok(defs.LearnerProfile);
      assert.ok(defs.SourceCitation);
      assert.ok(defs.VisualSpec);
      assert.ok(defs.Scene);
      assert.ok(defs.LessonPlan);
      assert.ok(defs.EvaluationResult);
      assert.ok(defs.LearningReport);
      assert.ok(defs.CheckpointSubmission);
    });
  });

  describe('type inference', () => {
    test('correctly infers LessonPlan type', () => {
      const plan = {
        id: 'plan-1',
        learner: { level: 'beginner', language: 'english', availableMinutes: 15, goal: 'learn' },
        scenes: []
      };
      assert.equal(inferType(plan), 'LessonPlan');
    });

    test('correctly infers Scene type', () => {
      const scene = {
        id: 'scene-1',
        conceptId: 'c1',
        objective: 'obj',
        narration: 'narr',
        visual: { type: 'equation', data: {} }
      };
      assert.equal(inferType(scene), 'Scene');
    });

    test('correctly infers EvaluationResult type', () => {
      const evalRes = {
        correct: true,
        mastery: 0.8,
        feedback: 'Good job',
        nextAction: 'advance'
      };
      assert.equal(inferType(evalRes), 'EvaluationResult');
    });

    test('correctly infers LearningReport type', () => {
      const report = {
        studentId: 's1',
        lessonId: 'l1',
        score: 0.9,
        strongConcepts: ['v', 'i']
      };
      assert.equal(inferType(report), 'LearningReport');
    });

    test('correctly infers CheckpointSubmission type', () => {
      const sub = {
        checkpointId: 'cp-1',
        studentAnswer: 'current drops'
      };
      assert.equal(inferType(sub), 'CheckpointSubmission');
    });

    test('returns null for unknown objects', () => {
      assert.equal(inferType({ foo: 'bar' }), null);
      assert.equal(inferType(null), null);
      assert.equal(inferType([1, 2, 3]), null);
    });
  });

  describe('LearnerProfile validation', () => {
    test('validates a compliant learner profile', () => {
      const profile = {
        level: 'beginner',
        language: 'hinglish',
        availableMinutes: 25,
        goal: "Master Ohm's Law",
        priorKnowledge: 'Basic arithmetic'
      };
      const result = validateData(profile, 'LearnerProfile');
      assert.equal(result.valid, true);
      assert.equal(result.errors.length, 0);
    });

    test('rejects invalid language enum', () => {
      const profile = {
        level: 'beginner',
        language: 'spanish',
        availableMinutes: 20,
        goal: 'test'
      };
      const result = validateData(profile, 'LearnerProfile');
      assert.equal(result.valid, false);
      assert.ok(result.errors.some(e => e.includes('language')));
    });

    test('rejects invalid level enum', () => {
      const profile = {
        level: 'master',
        language: 'english',
        availableMinutes: 20,
        goal: 'test'
      };
      const result = validateData(profile, 'LearnerProfile');
      assert.equal(result.valid, false);
      assert.ok(result.errors.some(e => e.includes('level')));
    });

    test('rejects availableMinutes out of bounds (< 1 or > 10080)', () => {
      const zeroMin = { level: 'beginner', language: 'english', availableMinutes: 0, goal: 'test' };
      assert.equal(validateData(zeroMin, 'LearnerProfile').valid, false);

      const excessMin = { level: 'beginner', language: 'english', availableMinutes: 20000, goal: 'test' };
      assert.equal(validateData(excessMin, 'LearnerProfile').valid, false);
    });

    test('rejects empty goal string (minLength: 1)', () => {
      const emptyGoal = { level: 'beginner', language: 'english', availableMinutes: 10, goal: '' };
      assert.equal(validateData(emptyGoal, 'LearnerProfile').valid, false);
    });
  });

  describe('SourceCitation validation', () => {
    test('validates compliant citation', () => {
      const citation = {
        documentId: 'ncert-class9-science-ch12',
        pageOrSlide: 204,
        heading: "12.3 Ohm's Law",
        excerpt: 'V is proportional to I'
      };
      const result = validateData(citation, 'SourceCitation');
      assert.equal(result.valid, true);
    });

    test('rejects citation with invalid pageOrSlide (< 1)', () => {
      const citation = {
        documentId: 'doc1',
        pageOrSlide: 0,
        excerpt: 'excerpt'
      };
      const result = validateData(citation, 'SourceCitation');
      assert.equal(result.valid, false);
      assert.ok(result.errors.some(e => e.includes('pageOrSlide')));
    });

    test('rejects missing required fields', () => {
      const citation = {
        pageOrSlide: 5
      };
      const result = validateData(citation, 'SourceCitation');
      assert.equal(result.valid, false);
      assert.ok(result.errors.some(e => e.includes('documentId')));
      assert.ok(result.errors.some(e => e.includes('excerpt')));
    });
  });

  describe('VisualSpec validation', () => {
    test('validates supported visual types', () => {
      const validTypes = ['circuit', 'equation', 'graph', 'timeline', 'diagram', 'code_trace', 'concept_map'];
      for (const t of validTypes) {
        const result = validateData({ type: t, data: { sample: 123 } }, 'VisualSpec');
        assert.equal(result.valid, true, `Expected valid for type: ${t}`);
      }
    });

    test('rejects unsupported visual type', () => {
      const result = validateData({ type: '3d_voxel', data: {} }, 'VisualSpec');
      assert.equal(result.valid, false);
      assert.ok(result.errors.some(e => e.includes('type')));
    });
  });

  describe('Scene validation', () => {
    test('validates compliant scene', () => {
      const scene = {
        id: 'scene-1',
        conceptId: 'ohms-law',
        objective: 'Teach V = IR',
        narration: 'Narration script text',
        visual: { type: 'equation', data: { steps: [] } },
        citations: [{ documentId: 'doc-1', pageOrSlide: 1, excerpt: 'Citation text' }],
        durationSeconds: 45,
        checkpointId: 'cp-1'
      };
      const result = validateData(scene, 'Scene');
      assert.equal(result.valid, true);
    });

    test('rejects durationSeconds < 1', () => {
      const scene = {
        id: 'scene-1',
        conceptId: 'c1',
        objective: 'obj',
        narration: 'text',
        visual: { type: 'circuit', data: {} },
        citations: [],
        durationSeconds: 0
      };
      const result = validateData(scene, 'Scene');
      assert.equal(result.valid, false);
      assert.ok(result.errors.some(e => e.includes('durationSeconds')));
    });
  });

  describe('LessonPlan validation', () => {
    test('rejects LessonPlan with 0 scenes (minItems: 1)', () => {
      const plan = {
        id: 'lesson-empty',
        learner: { level: 'beginner', language: 'english', availableMinutes: 10, goal: 'learn' },
        scenes: []
      };
      const result = validateData(plan, 'LessonPlan');
      assert.equal(result.valid, false);
      assert.ok(result.errors.some(e => e.includes('scenes')));
    });
  });

  describe('EvaluationResult validation', () => {
    test('validates compliant advance evaluation', () => {
      const evalRes = {
        correct: true,
        mastery: 0.85,
        feedback: 'Excellent work!',
        nextAction: 'advance'
      };
      const result = validateData(evalRes, 'EvaluationResult');
      assert.equal(result.valid, true);
    });

    test('validates compliant repair evaluation with repairScene', () => {
      const evalRes = {
        correct: false,
        mastery: 0.35,
        misconception: 'direct-proportionality confusion',
        feedback: 'Let us review the inverse relationship.',
        nextAction: 'repair',
        repairScene: {
          id: 'scene-repair',
          conceptId: 'ohms-law',
          objective: 'Remediate misconception',
          narration: 'Here is the water pipe analogy',
          visual: { type: 'diagram', data: {} },
          citations: [{ documentId: 'ncert', pageOrSlide: 205, excerpt: 'excerpt' }],
          durationSeconds: 35
        }
      };
      const result = validateData(evalRes, 'EvaluationResult');
      assert.equal(result.valid, true);
    });

    test('rejects mastery out of bounds (< 0 or > 1)', () => {
      const negMastery = { correct: true, mastery: -0.1, feedback: 'f', nextAction: 'advance' };
      assert.equal(validateData(negMastery, 'EvaluationResult').valid, false);

      const highMastery = { correct: true, mastery: 1.5, feedback: 'f', nextAction: 'advance' };
      assert.equal(validateData(highMastery, 'EvaluationResult').valid, false);
    });

    test('rejects invalid nextAction enum', () => {
      const invalidAction = { correct: true, mastery: 0.5, feedback: 'f', nextAction: 'skip_all' };
      assert.equal(validateData(invalidAction, 'EvaluationResult').valid, false);
    });
  });

  describe('LearningReport validation', () => {
    test('validates compliant learning report', () => {
      const report = {
        studentId: 'std-123',
        lessonId: 'lesson-ohms-law',
        score: 0.85,
        strongConcepts: ['voltage', 'current'],
        weakConcepts: ['resistance'],
        misconceptions: [
          { id: 'direct-proportionality-confusion', status: 'resolved', concept: 'ohms-law' }
        ],
        revisionActions: ['Practice formula inversion'],
        nextTopic: { id: 'series-parallel', title: 'Series and Parallel Circuits' },
        totalTimeSeconds: 900,
        scenesCompleted: 7,
        checkpointsPassed: 1,
        checkpointsFailed: 0
      };
      const result = validateData(report, 'LearningReport');
      assert.equal(result.valid, true);
    });
  });

  describe('CheckpointSubmission validation', () => {
    test('validates compliant checkpoint submission', () => {
      const sub = {
        lessonId: 'lesson-ohms-law',
        checkpointId: 'checkpoint-1',
        studentAnswer: 'Current decreases when resistance increases.',
        expectedEvaluation: {
          correct: true,
          mastery: 0.8,
          feedback: 'Correct!',
          nextAction: 'advance'
        }
      };
      const result = validateData(sub, 'CheckpointSubmission');
      assert.equal(result.valid, true);
    });
  });

  describe('Fixture disk validation', () => {
    const fixtureDir = path.resolve(__dirname, '../../../demo-fixtures');

    const fixtureFiles = [
      'ohms-law-beginner-hinglish.json',
      'ohms-law-repair-scene.json',
      'ohms-law-evaluation-wrong.json',
      'ohms-law-evaluation-correct.json',
      'ohms-law-evaluation-retry.json',
      'ohms-law-misconception.json',
      'ohms-law-report.json'
    ];

    for (const file of fixtureFiles) {
      test(`validates demo fixture file: ${file}`, () => {
        const fullPath = path.join(fixtureDir, file);
        const res = validateFixture(fullPath);
        assert.equal(res.valid, true, `Fixture ${file} failed validation: ${res.errors.join(', ')}`);
        assert.ok(res.type);
      });
    }
  });
});
