/**
 * Deterministic renderers for every Scene.visual.type in the contract.
 *
 * Backend-generated scenes and Person 3's demo fixtures describe the same
 * visuals with slightly different shapes (a fixture says
 * `components: ["battery", "wire"]`, the planner says
 * `components: [{type: "battery", label: "V = 10V"}]`). Every renderer below
 * normalises both, so one component set draws both sources.
 */

import { getRenderHint } from '/vendor/visuals/index.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

function el(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

function svgRoot(width, height) {
  const svg = el('svg', {
    viewBox: `0 0 ${width} ${height}`,
    width: '100%',
    role: 'img',
  });
  return svg;
}

/* ------------------------------------------------------------------ *
 * Shape normalisers
 * ------------------------------------------------------------------ */

function normaliseSteps(steps = []) {
  return steps.map((step) =>
    typeof step === 'string' ? { expression: step, label: '' } : step
  );
}

function normaliseComponents(components = []) {
  return components.map((component) =>
    typeof component === 'string'
      ? { type: component, label: component }
      : { type: component.type, label: component.label || component.type }
  );
}

function normaliseNodes(nodes = []) {
  return nodes.map((node, index) =>
    typeof node === 'string'
      ? { id: `n${index}`, label: node, type: node.includes('=') ? 'formula' : 'concept' }
      : node
  );
}

function axisLabel(axis, fallback) {
  if (!axis) return fallback;
  return typeof axis === 'string' ? axis : axis.label || fallback;
}

/** Pull points out of either the rich series shape or a bare points array. */
function normalisePoints(data) {
  if (Array.isArray(data.points) && data.points.length) return data.points;
  const series = data.series && data.series[0];
  if (series && Array.isArray(series.points) && series.points.length) return series.points;
  // Fixture graphs describe the axes but leave the curve implicit; derive the
  // canonical I = V/R curve at V = 10 so the shape is still truthful.
  return [1, 2, 4, 6, 10, 16, 20].map((x) => ({ x, y: 10 / x }));
}

/* ------------------------------------------------------------------ *
 * Renderers
 * ------------------------------------------------------------------ */

function renderCircuit(data) {
  const components = normaliseComponents(data.components);
  const highlight = data.highlight || '';
  const svg = svgRoot(420, 260);

  const wireColor = highlight === 'current-flow' ? '#6c8cff' : '#6b7488';
  const wireWidth = highlight === 'current-flow' ? 3.5 : 2;

  // Circuit loop.
  svg.appendChild(
    el('rect', {
      x: 60, y: 50, width: 300, height: 160,
      fill: 'none', stroke: wireColor, 'stroke-width': wireWidth, rx: 8,
    })
  );

  // Battery on the left rail.
  const batteryActive = highlight === 'battery';
  svg.appendChild(el('line', {
    x1: 60, y1: 110, x2: 60, y2: 150,
    stroke: batteryActive ? '#f5a524' : '#e8eaf0', 'stroke-width': batteryActive ? 7 : 5,
  }));
  svg.appendChild(el('line', {
    x1: 48, y1: 120, x2: 72, y2: 120,
    stroke: batteryActive ? '#f5a524' : '#e8eaf0', 'stroke-width': 3,
  }));
  const battery = components.find((c) => c.type === 'battery');
  svg.appendChild(el('text', {
    x: 14, y: 176, fill: batteryActive ? '#f5a524' : '#9aa3b8', 'font-size': 13,
  }, battery ? battery.label : 'Battery'));

  // Resistor or bulb on the right rail.
  const load = components.find((c) => c.type === 'resistor' || c.type === 'bulb') || { type: 'bulb', label: 'Bulb' };
  const loadActive = highlight === 'resistor' || highlight === 'bulb';
  const loadColor = loadActive ? '#f5a524' : '#e8eaf0';

  if (load.type === 'resistor') {
    svg.appendChild(el('path', {
      d: 'M360 100 l0 12 l-14 8 l28 12 l-28 12 l28 12 l-14 8 l0 12',
      fill: 'none', stroke: loadColor, 'stroke-width': loadActive ? 4 : 2.5,
    }));
  } else {
    svg.appendChild(el('circle', {
      cx: 360, cy: 130, r: 20,
      fill: loadActive ? 'rgba(245,165,36,0.2)' : 'none',
      stroke: loadColor, 'stroke-width': loadActive ? 4 : 2.5,
    }));
    svg.appendChild(el('path', {
      d: 'M348 118 L372 142 M372 118 L348 142',
      stroke: loadColor, 'stroke-width': 2,
    }));
  }
  // Sit the label clear of the symbol; the resistor is taller than the bulb.
  svg.appendChild(el('text', {
    x: 360,
    y: load.type === 'resistor' ? 196 : 172,
    fill: loadActive ? '#f5a524' : '#9aa3b8',
    'font-size': 13,
    'text-anchor': 'middle',
  }, load.label));

  // Animated current arrows when the scene is about current flow.
  if (highlight === 'current-flow') {
    for (let i = 0; i < 3; i += 1) {
      const marker = el('circle', { cx: 0, cy: 0, r: 5, fill: '#6c8cff' });
      const motion = el('animateMotion', {
        dur: '3s', repeatCount: 'indefinite', begin: `${i}s`,
        path: 'M60,50 L360,50 L360,210 L60,210 Z',
      });
      marker.appendChild(motion);
      svg.appendChild(marker);
    }
  }

  const annotations = data.annotations || [];
  if (annotations.length) {
    svg.appendChild(el('text', {
      x: 210, y: 240, fill: '#6b7488', 'font-size': 12, 'text-anchor': 'middle',
    }, String(annotations[0])));
  }

  return svg;
}

function renderEquation(data) {
  const wrap = document.createElement('div');
  wrap.className = 'eq-stack';

  const steps = normaliseSteps(data.steps);
  steps.forEach((step, index) => {
    const row = document.createElement('div');
    row.className = 'eq-step';
    if (data.highlight === 'result' && index === steps.length - 1) {
      row.classList.add('is-highlight');
    }
    const expr = document.createElement('span');
    expr.className = 'eq-expr';
    expr.textContent = step.expression;
    row.appendChild(expr);
    if (step.label) {
      const label = document.createElement('span');
      label.className = 'eq-label';
      label.textContent = step.label;
      row.appendChild(label);
    }
    wrap.appendChild(row);
  });

  // Repair scenes carry an analogy and a descending curve alongside the maths.
  if (data.analogy) {
    const chip = document.createElement('div');
    chip.className = 'analogy-chip';
    chip.textContent =
      data.analogy === 'water-pipe'
        ? 'Analogy: narrower pipe means slower flow'
        : `Analogy: ${data.analogy}`;
    wrap.appendChild(chip);
  }

  if (data.graph) {
    wrap.appendChild(
      renderGraph({
        xAxis: data.graph.xAxis,
        yAxis: data.graph.yAxis,
        points: data.graph.points,
        title: data.graph.caption || '',
      })
    );
  }

  return wrap;
}

function renderGraph(data) {
  const width = 420;
  const height = 260;
  const pad = { left: 52, right: 18, top: 30, bottom: 44 };
  const svg = svgRoot(width, height);

  const points = normalisePoints(data);
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const yMax = Math.max(...ys);

  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const sx = (x) => pad.left + ((x - xMin) / (xMax - xMin || 1)) * plotW;
  const sy = (y) => pad.top + plotH - (y / (yMax || 1)) * plotH;

  // Axes.
  svg.appendChild(el('line', {
    x1: pad.left, y1: pad.top, x2: pad.left, y2: pad.top + plotH,
    stroke: '#3a4152', 'stroke-width': 1.5,
  }));
  svg.appendChild(el('line', {
    x1: pad.left, y1: pad.top + plotH, x2: pad.left + plotW, y2: pad.top + plotH,
    stroke: '#3a4152', 'stroke-width': 1.5,
  }));

  // Curve.
  const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ');
  svg.appendChild(el('path', {
    d, fill: 'none', stroke: '#6c8cff', 'stroke-width': 3, 'stroke-linecap': 'round',
  }));

  points.forEach((p) => {
    svg.appendChild(el('circle', { cx: sx(p.x), cy: sy(p.y), r: 4, fill: '#6c8cff' }));
  });

  // Axis labels.
  svg.appendChild(el('text', {
    x: pad.left + plotW / 2, y: height - 10,
    fill: '#9aa3b8', 'font-size': 12, 'text-anchor': 'middle',
  }, axisLabel(data.xAxis, 'Resistance')));

  const yLabel = el('text', {
    x: 14, y: pad.top + plotH / 2,
    fill: '#9aa3b8', 'font-size': 12, 'text-anchor': 'middle',
    transform: `rotate(-90 14 ${pad.top + plotH / 2})`,
  }, axisLabel(data.yAxis, 'Current'));
  svg.appendChild(yLabel);

  if (data.title) {
    svg.appendChild(el('text', {
      x: width / 2, y: 18, fill: '#e8eaf0', 'font-size': 12, 'text-anchor': 'middle',
    }, data.title));
  }

  const annotation = (data.annotations || [])[0];
  if (annotation) {
    svg.appendChild(el('text', {
      x: pad.left + plotW, y: pad.top + 14,
      fill: '#f5a524', 'font-size': 11, 'text-anchor': 'end',
    }, typeof annotation === 'string' ? annotation : annotation.text));
  }

  return svg;
}

function renderConceptMap(data) {
  const nodes = normaliseNodes(data.nodes);
  const formulas = nodes.filter((n) => n.type === 'formula');
  const concepts = nodes.filter((n) => n.type !== 'formula');

  const width = 420;
  const height = 240;
  const svg = svgRoot(width, height);

  const topY = 54;
  const bottomY = 168;
  const spacing = width / (concepts.length + 1);

  // Edges first so nodes paint over them.
  concepts.forEach((_, index) => {
    svg.appendChild(el('line', {
      x1: width / 2, y1: topY + 16,
      x2: spacing * (index + 1), y2: bottomY - 16,
      stroke: '#2a2f3d', 'stroke-width': 1.5,
    }));
  });

  if (formulas.length) {
    svg.appendChild(el('rect', {
      x: width / 2 - 88, y: topY - 18, width: 176, height: 36, rx: 8,
      fill: 'rgba(108,140,255,0.14)', stroke: '#6c8cff', 'stroke-width': 1.5,
    }));
    svg.appendChild(el('text', {
      x: width / 2, y: topY + 5, fill: '#6c8cff',
      'font-size': 14, 'text-anchor': 'middle', 'font-family': 'monospace',
    }, formulas[0].label));
  }

  concepts.forEach((node, index) => {
    const cx = spacing * (index + 1);
    const label = node.label;
    const boxWidth = Math.max(74, label.length * 7.4);
    svg.appendChild(el('rect', {
      x: cx - boxWidth / 2, y: bottomY - 17, width: boxWidth, height: 34, rx: 8,
      fill: '#1e222d', stroke: '#2a2f3d', 'stroke-width': 1.5,
    }));
    svg.appendChild(el('text', {
      x: cx, y: bottomY + 5, fill: '#e8eaf0', 'font-size': 12, 'text-anchor': 'middle',
    }, label));
  });

  return svg;
}

function renderDiagram(data) {
  const wrap = document.createElement('div');
  wrap.className = 'concept-grid';
  (data.elements || []).forEach((element) => {
    const node = document.createElement('div');
    node.className = 'concept-node';
    node.textContent = element.label || element.type;
    wrap.appendChild(node);
  });
  if (data.description) {
    const chip = document.createElement('div');
    chip.className = 'analogy-chip';
    chip.textContent = data.description;
    wrap.appendChild(chip);
  }
  return wrap;
}

/** Last-resort card so an unknown visual type still shows something useful. */
function renderFallback(spec) {
  const wrap = document.createElement('div');
  wrap.className = 'concept-grid';
  const values = Object.values(spec.data || {}).flat().filter((v) => typeof v === 'string');
  if (!values.length) {
    const empty = document.createElement('p');
    empty.className = 'visual-empty';
    empty.textContent = `Visual type "${spec.type}" has no dedicated renderer yet.`;
    wrap.appendChild(empty);
    return wrap;
  }
  values.forEach((value) => {
    const node = document.createElement('div');
    node.className = 'concept-node';
    node.textContent = value;
    wrap.appendChild(node);
  });
  return wrap;
}

const RENDERERS = {
  circuit: renderCircuit,
  equation: renderEquation,
  graph: renderGraph,
  concept_map: renderConceptMap,
  diagram: renderDiagram,
};

/**
 * Draw a Scene.visual into a container.
 * @param {HTMLElement} container
 * @param {{type: string, data: object}} spec
 * @returns {object} the render hint reported by services/visuals
 */
export function renderVisual(container, spec) {
  container.textContent = '';
  if (!spec || !spec.type) {
    container.appendChild(renderFallback({ type: 'unknown', data: {} }));
    return { library: 'html' };
  }

  // Person 3's module decides which library a real renderer should use; we
  // surface it so the choice stays owned by services/visuals.
  const hint = getRenderHint(spec);

  const renderer = RENDERERS[spec.type];
  container.appendChild(renderer ? renderer(spec.data || {}) : renderFallback(spec));
  return hint;
}
