/**
 * API client with a fixture-backed fallback.
 *
 * If the teacher-brain API is unreachable the client transparently switches to
 * `demo-fixtures/`, so the judge-visible flow still completes end to end. The
 * UI reads `client.mode` to say honestly which source it is using.
 */

const API_BASE = '';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${detail.slice(0, 160)}`);
  }
  return response.json();
}

async function loadFixture(name) {
  const response = await fetch(`/fixtures/${name}`);
  if (!response.ok) throw new Error(`Fixture ${name} unavailable`);
  return response.json();
}

/** Local classifier used only in fixture mode. Mirrors the server's rules. */
function classifyLocally(answer, optionId) {
  if (optionId === 'decreases') return 'correct';
  if (optionId === 'increases') return 'direct-proportionality';
  if (optionId === 'no-change') return 'constant-current';

  const text = (answer || '').toLowerCase();
  if (!text.trim()) return 'unclear';
  // Strip the premise clause so "resistance badhne se current kam" reads as a
  // decrease, matching services/evaluation/misconceptions.py.
  const claim = text
    .replace(/resistance\s+(is\s+)?(increase[sd]?|badh\w*|doubl\w+)/g, ' ')
    .replace(/resistance\s+badhne\s+se/g, ' ');

  const down = /(decreas|less|lower|reduc|halv|half|fall|drop|inverse|kam|ghat|कम|घट)/.test(claim);
  const up = /(increas|more|higher|rise|grow|double|badh|zyada|अधिक|बढ़)/.test(claim);
  if (down && !up) return 'correct';
  if (up && !down) return 'direct-proportionality';
  if (/(same|unchanged|constant|no change)/.test(claim)) return 'constant-current';
  return 'unclear';
}

export class GuruFlowClient {
  constructor() {
    this.mode = 'unknown';
    this.attempts = {};
    this.fixturePlan = null;
    this.progress = { scenes: new Set(), passed: 0, failed: 0, misconception: null };
  }

  async detectMode() {
    try {
      const health = await request('/health');
      this.mode = health.status === 'ok' ? 'api' : 'fixture';
      this.gemini = Boolean(health && health.gemini);
    } catch {
      this.mode = 'fixture';
      this.gemini = false;
    }
    return this.mode;
  }

  get isLive() {
    return this.mode === 'api';
  }

  get isGeminiLive() {
    return this.isLive && this.gemini;
  }

  /* --------------------------------------------------------------- */

  async createMaterial({ topic, text, title }) {
    if (this.isLive) {
      return request('/materials', {
        method: 'POST',
        body: JSON.stringify({ topic, text, title }),
      });
    }
    return {
      materialId: 'material-ncert-class9-science-ch12',
      documentId: 'ncert-class9-science-ch12',
      title: 'NCERT Class 9 Science - Chapter 12: Electricity (fixture)',
      status: 'ready',
      origin: 'fixture',
      sectionCount: 7,
      pageCount: 6,
      sections: [],
    };
  }

  async uploadFile(file) {
    if (this.isLive) {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Upload failed: ${response.status} ${detail.slice(0, 160)}`);
      }
      return response.json();
    }
    // Fixture fallback for demo mode
    return {
      materialId: 'material-ncert-class9-science-ch12',
      documentId: 'ncert-class9-science-ch12',
      title: 'NCERT Class 9 Science - Chapter 12: Electricity (fixture)',
      status: 'ready',
      origin: 'fixture',
      sectionCount: 7,
      pageCount: 6,
      sections: [],
    };
  }

  async createPlan({ learner, materialId, topic, studyMode = 'lesson' }) {
    if (this.isLive) {
      return request('/lessons/plan', {
        method: 'POST',
        body: JSON.stringify({ learner, materialId, topic, studentId: 'student-demo', studyMode }),
      });
    }
    const plan = await loadFixture('ohms-law-beginner-hinglish.json');
    plan.topic = topic;
    plan.studyMode = studyMode;
    plan.tier = studyMode === 'exam' ? 'exam-drill' : 'fixture';
    plan.estimatedSeconds = plan.scenes.reduce((sum, s) => sum + s.durationSeconds, 0);
    plan.documentTitle = 'NCERT Class 9 Science - Chapter 12 (fixture)';
    this.fixturePlan = plan;
    return plan;
  }

  async getStudyPlan(studentId) {
    if (this.isLive) {
      try {
        return await request(`/students/${studentId}/study-plan`);
      } catch (err) {
        if (String(err.message).startsWith('404')) return null;
        throw err;
      }
    }
    // Fixture mode: a plausible 7-day spaced-revision schedule.
    const today = new Date().toISOString().slice(0, 10);
    const plus = (d) => {
      const t = new Date();
      t.setDate(t.getDate() + d);
      return t.toISOString().slice(0, 10);
    };
    return {
      studentId,
      strategy: 'spaced-repetition',
      horizonDays: 7,
      weakConcepts: this.progress.misconception ? ['ohms-law-application'] : [],
      strongConcepts: ['current', 'voltage', 'resistance', 'ohms-law'],
      sessions: [
        { day: 1, date: today, title: 'Relearn what you missed', conceptIds: ['ohms-law-application'], sessionMinutes: 5, mode: 'revision' },
        { day: 2, date: plus(1), title: 'Reinforce today', conceptIds: ['ohms-law', 'ohms-law-application'], sessionMinutes: 10, mode: 'revision' },
        { day: 4, date: plus(3), title: 'Bring back borderline ideas', conceptIds: ['resistance', 'ohms-law', 'ohms-law-application'], sessionMinutes: 15, mode: 'revision' },
        { day: 7, date: plus(6), title: 'Full mixed review', conceptIds: ['current', 'voltage', 'resistance', 'ohms-law', 'ohms-law-application', 'lesson-summary'], sessionMinutes: 30, mode: 'revision' },
      ],
      totalReviewMinutes: 60,
    };
  }

  async switchLanguage(lessonId, language) {
    if (this.isLive) {
      return request(`/lessons/${lessonId}/language`, {
        method: 'POST',
        body: JSON.stringify({ language }),
      });
    }
    // Fixtures exist in Hinglish only; keep the plan rather than fail.
    return this.fixturePlan;
  }

  async completeScene(lessonId, sceneId) {
    if (this.isLive) {
      return request(`/lessons/${lessonId}/scenes/${sceneId}/complete`, { method: 'POST' });
    }
    this.progress.scenes.add(sceneId);
    return { sceneId, scenesCompleted: this.progress.scenes.size };
  }

  async submitAnswer(lessonId, checkpointId, { answer, optionId, language }) {
    if (this.isLive) {
      return request(`/lessons/${lessonId}/checkpoints/${checkpointId}/answer`, {
        method: 'POST',
        body: JSON.stringify({ answer, optionId, language, studentId: 'student-demo' }),
      });
    }

    const key = checkpointId;
    this.attempts[key] = (this.attempts[key] || 0) + 1;
    const attempt = this.attempts[key];
    const classification = classifyLocally(answer, optionId);

    if (classification === 'correct') {
      this.progress.passed += 1;
      if (this.progress.misconception) this.progress.misconception.status = 'resolved';
      const fixture = await loadFixture(
        attempt > 1 ? 'ohms-law-evaluation-retry.json' : 'ohms-law-evaluation-correct.json'
      );
      return { ...fixture, attempt };
    }

    if (classification === 'unclear') {
      return {
        correct: false,
        mastery: 0.4,
        feedback: 'Ek baar aur try karo. Ek line mein: current badhega ya kam hoga?',
        nextAction: 'retry',
        attempt,
      };
    }

    this.progress.failed += 1;
    const fixture = await loadFixture('ohms-law-evaluation-wrong.json');
    this.progress.misconception = {
      id: fixture.misconception,
      status: 'open',
      concept: 'ohms-law',
    };
    return { ...fixture, attempt };
  }

  async getReport(lessonId) {
    if (this.isLive) {
      return request(`/lessons/${lessonId}/report`);
    }
    const report = await loadFixture('ohms-law-report.json');
    report.scenesCompleted = this.progress.scenes.size || report.scenesCompleted;
    report.checkpointsPassed = this.progress.passed;
    report.checkpointsFailed = this.progress.failed;
    if (this.progress.misconception) {
      report.misconceptions = [this.progress.misconception];
    }
    return report;
  }

  async getProfile(studentId) {
    if (this.isLive) {
      try {
        return await request(`/students/${studentId}/profile`);
      } catch (err) {
        if (String(err.message).startsWith('404')) return null;
        throw err;
      }
    }
    // Fixture mode: a small, sensible long-term profile built from this lesson.
    return {
      studentId,
      lessonsCompleted: 1,
      avgScore: this.progress.passed ? 0.9 : 0.5,
      weakConcepts: this.progress.misconception
        ? ['ohms-law-practice', 'ohms-law-application']
        : [],
      recurringMisconceptions: this.progress.misconception
        ? [this.progress.misconception.id]
        : [],
      misconceptions: this.progress.misconception
        ? [{ id: this.progress.misconception.id, status: 'open', count: 1 }]
        : [],
      lessons: [
        {
          lessonId: 'demo',
          topic: "Ohm's Law",
          score: this.progress.passed ? 0.9 : 0.5,
          weekName: 'This session',
        },
      ],
    };
  }

  async getFlashcards(lessonId, conceptIds) {
    if (this.isLive) {
      return request(`/lessons/${lessonId}/flashcards`, {
        method: 'POST',
        body: JSON.stringify({ conceptIds: conceptIds || undefined }),
      });
    }
    const cards = [
      { conceptId: 'electric-current', front: 'What is current?', back: 'The flow of electric charge, measured in amperes (A).' },
      { conceptId: 'voltage', front: 'What is voltage?', back: 'The electric push between two points that drives current.' },
      { conceptId: 'resistance', front: 'What is resistance?', back: 'It opposes current flow, measured in ohms (Ω).' },
      { conceptId: 'ohms-law', front: 'State Ohm\u2019s Law.', back: 'V = I × R. Voltage equals current times resistance.' },
    ];
    if (conceptIds) return { cards: cards.filter((c) => conceptIds.includes(c.conceptId)) };
    return { cards };
  }
}
