/**
 * Rich visual specification generators for GuruFlow.
 * Provides complete data structures ready for frontend SVG/Canvas/KaTeX/Chart.js rendering.
 * @module visual-specs
 */

/**
 * Creates a comprehensive circuit diagram visual specification ready for SVG/Canvas rendering.
 *
 * @param {Array<Object>|Object} [componentsOrOptions={}] - Custom components array OR configuration options.
 * @param {Object} [maybeOptions={}] - Options if components array was passed as first argument.
 * @returns {Object} The circuit visual specification.
 */
export function createCircuitSpec(componentsOrOptions = {}, maybeOptions = {}) {
  let customComponents = null;
  let options = {};

  if (Array.isArray(componentsOrOptions)) {
    customComponents = componentsOrOptions;
    options = maybeOptions || {};
  } else if (typeof componentsOrOptions === 'object' && componentsOrOptions !== null) {
    options = componentsOrOptions;
    if (Array.isArray(options.components)) {
      customComponents = options.components;
    }
  }

  const {
    voltage = '10V',
    resistance = '5Ω',
    current = '2A',
    highlight = 'ammeter',
    title = "Ohm's Law Closed Circuit Schematic",
    switchState = 'closed',
    includeBulb = false,
    connections: customConnections = null
  } = options;

  // Extract numeric values if strings passed
  const vNum = typeof voltage === 'number' ? voltage : parseFloat(String(voltage)) || 10;
  const rNum = typeof resistance === 'number' ? resistance : parseFloat(String(resistance)) || 5;
  const iCalculated = (vNum / rNum).toFixed(1).replace(/\.0$/, '');
  const iDisplay = current && current !== '2A' ? current : `${iCalculated}A`;

  // Standard component definitions with positions, bounding boxes, and port terminals
  const defaultComponents = [
    {
      id: 'bat-1',
      type: 'battery',
      label: `V = ${voltage}`,
      value: vNum,
      unit: 'V',
      symbol: 'V',
      position: { x: 80, y: 160 },
      coordinates: { x: 80, y: 160, width: 60, height: 100 },
      terminals: {
        positive: { id: 'positive', name: 'anode', x: 80, y: 160, type: 'anode' },
        negative: { id: 'negative', name: 'cathode', x: 80, y: 260, type: 'cathode' }
      },
      ports: [
        { id: 'anode', name: 'positive', x: 80, y: 160 },
        { id: 'cathode', name: 'negative', x: 80, y: 260 }
      ],
      state: 'active',
      description: 'DC Voltage Source providing electromotive force'
    },
    {
      id: 'sw-1',
      type: 'switch',
      label: `Switch (${switchState === 'closed' ? 'Closed' : 'Open'})`,
      state: switchState,
      position: { x: 220, y: 70 },
      coordinates: { x: 220, y: 70, width: 60, height: 30 },
      terminals: {
        terminal_a: { id: 'terminal_a', name: 'inlet', x: 220, y: 80, type: 'terminal_a' },
        terminal_b: { id: 'terminal_b', name: 'outlet', x: 280, y: 80, type: 'terminal_b' }
      },
      ports: [
        { id: 'terminal_a', name: 'terminal_a', x: 220, y: 80 },
        { id: 'terminal_b', name: 'terminal_b', x: 280, y: 80 }
      ],
      description: 'Single-pole single-throw switch completing circuit loop'
    },
    {
      id: 'res-1',
      type: 'resistor',
      label: `R = ${resistance}`,
      value: rNum,
      unit: 'Ω',
      symbol: 'R',
      position: { x: 380, y: 65 },
      coordinates: { x: 380, y: 65, width: 80, height: 35 },
      terminals: {
        terminal_a: { id: 'terminal_a', name: 'inlet', x: 380, y: 80, type: 'terminal_a' },
        terminal_b: { id: 'terminal_b', name: 'outlet', x: 460, y: 80, type: 'terminal_b' }
      },
      ports: [
        { id: 'terminal_a', name: 'terminal_a', x: 380, y: 80 },
        { id: 'terminal_b', name: 'terminal_b', x: 460, y: 80 }
      ],
      powerDissipation: `${(vNum * parseFloat(iDisplay)).toFixed(1)}W`,
      description: 'Linear ohmic resistor opposing charge flow'
    },
    {
      id: 'amm-1',
      type: 'ammeter',
      label: `I = ${iDisplay}`,
      value: parseFloat(iDisplay),
      unit: 'A',
      symbol: 'I',
      position: { x: 460, y: 180 },
      coordinates: { x: 460, y: 180, width: 60, height: 60 },
      terminals: {
        anode: { id: 'anode', name: 'in', x: 490, y: 180, type: 'anode' },
        cathode: { id: 'cathode', name: 'out', x: 490, y: 240, type: 'cathode' },
        terminal_a: { id: 'terminal_a', name: 'in', x: 490, y: 180, type: 'terminal_a' },
        terminal_b: { id: 'terminal_b', name: 'out', x: 490, y: 240, type: 'terminal_b' }
      },
      ports: [
        { id: 'anode', name: 'positive', x: 490, y: 180 },
        { id: 'cathode', name: 'negative', x: 490, y: 240 }
      ],
      state: 'measuring',
      description: 'Ideal series ammeter measuring current flow'
    }
  ];

  if (includeBulb) {
    defaultComponents.push({
      id: 'bulb-1',
      type: 'bulb',
      label: 'Indicator Lamp',
      position: { x: 270, y: 320 },
      coordinates: { x: 270, y: 320, width: 50, height: 50 },
      terminals: {
        terminal_a: { id: 'terminal_a', name: 'in', x: 270, y: 340, type: 'terminal_a' },
        terminal_b: { id: 'terminal_b', name: 'out', x: 320, y: 340, type: 'terminal_b' }
      },
      ports: [
        { id: 'terminal_a', name: 'in', x: 270, y: 340 },
        { id: 'terminal_b', name: 'out', x: 320, y: 340 }
      ],
      state: switchState === 'closed' ? 'glowing' : 'off',
      description: 'Incandescent indicator load'
    });
  }

  const components = customComponents || defaultComponents;

  // Standard connections with waypoints for SVG orthogonal path rendering
  const defaultConnections = [
    {
      id: 'wire-1',
      from: 'bat-1',
      fromComponent: 'bat-1',
      fromPort: 'positive',
      to: 'sw-1',
      toComponent: 'sw-1',
      toPort: 'terminal_a',
      waypoints: [[80, 160], [80, 80], [220, 80]],
      path: 'M 80 160 L 80 80 L 220 80'
    },
    {
      id: 'wire-2',
      from: 'sw-1',
      fromComponent: 'sw-1',
      fromPort: 'terminal_b',
      to: 'res-1',
      toComponent: 'res-1',
      toPort: 'terminal_a',
      waypoints: [[280, 80], [380, 80]],
      path: 'M 280 80 L 380 80'
    },
    {
      id: 'wire-3',
      from: 'res-1',
      fromComponent: 'res-1',
      fromPort: 'terminal_b',
      to: 'amm-1',
      toComponent: 'amm-1',
      toPort: 'anode',
      waypoints: [[460, 80], [490, 80], [490, 180]],
      path: 'M 460 80 L 490 80 L 490 180'
    },
    {
      id: 'wire-4',
      from: 'amm-1',
      fromComponent: 'amm-1',
      fromPort: 'cathode',
      to: 'bat-1',
      toComponent: 'bat-1',
      toPort: 'negative',
      waypoints: [[490, 240], [490, 340], [80, 340], [80, 260]],
      path: 'M 490 240 L 490 340 L 80 340 L 80 260'
    }
  ];

  const connections = customConnections || defaultConnections;

  const layout = {
    width: 580,
    height: 400,
    viewBox: '0 0 580 400',
    padding: 24,
    gridSize: 20
  };

  const currentFlow = {
    direction: 'clockwise',
    active: switchState === 'closed',
    speed: 'normal',
    intensity: iDisplay,
    carrier: 'conventional_current',
    path: [
      [80, 160], [80, 80], [220, 80], [280, 80],
      [380, 80], [460, 80], [490, 80], [490, 180],
      [490, 240], [490, 340], [80, 340], [80, 260]
    ]
  };

  return {
    type: 'circuit',
    data: {
      title,
      components,
      connections,
      currentFlow,
      layout,
      dimensions: { width: layout.width, height: layout.height, viewBox: layout.viewBox },
      viewBox: layout.viewBox,
      annotations: [
        'Conventional current flows from positive (+) to negative (-) terminal.',
        `Circuit parameters: V = ${voltage}, R = ${resistance}, I = ${iDisplay}.`
      ],
      highlight
    }
  };
}

/**
 * Creates a step-by-step mathematical transformation specification (KaTeX-compatible).
 *
 * @param {Array<Object>|Object} [stepsOrOptions={}] - Custom steps array OR configuration options.
 * @param {Object} [maybeOptions={}] - Options if steps array was passed as first argument.
 * @returns {Object} The equation visual specification.
 */
export function createEquationSpec(stepsOrOptions = {}, maybeOptions = {}) {
  let customSteps = null;
  let options = {};

  if (Array.isArray(stepsOrOptions)) {
    customSteps = stepsOrOptions;
    options = maybeOptions || {};
  } else if (typeof stepsOrOptions === 'object' && stepsOrOptions !== null) {
    options = stepsOrOptions;
    if (Array.isArray(options.steps)) {
      customSteps = options.steps;
    }
  }

  const {
    voltage = '10V',
    resistance = '5Ω',
    current = '2A',
    highlight = 'step-2',
    mode = 'standard',
    title = "Deriving Current using Ohm's Law"
  } = options;

  const vNum = typeof voltage === 'number' ? voltage : parseFloat(String(voltage)) || 10;
  const rNum = typeof resistance === 'number' ? resistance : parseFloat(String(resistance)) || 5;
  const iCalculated = (vNum / rNum).toFixed(1).replace(/\.0$/, '');

  const defaultSteps = [
    {
      stepIndex: 0,
      id: 'step-1',
      title: "Ohm's Law Standard Formula",
      label: "Ohm's Law Standard Formula",
      rawExpression: 'V = I * R',
      expression: 'V = I \\cdot R',
      latex: 'V = I \\cdot R',
      explanation: 'Potential difference (V) equals Current (I) multiplied by Resistance (R).',
      caption: 'Potential difference (V) equals Current (I) multiplied by Resistance (R).',
      highlightedTerms: ['V', 'I', 'R'],
      highlight: false
    },
    {
      stepIndex: 1,
      id: 'step-2',
      title: 'Rearrange Solving for Current (I)',
      label: 'Rearrange Solving for Current (I)',
      rawExpression: 'I = V / R',
      expression: 'I = \\frac{V}{R}',
      latex: 'I = \\frac{V}{R}',
      explanation: 'Dividing both sides by Resistance (R) isolates Current (I).',
      caption: 'Dividing both sides by Resistance (R) isolates Current (I).',
      highlightedTerms: ['I', 'V', 'R'],
      highlight: highlight === 'step-2' || highlight === 'result',
      misconceptionAnnotation: {
        flag: 'inverse_proportionality',
        note: 'Resistance (R) is in the denominator. As R increases at constant V, I decreases.'
      }
    },
    {
      stepIndex: 2,
      id: 'step-3',
      title: 'Substitute Given Values',
      label: 'Substitute Given Values',
      rawExpression: `I = ${vNum} / ${rNum} = ${iCalculated}A`,
      expression: `I = \\frac{${vNum}\\text{ V}}{${rNum}\\,\\Omega} = ${iCalculated}\\text{ A}`,
      latex: `I = \\frac{${vNum}\\text{ V}}{${rNum}\\,\\Omega} = ${iCalculated}\\text{ A}`,
      explanation: `Substitute V = ${vNum}V and R = ${rNum}Ω to compute I = ${iCalculated}A.`,
      caption: `Substitute V = ${vNum}V and R = ${rNum}Ω to compute I = ${iCalculated}A.`,
      highlightedTerms: ['I', `${iCalculated}A`],
      highlight: highlight === 'step-3'
    }
  ];

  if (mode === 'misconception_repair') {
    defaultSteps.push({
      stepIndex: 3,
      id: 'step-4',
      title: 'Key Proportionality Rule',
      label: 'Key Proportionality Rule',
      rawExpression: 'R up => I down (constant V)',
      expression: '\\uparrow R \\implies \\downarrow I \\quad (\\text{at constant } V)',
      latex: '\\uparrow R \\implies \\downarrow I \\quad (\\text{at constant } V)',
      explanation: 'Resistance opposes current: higher resistance means less current flow.',
      caption: 'Resistance opposes current: higher resistance means less current flow.',
      highlightedTerms: ['R', 'I'],
      highlight: true,
      misconceptionAnnotation: {
        flag: 'direct_vs_inverse_proportionality',
        note: 'Direct proportionality confusion resolved: I is inversely proportional to R.'
      }
    });
  }

  // Normalize custom steps if string array or partial objects were provided
  const normalizedSteps = (customSteps || defaultSteps).map((step, idx) => {
    if (typeof step === 'string') {
      return {
        stepIndex: idx,
        id: `step-${idx + 1}`,
        title: `Step ${idx + 1}`,
        label: `Step ${idx + 1}`,
        rawExpression: step,
        expression: step.replace(/\*/g, '\\cdot').replace(/\//g, '\\div'),
        latex: step.replace(/\*/g, '\\cdot').replace(/\//g, '\\div'),
        explanation: step,
        caption: step,
        highlightedTerms: [],
        highlight: idx === 0
      };
    }
    return {
      stepIndex: typeof step.stepIndex === 'number' ? step.stepIndex : idx,
      id: step.id || `step-${idx + 1}`,
      title: step.title || step.label || `Step ${idx + 1}`,
      label: step.label || step.title || `Step ${idx + 1}`,
      rawExpression: step.rawExpression || step.expression || '',
      expression: step.expression || step.latex || step.rawExpression || '',
      latex: step.latex || step.expression || step.rawExpression || '',
      explanation: step.explanation || step.caption || step.label || '',
      caption: step.caption || step.explanation || step.label || '',
      highlightedTerms: step.highlightedTerms || [],
      highlight: step.highlight ?? (step.id === highlight),
      misconceptionAnnotation: step.misconceptionAnnotation || null
    };
  });

  const variableAnnotations = {
    V: {
      symbol: 'V',
      name: 'Voltage (Potential Difference)',
      unit: 'Volts (V)',
      role: 'Driving force / energy per unit charge',
      value: typeof voltage === 'string' ? voltage : `${voltage}V`
    },
    I: {
      symbol: 'I',
      name: 'Current (Charge Flow Rate)',
      unit: 'Amperes (A)',
      role: 'Rate of charge flow through conductor',
      value: `${iCalculated}A`
    },
    R: {
      symbol: 'R',
      name: 'Resistance (Flow Opposition)',
      unit: 'Ohms (Ω)',
      role: 'Opposition to charge flow',
      value: typeof resistance === 'string' ? resistance : `${resistance}Ω`
    }
  };

  const misconceptionAnnotations = {
    topic: 'direct_vs_inverse_proportionality',
    confusion: 'Current increases when resistance increases',
    correction: 'At constant voltage, current is inversely proportional to resistance: I = V/R',
    rule: 'As R increases in denominator, I decreases'
  };

  return {
    type: 'equation',
    data: {
      title,
      format: 'katex',
      steps: normalizedSteps,
      variables: variableAnnotations,
      variableAnnotations,
      misconceptionAnnotations,
      highlight,
      highlightStepId: highlight
    }
  };
}

/**
 * Creates a Cartesian coordinate graph specification showing I vs R.
 *
 * @param {Array<Object>|Object} [dataOrOptions={}] - Custom points OR configuration options.
 * @param {Object} [maybeOptions={}] - Options if points array was passed.
 * @returns {Object} The graph visual specification.
 */
export function createGraphSpec(dataOrOptions = {}, maybeOptions = {}) {
  let customPoints = null;
  let options = {};

  if (Array.isArray(dataOrOptions)) {
    customPoints = dataOrOptions;
    options = maybeOptions || {};
  } else if (typeof dataOrOptions === 'object' && dataOrOptions !== null) {
    options = dataOrOptions;
    if (Array.isArray(options.points)) {
      customPoints = options.points;
    }
  }

  const {
    voltage = 10,
    rMin = 1,
    rMax = 20,
    title = `Current (I) vs Resistance (R) at Constant Voltage (V = ${voltage}V)`,
    highlightPoints: customHighlightPoints = null,
    xAxis: customXAxis = null,
    yAxis: customYAxis = null
  } = options;

  const vNum = typeof voltage === 'number' ? voltage : parseFloat(String(voltage)) || 10;

  // Generate smooth hyperbolic curve points across range
  const sampleRValues = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 14, 15, 16, 18, 20];
  const computedPoints = sampleRValues
    .filter(r => r >= rMin && r <= rMax)
    .map(r => ({
      x: r,
      y: parseFloat((vNum / r).toFixed(3))
    }));

  const points = customPoints || computedPoints;

  const xAxis = customXAxis || {
    label: 'Resistance (R)',
    symbol: 'R',
    unit: 'Ω',
    min: 0,
    max: Math.max(20, rMax),
    tickInterval: 2,
    ticks: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20],
    scale: 'linear'
  };

  const yMax = Math.ceil((vNum / rMin) + 2);
  const yTicks = [];
  for (let t = 0; t <= Math.max(12, yMax); t += 2) {
    yTicks.push(t);
  }

  const yAxis = customYAxis || {
    label: 'Current (I)',
    symbol: 'I',
    unit: 'A',
    min: 0,
    max: Math.max(12, yMax),
    tickInterval: 2,
    ticks: yTicks,
    scale: 'linear'
  };

  const gridlines = {
    show: true,
    xStep: 2,
    yStep: 2,
    color: '#E2E8F0',
    strokeDasharray: '3 3'
  };

  const series = [
    {
      id: 'series-i-vs-r',
      name: `I = ${vNum} / R`,
      label: `Current I = ${vNum}/R`,
      curveType: 'inverse_proportionality',
      type: 'curve',
      formula: `I = ${vNum} / R`,
      mathematicalFormula: `I = \\frac{${vNum}}{R}`,
      color: '#3B82F6',
      strokeWidth: 3,
      points
    }
  ];

  const highlightedOperatingPoints = customHighlightPoints || [
    {
      x: 5,
      y: parseFloat((vNum / 5).toFixed(2)),
      label: `R = 5Ω, I = ${(vNum / 5).toFixed(1)}A`,
      description: 'Base operating point',
      color: '#10B981'
    },
    {
      x: 10,
      y: parseFloat((vNum / 10).toFixed(2)),
      label: `R = 10Ω, I = ${(vNum / 10).toFixed(1)}A`,
      description: 'Doubled resistance halves current (Inverse Proportionality)',
      color: '#EF4444'
    }
  ];

  const annotations = [
    {
      x: 10,
      y: parseFloat((vNum / 10).toFixed(2)),
      text: 'As Resistance (R) increases, Current (I) decreases (Inverse Proportionality)',
      trend: 'descending',
      position: 'top-right'
    }
  ];

  return {
    type: 'graph',
    data: {
      title,
      graphType: 'inverse_proportionality',
      xAxis,
      yAxis,
      gridlines,
      series,
      points,
      highlightedOperatingPoints,
      highlightPoints: highlightedOperatingPoints,
      annotations,
      trendAnnotations: annotations,
      formula: `I = ${vNum} / R`
    }
  };
}

/**
 * Creates a hierarchical concept map knowledge graph specification.
 *
 * @param {Array<Object>|Object} [nodesOrOptions={}] - Custom nodes array OR configuration options.
 * @param {Array<Object>|Object} [edgesOrOptions={}] - Custom edges array OR options if nodes was first arg.
 * @param {Object} [maybeOptions={}] - Options if nodes and edges were passed.
 * @returns {Object} The concept map visual specification.
 */
export function createConceptMapSpec(nodesOrOptions = {}, edgesOrOptions = {}, maybeOptions = {}) {
  let customNodes = null;
  let customEdges = null;
  let options = {};

  if (Array.isArray(nodesOrOptions)) {
    customNodes = nodesOrOptions;
    if (Array.isArray(edgesOrOptions)) {
      customEdges = edgesOrOptions;
      options = maybeOptions || {};
    } else {
      options = edgesOrOptions || {};
    }
  } else if (typeof nodesOrOptions === 'object' && nodesOrOptions !== null) {
    options = nodesOrOptions;
    if (Array.isArray(options.nodes)) customNodes = options.nodes;
    if (Array.isArray(options.edges)) customEdges = options.edges;
  }

  const {
    title = 'Electricity & Ohm\'s Law Concept Map',
    layout: customLayout = null
  } = options;

  const defaultNodes = [
    {
      id: 'v',
      label: 'Voltage (V)',
      category: 'quantity',
      type: 'concept',
      symbol: 'V',
      unit: 'Volts (V)',
      description: 'Electric potential difference pushing charge through circuit',
      position: { x: 150, y: 100 },
      coordinates: { x: 150, y: 100 },
      level: 0,
      style: {
        shape: 'rectangle',
        fill: '#DBEAFE',
        stroke: '#2563EB',
        color: '#1E40AF'
      }
    },
    {
      id: 'r',
      label: 'Resistance (R)',
      category: 'quantity',
      type: 'concept',
      symbol: 'R',
      unit: 'Ohms (Ω)',
      description: 'Opposition to the flow of electric charge',
      position: { x: 450, y: 100 },
      coordinates: { x: 450, y: 100 },
      level: 0,
      style: {
        shape: 'rectangle',
        fill: '#FEE2E2',
        stroke: '#DC2626',
        color: '#991B1B'
      }
    },
    {
      id: 'ohm',
      label: "Ohm's Law (V = IR)",
      category: 'law',
      type: 'formula',
      symbol: 'V=IR',
      description: 'Fundamental linear relationship governing electric circuits',
      position: { x: 300, y: 220 },
      coordinates: { x: 300, y: 220 },
      level: 1,
      style: {
        shape: 'rounded',
        fill: '#FEF3C7',
        stroke: '#D97706',
        color: '#92400E'
      }
    },
    {
      id: 'i',
      label: 'Current (I)',
      category: 'quantity',
      type: 'concept',
      symbol: 'I',
      unit: 'Amperes (A)',
      description: 'Rate of electric charge flow (I = V/R)',
      position: { x: 300, y: 350 },
      coordinates: { x: 300, y: 350 },
      level: 2,
      style: {
        shape: 'rectangle',
        fill: '#D1FAE5',
        stroke: '#059669',
        color: '#065F46'
      }
    }
  ];

  const defaultEdges = [
    {
      id: 'edge-ohm-v',
      from: 'ohm',
      to: 'v',
      relationType: 'defines',
      label: 'defines',
      directional: true,
      style: { stroke: '#64748B', strokeWidth: 2 }
    },
    {
      id: 'edge-ohm-r',
      from: 'ohm',
      to: 'r',
      relationType: 'defines',
      label: 'defines',
      directional: true,
      style: { stroke: '#64748B', strokeWidth: 2 }
    },
    {
      id: 'edge-ohm-i',
      from: 'ohm',
      to: 'i',
      relationType: 'defines',
      label: 'defines',
      directional: true,
      style: { stroke: '#64748B', strokeWidth: 2 }
    },
    {
      id: 'edge-v-i',
      from: 'v',
      to: 'i',
      relationType: 'drives',
      label: 'drives / pushes (+)',
      directional: true,
      style: { stroke: '#2563EB', strokeWidth: 2 }
    },
    {
      id: 'edge-r-i',
      from: 'r',
      to: 'i',
      relationType: 'opposes',
      label: 'restricts / opposes (-)',
      directional: true,
      style: { stroke: '#DC2626', strokeWidth: 2, strokeDasharray: '4 4' }
    }
  ];

  // Convert string array nodes to objects if needed (e.g. from minimal fixtures)
  const nodes = (customNodes || defaultNodes).map((node, idx) => {
    if (typeof node === 'string') {
      return {
        id: `node-${idx + 1}`,
        label: node,
        category: 'concept',
        type: 'concept',
        description: node,
        position: { x: 150 + (idx % 2) * 300, y: 100 + Math.floor(idx / 2) * 120 },
        coordinates: { x: 150 + (idx % 2) * 300, y: 100 + Math.floor(idx / 2) * 120 },
        level: Math.floor(idx / 2),
        style: { shape: 'rounded', fill: '#E2E8F0', stroke: '#475569', color: '#1E293B' }
      };
    }
    return {
      ...node,
      coordinates: node.coordinates || node.position || { x: 0, y: 0 },
      position: node.position || node.coordinates || { x: 0, y: 0 }
    };
  });

  const edges = customEdges || defaultEdges;

  const layout = customLayout || {
    type: 'hierarchical',
    orientation: 'top-to-bottom',
    width: 600,
    height: 450,
    nodeSpacing: 100,
    levelSpacing: 120
  };

  return {
    type: 'concept_map',
    data: {
      title,
      layout,
      nodes,
      edges
    }
  };
}

/**
 * Creates a hydraulic analogy diagram specification for Ohm's Law.
 *
 * @param {Object} [options={}] - Configuration options.
 * @returns {Object} The water-pipe diagram visual specification.
 */
export function createWaterPipeAnalogySpec(options = {}) {
  const {
    title = 'Water Pipe Analogy for Electric Circuits',
    scenario = 'constrictedPipe',
    flowRate = '2.0 L/s',
    voltage = 10,
    resistance = 5
  } = options;

  const elements = [
    {
      id: 'water_pump',
      type: 'water_pump',
      label: 'Water Pump (Voltage / Pressure)',
      electricalEquivalent: 'Battery / Voltage Source (V)',
      formulaSymbol: 'V',
      role: 'Pressure Generator',
      position: { x: 80, y: 160 },
      coordinates: { x: 80, y: 160, width: 90, height: 90 },
      pressurePsi: 10,
      state: 'active',
      description: 'Pump creates water pressure differential, just as a battery creates electric potential difference.'
    },
    {
      id: 'pipe_constriction',
      type: 'pipe_constriction',
      label: 'Narrow Constriction (Resistance, R)',
      electricalEquivalent: 'Resistor (R)',
      formulaSymbol: 'R',
      role: 'Flow Restriction',
      position: { x: 300, y: 60 },
      coordinates: { x: 300, y: 60, width: 120, height: 40 },
      constrictionFactor: scenario === 'constrictedPipe' ? 0.75 : 0.25,
      description: 'Constriction restricts water throughput, just as resistance impedes electron flow.'
    },
    {
      id: 'water_flow',
      type: 'water_flow',
      label: 'Water Flow Rate (Current, I)',
      electricalEquivalent: 'Current (I)',
      formulaSymbol: 'I',
      role: 'Volume Flow Rate',
      position: { x: 300, y: 260 },
      coordinates: { x: 300, y: 260, width: 140, height: 50 },
      flowRate,
      velocityVector: { vx: 4, vy: 0 },
      description: 'Volume of water passing per second, directly analogous to electric charge flow per second.'
    },
    {
      id: 'pipe_reservoir',
      type: 'pipe_reservoir',
      label: 'Return Pipe (Conductor/Ground)',
      electricalEquivalent: 'Return Wire / Ground',
      position: { x: 80, y: 280 },
      coordinates: { x: 80, y: 280, width: 100, height: 40 },
      description: 'Completes the closed hydraulic circuit.'
    }
  ];

  const coordinateBounds = {
    width: 600,
    height: 420,
    viewBox: '0 0 600 420',
    padding: 20
  };

  const flowParticles = {
    count: 24,
    velocity: { x: 4, y: 0 },
    velocityVector: { vx: 4, vy: 0 },
    direction: 'clockwise',
    speed: scenario === 'constrictedPipe' ? 'slow' : 'fast',
    active: true,
    color: '#06B6D4'
  };

  const comparisonMappingTable = [
    {
      hydraulicElement: 'Water Pump Pressure (P)',
      electricalEquivalent: 'Voltage (V)',
      formulaSymbol: 'V',
      concept: 'Pushing force that initiates flow',
      unit: 'Pascal (Pa) ↔ Volt (V)'
    },
    {
      hydraulicElement: 'Pipe Constriction / Narrowness',
      electricalEquivalent: 'Resistance (R)',
      formulaSymbol: 'R',
      concept: 'Physical opposition to fluid/charge movement',
      unit: 'Hydraulic Resistance ↔ Ohm (Ω)'
    },
    {
      hydraulicElement: 'Water Flow Rate (Q)',
      electricalEquivalent: 'Current (I)',
      formulaSymbol: 'I',
      concept: 'Rate of volume/charge passing per second',
      unit: 'Liters/sec (L/s) ↔ Ampere (A)'
    },
    {
      hydraulicElement: 'Closed Pipe Loop',
      electricalEquivalent: 'Closed Electric Circuit',
      formulaSymbol: 'Loop',
      concept: 'Continuous unbroken path required for circulation',
      unit: 'N/A'
    }
  ];

  const scenarioStates = {
    widePipe: {
      label: 'Wide Pipe (Low Resistance)',
      resistanceLevel: 'low',
      flowLevel: 'high',
      currentA: '4.0A',
      pressure: `${voltage}V`,
      pipeDiameterMm: 50,
      description: 'Wide pipe offers little resistance; water flows quickly and in large volume.'
    },
    constrictedPipe: {
      label: 'Narrow Constriction (High Resistance)',
      resistanceLevel: 'high',
      flowLevel: 'low',
      currentA: '1.0A',
      pressure: `${voltage}V`,
      pipeDiameterMm: 15,
      description: 'Narrow pipe creates high resistance; water flow drops dramatically.'
    }
  };

  return {
    type: 'diagram',
    data: {
      title,
      diagramType: 'hydraulic_analogy',
      elements,
      coordinateBounds,
      bounds: coordinateBounds,
      flowParticles,
      velocityVector: flowParticles.velocityVector,
      comparisonMappingTable,
      mappings: comparisonMappingTable,
      scenarioStates,
      scenarios: scenarioStates,
      currentScenario: scenario,
      annotations: [
        'Narrowing the pipe (higher R) REDUCES the flow rate of water (lower I).',
        'Higher pump pressure (higher V) INCREASES the flow rate of water (higher I).'
      ],
      description: 'Water pipe analogy for Ohm\'s Law: Water pump provides pressure (Voltage), narrow pipe constricts flow (Resistance), and water flow rate represents Current.'
    }
  };
}

/**
 * Creates a compound 3-in-1 visual spec combining:
 * 1. Equation transformation: V=IR -> I=V/R with misconception highlight
 * 2. Water-pipe hydraulic analogy diagram
 * 3. Descending I-vs-R inverse proportionality graph
 *
 * @param {Object} [options={}] - Configuration options.
 * @returns {Object} The compound repair visual specification.
 */
export function createRepairVisualSpec(options = {}) {
  const {
    voltage = 10,
    title = "Ohm's Law Misconception Repair: Inverse Proportionality (I = V/R)"
  } = options;

  const eqSpec = createEquationSpec({
    voltage,
    mode: 'misconception_repair',
    title: 'Formula Transformation: I = V / R',
    highlight: 'step-2'
  });

  const analogySpec = createWaterPipeAnalogySpec({
    voltage,
    scenario: 'constrictedPipe',
    title: 'Hydraulic Analogy: Pipe Constriction vs Current Flow'
  });

  const graphSpec = createGraphSpec({
    voltage,
    title: `Current (I) vs Resistance (R) at Constant Voltage (V = ${voltage}V)`
  });

  return {
    type: 'diagram',
    data: {
      composite: true,
      diagramType: 'compound_repair',
      title,
      equation: eqSpec.data,
      analogy: analogySpec.data,
      graph: graphSpec.data,
      misconception: {
        diagnosed: 'direct-proportionality confusion',
        description: 'Learner assumed current increases when resistance increases',
        correctPrinciple: 'At constant voltage, Current (I) is inversely proportional to Resistance (R): I = V/R',
        formulaCorrection: 'I = \\frac{V}{R} \\implies \\uparrow R \\implies \\downarrow I'
      },
      layout: {
        mode: 'multi_panel',
        panels: ['equation', 'analogy', 'graph'],
        responsive: true
      }
    }
  };
}
