/**
 * GuruFlow classroom controller.
 *
 * Drives the full product loop:
 * Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate ->
 * Adapt -> Continue.
 *
 * The adaptive step is the important one: a diagnosed misconception splices a
 * *new* repair Scene into the lesson immediately after the checkpoint and
 * routes the learner back for a retry. The scene list the learner sees is not
 * the scene list the planner produced.
 */

import { GuruFlowClient } from './api.js';
import { MediaAdapter } from './media-adapter.js';
import { renderVisual } from './visuals.js';

const $ = (id) => document.getElementById(id);

const state = {
  client: new GuruFlowClient(),
  media: new MediaAdapter(),
  learner: null,
  material: null,
  plan: null,
  scenes: [],
  sceneIndex: 0,
  checkpointIndex: null,
  lastEvaluation: null,
  selectedOption: null,
  timer: null,
  elapsed: 0,
  voiceOn: false,
  uploadedFile: null,
};

const MCQ_OPTIONS = [
  { id: 'increases', label: 'The current increases' },
  { id: 'decreases', label: 'The current decreases' },
  { id: 'no-change', label: 'The current stays the same' },
];

const MISCONCEPTION_EXPLAIN = {
  'direct-proportionality confusion':
    'You linked resistance and current as if they rise together. In I = V/R they move in opposite directions when V is fixed.',
  'constant-current confusion':
    'You held the current fixed instead of the voltage. In this experiment V is the constant, so I has to change when R does.',
};

/* ------------------------------------------------------------------ *
 * Screen handling
 * ------------------------------------------------------------------ */

const SCREENS = ['landing', 'onboarding', 'plan', 'classroom', 'report', 'profile'];

function showScreen(name, opts = {}) {
  SCREENS.forEach((screen) => {
    $(`screen-${screen}`).hidden = screen !== name;
  });
  $('restart-btn').hidden = name === 'onboarding' || name === 'landing';
  document.querySelectorAll('.nav-link').forEach((link) => {
    link.classList.toggle('active', link.dataset.nav === name);
  });
  const smooth = opts.instant ? 'auto' : 'smooth';
  window.scrollTo({ top: 0, behavior: smooth });
}

function setModeBadge() {
  const badge = $('mode-badge');
  if (state.client.isGeminiLive) {
    badge.textContent = 'live Gemini brain';
    badge.className = 'badge badge-good';
    badge.title = 'Planning and evaluation run live on Gemini Flash';
  } else if (state.client.isLive) {
    badge.textContent = 'live API (add GEMINI_API_KEY)';
    badge.className = 'badge badge-warn';
    badge.title =
      'API connected, but no GEMINI_API_KEY set - using deterministic fallback. ' +
      'Set apps/api/.env GEMINI_API_KEY=... to enable live Gemini.';
  } else {
    badge.textContent = 'fixture mode';
    badge.className = 'badge badge-warn';
    badge.title = 'API unreachable - running from demo-fixtures/';
  }
}

/* ------------------------------------------------------------------ *
 * Onboarding -> analysis -> plan
 * ------------------------------------------------------------------ */

function readLearner() {
  const sliderEl = $('minutes-slider');
  const minutes = sliderEl ? Number(sliderEl.value) : Number($('minutes').value);
  return {
    level: $('level').value,
    language: $('language').value,
    availableMinutes: minutes > 0 ? minutes : 20,
    goal: $('goal').value.trim() || 'Understand the topic',
  };
}

function showDroppedFile(file) {
  const note = $('dropzone-note');
  if (!file || !note) return;
  note.hidden = false;
  const size = file.size > 1048576
    ? `${(file.size / 1048576).toFixed(1)} MB`
    : `${Math.round(file.size / 1024)} KB`;
  note.textContent = `Ready to teach from: ${file.name} (${size})`;
}

async function handleOnboarding(event) {
  event.preventDefault();
  const button = event.target.querySelector('button[type="submit"]');
  const error = $('onboarding-error');
  error.hidden = true;
  button.disabled = true;
  button.textContent = 'Analysing source...';

  try {
    const topic = $('topic').value.trim() || "Ohm's Law";
    const text = $('material-text').value.trim();
    const fileInput = $('material-file');
    const file = fileInput && fileInput.files && fileInput.files[0];

    state.learner = readLearner();

    // Handle file upload
    if (file) {
      state.material = await state.client.uploadFile(file);
    } else if (text) {
      state.material = await state.client.createMaterial({
        topic,
        text,
        title: 'Pasted material',
      });
    } else {
      state.material = await state.client.createMaterial({
        topic,
        text: undefined,
        title: undefined,
      });
    }

    state.plan = await state.client.createPlan({
      learner: state.learner,
      materialId: state.material.materialId,
      topic,
      studyMode: $('study-mode').value,
    });
    state.scenes = state.plan.scenes.map((scene) => ({ ...scene }));
    state.sceneIndex = 0;

    renderAnalysis();
    renderPlan();
    showScreen('plan');
  } catch (err) {
    error.textContent = `Could not plan the lesson: ${err.message}`;
    error.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = 'Analyse source & plan my lesson';
  }
}

function renderAnalysis() {
  const material = state.material;
  const grounded = state.scenes.some((s) => (s.citations || []).length > 0);
  const rows = [
    ['Document', material.title],
    ['Extraction', material.status === 'ready' ? 'Complete' : material.status],
    ['Sections found', String(material.sectionCount ?? '-')],
    ['Pages referenced', String(material.pageCount ?? '-')],
    ['Grounding', grounded ? 'Source-grounded' : 'General knowledge only'],
  ];

  const body = $('analysis-body');
  body.textContent = '';
  rows.forEach(([label, value]) => {
    const row = document.createElement('div');
    row.className = 'analysis-row';
    const left = document.createElement('span');
    left.textContent = label;
    const right = document.createElement('span');
    right.textContent = value;
    row.append(left, right);
    body.appendChild(row);
  });

  if (!grounded) {
    const warning = document.createElement('div');
    warning.className = 'evidence-empty';
    warning.style.marginTop = '14px';
    warning.textContent =
      'This topic is not covered by the loaded material. GuruFlow will teach it from general knowledge and will not attach citations.';
    body.appendChild(warning);
  }

  const sections = (material.sections || []).slice(0, 5);
  if (sections.length) {
    const list = document.createElement('ul');
    list.className = 'section-list';
    sections.forEach((section) => {
      const item = document.createElement('li');
      const tag = document.createElement('span');
      tag.className = 'page-tag';
      tag.textContent = `p.${section.pageOrSlide}`;
      item.append(tag, document.createTextNode(section.heading || section.excerpt.slice(0, 60)));
      list.appendChild(item);
    });
    body.appendChild(list);
  }
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins ? `${mins}m ${secs.toString().padStart(2, '0')}s` : `${secs}s`;
}

function modeLabel(mode) {
  return {
    lesson: 'Lesson mode',
    exam: 'Exam prep',
    revision: 'Quick revision',
  }[mode] || 'Lesson mode';
}

function renderPlan() {
  const plan = state.plan;
  const meta = $('plan-meta');
  meta.textContent = '';

  const chips = [
    { text: plan.learner.level, cls: 'badge-accent' },
    { text: plan.learner.language, cls: 'badge-accent' },
    {
      text: modeLabel(plan.studyMode),
      cls: plan.studyMode === 'lesson' ? 'badge-accent' : 'badge-good',
    },
    { text: `${plan.scenes.length} scenes`, cls: 'badge-muted' },
    {
      text: `${formatDuration(plan.estimatedSeconds || 0)} of ${plan.learner.availableMinutes}m budget`,
      cls: 'badge-muted',
    },
  ];
  chips.forEach(({ text, cls }) => {
    const chip = document.createElement('span');
    chip.className = `badge ${cls}`;
    chip.textContent = text;
    meta.appendChild(chip);
  });

  const timeline = $('plan-timeline');
  timeline.textContent = '';
  plan.scenes.forEach((scene, index) => {
    const item = document.createElement('li');
    if (scene.checkpointId) item.classList.add('is-checkpoint');

    const idx = document.createElement('span');
    idx.className = 'timeline-index';
    idx.textContent = scene.checkpointId ? '?' : String(index + 1);

    const body = document.createElement('div');
    body.className = 'timeline-body';
    const title = document.createElement('div');
    title.className = 'timeline-title';
    title.textContent = scene.objective;
    const sub = document.createElement('div');
    sub.className = 'timeline-sub';
    const cited = (scene.citations || []).length
      ? `p.${scene.citations.map((c) => c.pageOrSlide).join(', p.')}`
      : 'general knowledge';
    sub.textContent = `${scene.conceptId} - ${cited}`;
    body.append(title, sub);

    const dur = document.createElement('span');
    dur.className = 'timeline-dur';
    dur.textContent = formatDuration(scene.durationSeconds);

    item.append(idx, body, dur);
    timeline.appendChild(item);
  });
}

/* ------------------------------------------------------------------ *
 * Classroom
 * ------------------------------------------------------------------ */

function currentScene() {
  return state.scenes[state.sceneIndex];
}

function stopTimer() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
  state.media.tts.stop();
  $('avatar-mouth').classList.remove('speaking');
}

function startScene() {
  const scene = currentScene();
  stopTimer();
  state.elapsed = 0;

  renderClasspath();
  $('scene-objective').textContent = scene.objective;

  const grounded = (scene.citations || []).length > 0;
  const badge = $('grounding-badge');
  badge.textContent = grounded ? 'source-grounded' : 'general knowledge';
  badge.className = `badge ${grounded ? 'badge-good' : 'badge-warn'}`;

  renderVisual($('visual-canvas'), scene.visual);
  updateProgress();

  // Render the scene through services/media, then drive captions from it.
  state.media.render(scene, state.plan.learner.language).then((mediaResult) => {
    state.lastMediaResult = mediaResult;
    const status = $('media-status');
    if (mediaResult.status === 'degraded') {
      status.textContent = 'degraded - captions only';
      status.className = 'badge badge-warn';
    } else if (mediaResult.teacherPanel?.type === 'video') {
      status.textContent = 'avatar video';
      status.className = 'badge badge-good';
    } else {
      status.textContent = state.voiceOn ? 'voice + fallback panel' : 'fallback panel';
      status.className = 'badge badge-muted';
    }
    runCaptions(scene, mediaResult.captions || []);
  });

  const isCheckpoint = Boolean(scene.checkpointId);
  $('checkpoint-panel').hidden = !isCheckpoint;
  $('feedback-panel').hidden = true;
  $('next-scene').hidden = isCheckpoint;
  $('prev-scene').disabled = state.sceneIndex === 0;

  if (isCheckpoint) {
    state.checkpointIndex = state.sceneIndex;
    prepareCheckpoint(scene);
  } else {
    $('next-scene').textContent =
      state.sceneIndex === state.scenes.length - 1 ? 'Finish & see my report' : 'Next';
  }

  // A repair scene routes back to the question rather than forward.
  if (scene.isRepair) {
    $('next-scene').hidden = false;
    $('next-scene').textContent = 'Try the question again';
  }

  // Play the scene-transition entrance animation (re-trigger by swap).
  const stage = $('classroom-stage');
  if (stage) {
    stage.classList.remove('scene-enter');
    // Force reflow so the animation reliably restarts between scenes.
    void stage.offsetWidth;
    stage.classList.add('scene-enter');
  }

  state.client.completeScene(state.plan.id, scene.id).catch(() => {});
}

function runCaptions(scene, captions) {
  const box = $('captions');
  const mouth = $('avatar-mouth');
  const teacherVisual = $('teacher-visual');
  box.textContent = scene.narration;

  // Check if media result has a video URL from an avatar provider
  const mediaResult = state.lastMediaResult;
  if (mediaResult && mediaResult.teacherPanel && mediaResult.teacherPanel.type === 'video' && mediaResult.teacherPanel.url) {
    // Show avatar video
    teacherVisual.innerHTML = '';
    const video = document.createElement('video');
    video.src = mediaResult.teacherPanel.url;
    video.autoplay = true;
    video.muted = false;
    video.loop = false;
    video.style.width = '100%';
    video.style.height = '100%';
    video.style.objectFit = 'cover';
    video.style.borderRadius = 'var(--radius-sm)';
    teacherVisual.appendChild(video);
    mouth.classList.add('speaking');
  } else {
    mouth.classList.add('speaking');
  }

  if (state.voiceOn) {
    state.media.tts.speak(scene.narration, state.plan.learner.language, {
      onStart: () => mouth.classList.add('speaking'),
      onEnd: () => mouth.classList.remove('speaking'),
    });
  }

  const duration = scene.durationSeconds || 20;

  // Karaoke mode: for the active caption, highlight words as they are spoken.
  let karaokeWords = null;
  state.timer = setInterval(() => {
    state.elapsed += 0.25;
    $('scene-clock').textContent = `${Math.min(Math.ceil(state.elapsed), duration)}s / ${duration}s`;

    if (captions.length) {
      const active = captions.find(
        (caption) => state.elapsed >= caption.startTime && state.elapsed < caption.endTime
      );
      if (active) {
        const token = captionToWords(active.text);
        if (token !== karaokeWords) {
          karaokeWords = token;
          renderKaraoke(box, active.text, 0, token);
        }
        if (token) {
          const wordCount = token.length;
          const wordDur = (active.endTime - active.startTime) / wordCount || 0.15;
          const wordIndex = Math.floor((state.elapsed - active.startTime) / wordDur);
          renderKaraoke(box, active.text, wordIndex, token);
        }
      }
    }

    if (state.elapsed >= duration) {
      stopTimer();
      $('scene-clock').textContent = `${duration}s / ${duration}s`;
      box.textContent = scene.narration;
    }
  }, 250);
}

/** Split narration into word tokens, treating maths like "V = I x R" as one unit. */
function captionToWords(text) {
  const match = text.match(/\b[\w’\']+|\b[VvIRr]\s*[=×÷·]\s*[VvIRr]\b|[=×÷·]+|\bΩ\b/gi);
  return match || [];
}

/** Render a caption with an index of "spoken so far" words highlighted. */
function renderKaraoke(box, text, spokenUpTo, tokens) {
  if (tokens && tokens.length && tokens.length < 120) {
    let seen = 0;
    const node = document.createElement('div');
    node.className = 'caption-karaoke';
    text.replace(/\b[\w’\']+|\b[VvIRr]\s*[=×÷·]\s*[VvIRr]\b|[=×÷·]+|\bΩ\b/gi, (tok) => {
      const span = document.createElement('span');
      span.className = seen < spokenUpTo ? 'is-spoken' : '';
      span.textContent = tok;
      seen += 1;
      node.appendChild(span);
      node.appendChild(document.createTextNode(' '));
      return tok;
    });
    box.textContent = '';
    box.appendChild(node);
  } else {
    box.textContent = text;
  }
}

function updateProgress() {
  const total = state.scenes.length;
  const done = state.sceneIndex + 1;
  $('progress-fill').style.width = `${(done / total) * 100}%`;
  $('progress-label').textContent = `Scene ${done} / ${total}`;
}

/** Render the interactive lesson-path rail and keep it in sync with the current scene. */
function renderClasspath() {
  const list = $('classpath-list');
  const counter = $('classpath-progress');
  if (!list) return;
  list.textContent = '';
  const total = state.scenes.length;
  const done = state.sceneIndex + 1;
  if (counter) counter.textContent = `${done} / ${total}`;

  state.scenes.forEach((scene, index) => {
    const item = document.createElement('li');
    item.className = 'classpath-item';
    item.dataset.scene = String(index);
    if (scene.checkpointId) item.classList.add('checkpoint');
    if (index === state.sceneIndex) item.classList.add('active');
    else if (index < state.sceneIndex) item.classList.add('done');

    const node = document.createElement('span');
    node.className = 'classpath-node';
    node.textContent = scene.checkpointId ? '?' : String(index + 1);

    const label = document.createElement('span');
    label.className = 'classpath-label';
    label.textContent = scene.checkpointId ? 'Checkpoint question' : (scene.objective || scene.conceptId || `Scene ${index + 1}`);

    item.append(node, label);
    item.addEventListener('click', () => {
      if (index <= state.sceneIndex) goToScene(index);
    });
    list.appendChild(item);
  });
}

function prepareCheckpoint(scene) {
  $('checkpoint-question').textContent = scene.narration;
  state.selectedOption = null;
  $('answer-input').value = '';

  const wrap = $('mcq-options');
  wrap.textContent = '';
  MCQ_OPTIONS.forEach((option) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'mcq-option';
    button.textContent = option.label;
    button.addEventListener('click', () => {
      state.selectedOption = option.id;
      wrap.querySelectorAll('.mcq-option').forEach((node) => node.classList.remove('is-selected'));
      button.classList.add('is-selected');
    });
    wrap.appendChild(button);
  });
}

/* ------------------------------------------------------------------ *
 * Evaluation and adaptation
 * ------------------------------------------------------------------ */

async function submitAnswer() {
  const scene = currentScene();
  const button = $('submit-answer');
  button.disabled = true;
  button.textContent = 'Evaluating...';

  try {
    const result = await state.client.submitAnswer(state.plan.id, scene.checkpointId, {
      answer: $('answer-input').value.trim(),
      optionId: state.selectedOption,
      language: state.plan.learner.language,
    });
    state.lastEvaluation = result;
    showEvaluation(result);
  } catch (err) {
    $('captions').textContent = `Could not evaluate that answer: ${err.message}`;
  } finally {
    button.disabled = false;
    button.textContent = 'Submit';
  }
}

function showEvaluation(result) {
  stopTimer();
  $('checkpoint-panel').hidden = true;
  $('feedback-panel').hidden = false;
  // The verdict sits below the visual; bring it into view so the diagnosis is
  // never missed on a laptop screen.
  $('feedback-panel').scrollIntoView({ behavior: 'smooth', block: 'center' });

  const icon = $('feedback-icon');
  const title = $('feedback-title');
  const action = $('feedback-action');

  $('feedback-text').textContent = result.feedback;
  $('misconception-box').hidden = true;

  if (result.correct) {
    icon.textContent = '✓';
    icon.className = 'feedback-icon is-good';
    title.textContent = 'Correct';
    action.textContent = 'Continue the lesson';
    celebrate();
    // Step over any repair scene spliced in earlier, otherwise "continue"
    // would drop the learner back into the re-teach they have just passed.
    action.onclick = () => goToScene(firstTeachingSceneAfter(state.sceneIndex));
    return;
  }

  // Never "Wrong." -- a diagnosis plus a different explanation.
  icon.textContent = '↻';
  icon.className = 'feedback-icon is-repair';

  if (result.nextAction === 'retry') {
    title.textContent = "Let's try that once more";
    action.textContent = 'Try again';
    action.onclick = () => {
      $('feedback-panel').hidden = true;
      $('checkpoint-panel').hidden = false;
    };
    return;
  }

  title.textContent = 'Let me explain it a different way';
  if (result.misconception) {
    $('misconception-box').hidden = false;
    $('misconception-name').textContent = result.misconception;
    $('misconception-explain').textContent =
      MISCONCEPTION_EXPLAIN[result.misconception] || '';
  }

  action.textContent = 'Show me the correct idea';
  action.onclick = () => insertRepairScene(result.repairScene);
}

/** Fire a lightweight DOM confetti celebration (no dependencies). */
function celebrate() {
  const panel = $('feedback-panel');
  if (!panel || document.getElementById('confetti-layer')) return;
  const layer = document.createElement('div');
  layer.id = 'confetti-layer';
  layer.className = 'confetti-layer';
  panel.style.position = 'relative';
  panel.appendChild(layer);
  const colors = ['#3ecf8e', '#6c8cff', '#f5a524', '#ff6b9d', '#f8e16c'];
  for (let i = 0; i < 40; i += 1) {
    const piece = document.createElement('span');
    piece.className = 'confetti-piece';
    const size = 6 + Math.random() * 8;
    piece.style.width = `${size}px`;
    piece.style.height = `${size * (Math.random() > 0.5 ? 0.6 : 1.4)}px`;
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.setProperty('--drift', `${(Math.random() * 260 - 130).toFixed(0)}px`);
    piece.style.setProperty('--fall-duration', `${(1.4 + Math.random() * 1.4).toFixed(2)}s`);
    layer.appendChild(piece);
  }
  setTimeout(() => {
    const existing = document.getElementById('confetti-layer');
    if (existing) existing.remove();
  }, 3600);
}

/**
 * Splice the repair Scene into the lesson right after the checkpoint.
 * This is the visible proof that the answer changed the lesson.
 */
function insertRepairScene(repairScene) {
  if (!repairScene) {
    goToScene(state.sceneIndex + 1);
    return;
  }
  const scene = { ...repairScene, isRepair: true };
  const alreadyThere = state.scenes.findIndex((s) => s.id === scene.id);
  if (alreadyThere !== -1) state.scenes.splice(alreadyThere, 1);

  state.scenes.splice(state.checkpointIndex + 1, 0, scene);
  goToScene(state.checkpointIndex + 1);
}

/** Index of the next scene that is part of the original lesson, not a repair. */
function firstTeachingSceneAfter(index) {
  let next = index + 1;
  while (next < state.scenes.length && state.scenes[next].isRepair) next += 1;
  return next;
}

function goToScene(index) {
  if (index >= state.scenes.length) {
    showReport();
    return;
  }
  state.sceneIndex = Math.max(0, index);
  startScene();
}

function handleNext() {
  const scene = currentScene();
  if (scene.isRepair) {
    // Back to the question for the retry.
    goToScene(state.checkpointIndex);
    return;
  }
  goToScene(state.sceneIndex + 1);
}

/* ------------------------------------------------------------------ *
 * Language switch (progress preserving)
 * ------------------------------------------------------------------ */

async function handleLanguageSwitch(event) {
  const language = event.target.value;
  const keptIndex = state.sceneIndex;
  const repairScenes = state.scenes.filter((s) => s.isRepair);

  try {
    const plan = await state.client.switchLanguage(state.plan.id, language);
    state.plan = plan;
    state.scenes = plan.scenes.map((s) => ({ ...s }));

    // Re-splice any repair scene so the learner does not lose it.
    repairScenes.forEach((repair) => {
      const checkpointAt = state.scenes.findIndex((s) => s.checkpointId);
      state.checkpointIndex = checkpointAt;
      state.scenes.splice(checkpointAt + 1, 0, repair);
    });

    state.sceneIndex = Math.min(keptIndex, state.scenes.length - 1);
    startScene();
  } catch (err) {
    $('captions').textContent = `Could not switch language: ${err.message}`;
  }
}

/* ------------------------------------------------------------------ *
 * Evidence drawer
 * ------------------------------------------------------------------ */

function openEvidence() {
  const scene = currentScene();
  const body = $('evidence-body');
  body.textContent = '';

  const citations = scene.citations || [];
  if (!citations.length) {
    const empty = document.createElement('div');
    empty.className = 'evidence-empty';
    empty.textContent =
      'This scene is not backed by the uploaded material. GuruFlow is teaching it from general knowledge and says so rather than inventing a citation.';
    body.appendChild(empty);
  } else {
    citations.forEach((citation) => {
      const item = document.createElement('div');
      item.className = 'evidence-item';

      const meta = document.createElement('div');
      meta.className = 'evidence-meta';
      meta.textContent = `${citation.documentId} - page ${citation.pageOrSlide}`;
      item.appendChild(meta);

      if (citation.heading) {
        const heading = document.createElement('div');
        heading.className = 'evidence-heading';
        heading.textContent = citation.heading;
        item.appendChild(heading);
      }

      const excerpt = document.createElement('p');
      excerpt.className = 'evidence-excerpt';
      excerpt.textContent = `"${citation.excerpt}"`;
      item.appendChild(excerpt);

      body.appendChild(item);
    });
  }

  $('evidence-drawer').hidden = false;
}

/* ------------------------------------------------------------------ *
 * Report
 * ------------------------------------------------------------------ */

/** Put a visible spinner into a container in place of plain loading text. */
function showLoading(container, message) {
  container.textContent = '';
  const shim = document.createElement('div');
  shim.className = 'loading-shim';
  const spinner = document.createElement('div');
  spinner.className = 'spinner';
  const label = document.createElement('span');
  label.textContent = message || 'Loading...';
  shim.append(spinner, label);
  container.appendChild(shim);
}

async function showReport() {
  stopTimer();
  showScreen('report');
  const body = $('report-body');
  showLoading(body, 'Building your report...');

  try {
    const report = await state.client.getReport(state.plan.id);
    body.textContent = '';

    const score = document.createElement('div');
    score.className = 'score-ring';
    const value = document.createElement('div');
    value.className = 'score-value';
    value.textContent = `${Math.round((report.score || 0) * 100)}%`;
    const caption = document.createElement('div');
    caption.className = 'score-caption';
    caption.textContent = `${report.scenesCompleted} scenes watched - ${report.checkpointsPassed} checkpoint passed, ${report.checkpointsFailed} needed a second look - ${formatDuration(report.totalTimeSeconds || 0)} spent`;
    score.append(value, caption);
    body.appendChild(score);

    body.appendChild(chipSection('Strong concepts', report.strongConcepts, 'is-strong'));
    body.appendChild(chipSection('Needs revision', report.weakConcepts, 'is-weak'));

    if (report.misconceptions?.length) {
      const section = document.createElement('div');
      section.className = 'report-section';
      const heading = document.createElement('h4');
      heading.textContent = 'Misconceptions';
      section.appendChild(heading);
      const row = document.createElement('div');
      row.className = 'chip-row';
      report.misconceptions.forEach((misconception) => {
        const chip = document.createElement('span');
        chip.className = `chip ${misconception.status === 'resolved' ? 'is-strong' : 'is-weak'}`;
        chip.textContent = `${misconception.id} - ${misconception.status}`;
        row.appendChild(chip);
      });
      section.appendChild(row);
      body.appendChild(section);
    }

    if (report.revisionActions?.length) {
      const section = document.createElement('div');
      section.className = 'report-section';
      const heading = document.createElement('h4');
      heading.textContent = 'What to do next';
      section.appendChild(heading);
      const list = document.createElement('ul');
      list.className = 'action-list';
      report.revisionActions.forEach((action) => {
        const item = document.createElement('li');
        item.textContent = action;
        list.appendChild(item);
      });
      section.appendChild(list);
      body.appendChild(section);
    }

    if (report.nextTopic) {
      const next = document.createElement('div');
      next.className = 'next-topic';
      const label = document.createElement('span');
      label.textContent = 'Recommended next topic';
      const title = document.createElement('strong');
      title.textContent = report.nextTopic.title;
      next.append(label, title);
      body.appendChild(next);
    }

    $('profile-btn').hidden = false;
  } catch (err) {
    body.textContent = `Could not load the report: ${err.message}`;
    $('profile-btn').hidden = true;
  }
}

/* ------------------------------------------------------------------ *
 * Learning profile dashboard
 * ------------------------------------------------------------------ */

function profileChip(label, value, cls) {
  const chip = document.createElement('div');
  chip.className = `profile-stat ${cls || ''}`;
  const l = document.createElement('span');
  l.className = 'profile-stat-label';
  l.textContent = label;
  const v = document.createElement('span');
  v.className = 'profile-stat-value';
  v.textContent = value != null ? value : '—';
  chip.append(l, v);
  return chip;
}

function profileTrendBar(label, value) {
  const row = document.createElement('div');
  row.className = 'trend-row';
  const name = document.createElement('span');
  name.className = 'trend-label';
  name.textContent = label;
  const track = document.createElement('div');
  track.className = 'trend-track';
  const fill = document.createElement('div');
  fill.className = 'trend-fill';
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  fill.style.width = `${pct}%`;
  fill.textContent = pct < 40 ? `revisit` : pct < 70 ? 'steady' : 'mastered';
  track.appendChild(fill);
  row.append(name, track);
  return row;
}

function profileList(mastery) {
  const wrap = document.createElement('div');
  wrap.className = 'trend-wrap';
  const entries = Object.entries(mastery || {}).sort((a, b) => a[1] - b[1]);
  if (!entries.length) {
    const none = document.createElement('p');
    none.className = 'hint';
    none.textContent = 'No mastery data yet. Complete a lesson to start tracking.';
    wrap.appendChild(none);
    return wrap;
  }
  entries.forEach(([concept, value]) => wrap.appendChild(profileTrendBar(concept, value)));
  return wrap;
}

function profileFlashcards(cards) {
  const wrap = document.createElement('div');
  wrap.className = 'flashcard-list';
  const list = (cards || []).slice(0, 6);
  if (!list.length) {
    const none = document.createElement('p');
    none.className = 'hint';
    none.textContent = 'No review cards yet.';
    wrap.appendChild(none);
    return wrap;
  }
  list.forEach((card) => {
    const item = document.createElement('details');
    item.className = 'flashcard';
    const summary = document.createElement('summary');
    summary.textContent = card.front;
    const back = document.createElement('p');
    back.textContent = card.back;
    item.append(summary, back);
    wrap.appendChild(item);
  });
  return wrap;
}

function elem(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function profileSection(title, child) {
  const section = document.createElement('div');
  section.className = 'report-section';
  section.appendChild(elem('h4', title));
  section.appendChild(child);
  return section;
}

async function showProfile() {
  stopTimer();
  showScreen('profile');
  const body = $('profile-body');
  showLoading(body, 'Loading your learning profile...');

  const studentId = (state.plan && state.plan.learner && state.plan.learner.studentId) || 'student-demo';

  try {
    const profile = await state.client.getProfile(studentId);
    if (!profile) {
      body.textContent = 'No long-term profile for this student yet. Take a lesson to start tracking.';
      return;
    }
    body.textContent = '';

    // Header stats
    const statsRow = document.createElement('div');
    statsRow.className = 'stats-row';
    const score = profile.avgScore != null ? `${Math.round(profile.avgScore * 100)}%` : '—';
    statsRow.append(
      profileChip('Lessons completed', profile.lessonsCompleted ?? (profile.lessons || []).length, 'is-strong'),
      profileChip('Average score', score, 'is-strong'),
      profileChip('Recurring misconceptions', (profile.recurringMisconceptions || []).length, 'is-weak'),
    );
    body.appendChild(statsRow);

    // Concept mastery trend
    if (profile.conceptMastery) {
      body.appendChild(profileSection('Concept mastery', profileList(profile.conceptMastery)));
    }

    // Weak concepts
    const weak = profile.weakConcepts || [];
    const strong = (profile.strongConcepts || []).filter((c) => !weak.includes(c));
    body.appendChild(profileSection('Needs revision', chipSection('', weak, 'is-weak')));
    body.appendChild(profileSection('Strong concepts', chipSection('', strong, 'is-strong')));

    // Recurring misconceptions
    if ((profile.recurringMisconceptions || []).length) {
      const list = document.createElement('ul');
      list.className = 'action-list';
      profile.recurringMisconceptions.forEach((id) => {
        list.appendChild(elem('li', id));
      });
      body.appendChild(profileSection('Patterns to watch', list));
    }

    // Review flashcards for weak concepts
    const flashTargets = weak.length ? weak : (profile.weakConcepts || []);
    const flash = await state.client.getFlashcards(state.plan ? state.plan.id : profile.lessonId, flashTargets);
    body.appendChild(profileSection('Review flashcards', profileFlashcards(flash.cards)));

    // Spaced, multi-day revision plan built from long-term memory.
    const study = await state.client.getStudyPlan(studentId);
    if (study) {
      const wrap = document.createElement('div');
      wrap.className = 'study-timeline';
      const total = elem('p', `Spaced revision: ${study.totalReviewMinutes} min across ${study.horizonDays} days`, 'hint');
      wrap.appendChild(total);
      (study.sessions || []).forEach((s) => {
        const day = document.createElement('div');
        day.className = 'study-day';
        const head = document.createElement('div');
        head.className = 'study-day-head';
        head.appendChild(elem('strong', `Day ${s.day}`));
        head.appendChild(elem('span', s.date, 'study-day-date'));
        const para = document.createElement('div');
        para.className = 'study-day-body';
        para.appendChild(elem('div', s.title));
        para.appendChild(elem('span', `${s.conceptIds.length} topics - ${s.sessionMinutes} min`, 'hint'));
        day.append(head, para);
        wrap.appendChild(day);
      });
      body.appendChild(profileSection('7-day revision plan', wrap));
    }

    // Lesson history
    if ((profile.lessons || []).length) {
      const list = document.createElement('ul');
      list.className = 'action-list';
      profile.lessons.slice(0, 8).reverse().forEach((lesson) => {
        const pct = Math.round((lesson.score || 0) * 100);
        list.appendChild(elem('li', `${lesson.topic} - ${pct}%${lesson.weekName ? ` (${lesson.weekName})` : ''}`));
      });
      body.appendChild(profileSection('Lesson history', list));
    }
  } catch (err) {
    body.textContent = `Could not load the profile: ${err.message}`;
  }
}

function chipSection(heading, items, cls) {
  const section = document.createElement('div');
  section.className = 'report-section';
  const title = document.createElement('h4');
  title.textContent = heading;
  section.appendChild(title);

  const row = document.createElement('div');
  row.className = 'chip-row';
  if (!items || !items.length) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = 'None';
    row.appendChild(chip);
  } else {
    items.forEach((item) => {
      const chip = document.createElement('span');
      chip.className = `chip ${cls}`;
      chip.textContent = item;
      row.appendChild(chip);
    });
  }
  section.appendChild(row);
  return section;
}

/* ------------------------------------------------------------------ *
 * Wiring
 * ------------------------------------------------------------------ */

function restart() {
  stopTimer();
  state.client = new GuruFlowClient();
  state.client.mode = state.client.mode;
  state.plan = null;
  state.scenes = [];
  state.sceneIndex = 0;
  state.checkpointIndex = null;
  showScreen('landing');
  state.client.detectMode().then(setModeBadge);
}

function goHome() {
  showScreen('landing');
  state.client.detectMode().then(setModeBadge);
}

function goOnboarding() {
  syncControlUI();
  showScreen('onboarding');
}

/** Push the current control values into every mirrored input so the visible
 *  segmented/slider UI always matches the hidden selects the logic reads. */
function syncControlUI() {
  const pairs = [['level', 'level'], ['language', 'language'], ['study-mode', 'study-mode']];
  pairs.forEach(([segKey]) => {
    const select = $(segKey);
    select.value = select.value;
  });
  syncRadiosToSelects();
  syncSliderLabel();
}

/** Copy checked segmented radio values into the hidden selects. */
function syncRadiosToSelects() {
  const map = { level: 'level', language: 'language', 'study-mode': 'study-mode' };
  Object.entries(map).forEach(([radioName, selectId]) => {
    const checked = document.querySelector(`input[name="${radioName}"]:checked`);
    if (checked) $(selectId).value = checked.value;
  });
  syncSliderLabel();
}

/** Reflect the time slider into the hidden minutes select + label. */
const MINUTE_PRESETS = [5, 10, 20, 60];
function nearestMinutePreset(value) {
  let best = 20;
  let bestDiff = Infinity;
  MINUTE_PRESETS.forEach((p) => {
    const diff = Math.abs(p - value);
    if (diff < bestDiff) { bestDiff = diff; best = p; }
  });
  return best;
}
function syncSliderLabel() {
  const slider = $('minutes-slider');
  const minutesSelect = $('minutes');
  if (!slider) return;
  const value = Number(slider.value) || 20;
  const preset = nearestMinutePreset(value);
  if (minutesSelect) minutesSelect.value = String(preset);
  const label = $('minutes-label');
  if (label) label.textContent = `${value} min`;
}

function loadDemoPreset() {
  $('topic').value = "Ohm's Law";
  $('material-text').value = '';
  setRadio('level', 'beginner');
  setRadio('language', 'hinglish');
  $('minutes-slider').value = '20';
  setRadio('study-mode', 'lesson');
  $('goal').value = "Understand Ohm's Law";
  syncControlUI();
  $('onboarding-form').requestSubmit();
}

/** Check the segmented radio that matches a value for a given radio group. */
function setRadio(groupName, value) {
  const radio = document.querySelector(`input[name="${groupName}"][value="${value}"]`);
  if (radio) radio.checked = true;
}

function init() {
  syncControlUI();
  showScreen('landing', { instant: true });

  // Landing + navigation.
  $('landing-start').addEventListener('click', goOnboarding);
  $('landing-cta-start').addEventListener('click', goOnboarding);
  $('landing-closing-start').addEventListener('click', goOnboarding);
  $('landing-cta-how').addEventListener('click', () => {
    showScreen('landing');
    const section = $('landing-features');
    if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  $('home-link').addEventListener('click', goHome);
  $('home-link').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goHome(); }
  });
  document.querySelectorAll('[data-nav]').forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const target = link.dataset.nav;
      if (target === 'landing-features') {
        showScreen('landing');
        const section = $('landing-features');
        if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        showScreen(target, { instant: true });
      }
    });
  });

  // Onboarding control sync.
  ['level', 'language', 'study-mode'].forEach((name) => {
    const inputs = document.querySelectorAll(`input[name="${name}"]`);
    inputs.forEach((input) => input.addEventListener('change', syncRadiosToSelects));
  });
  const slider = $('minutes-slider');
  if (slider) slider.addEventListener('input', syncSliderLabel);

  // Drag-and-drop upload.
  const dropzone = $('dropzone');
  const fileInput = $('material-file');
  if (dropzone && fileInput) {
    ['dragenter', 'dragover'].forEach((evt) =>
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      }));
    ['dragleave', 'drop'].forEach((evt) =>
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
      }));
    dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        showDroppedFile(e.dataTransfer.files[0]);
      }
    });
    fileInput.addEventListener('change', () => {
      showDroppedFile(fileInput.files && fileInput.files[0]);
    });
  }

  $('onboarding-form').addEventListener('submit', handleOnboarding);
  $('start-lesson').addEventListener('click', () => {
    showScreen('classroom');
    $('lang-switch').value = state.plan.learner.language;
    startScene();
  });

  $('next-scene').addEventListener('click', handleNext);
  $('prev-scene').addEventListener('click', () => goToScene(state.sceneIndex - 1));
  $('submit-answer').addEventListener('click', submitAnswer);
  $('answer-input').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') submitAnswer();
  });

  $('lang-switch').addEventListener('change', handleLanguageSwitch);
  $('evidence-btn').addEventListener('click', openEvidence);
  $('evidence-close').addEventListener('click', () => {
    $('evidence-drawer').hidden = true;
  });

  $('voice-btn').addEventListener('click', () => {
    state.voiceOn = state.media.setVoiceEnabled(!state.voiceOn);
    const button = $('voice-btn');
    button.textContent = state.voiceOn ? 'Voice on' : 'Voice off';
    button.setAttribute('aria-pressed', String(state.voiceOn));
    if (!state.media.voiceAvailable) {
      button.textContent = 'Voice unavailable';
      button.disabled = true;
    }
  });

  $('demo-btn').addEventListener('click', loadDemoPreset);
  $('restart-btn').addEventListener('click', restart);
  $('report-restart').addEventListener('click', restart);
  $('profile-btn').addEventListener('click', showProfile);
  $('profile-back').addEventListener('click', () => showScreen('report'));

  state.client.detectMode().then(setModeBadge);
}

document.addEventListener('DOMContentLoaded', init);
