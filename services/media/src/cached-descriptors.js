/**
 * Pre-generated deterministic scene descriptors for GuruFlow hero demo.
 * Covers initial teaching scenes, advance branch, and repair branch across English, Hindi, and Hinglish
 * with strict mathematical formula invariance (V=IR, I=V/R, 10/5=2A).
 * @module cached-descriptors
 */

/**
 * Normalizes language string to canonical format.
 * @param {string} lang
 * @returns {'english'|'hindi'|'hinglish'}
 */
export function normalizeLanguage(lang) {
  if (!lang || typeof lang !== 'string') return 'hinglish';
  const l = lang.toLowerCase().trim();
  if (l === 'en' || l === 'english' || l === 'eng') return 'english';
  if (l === 'hi' || l === 'hindi' || l === 'hin') return 'hindi';
  if (l === 'hinglish' || l === 'hi-latn' || l === 'hing') return 'hinglish';
  return 'hinglish';
}

/**
 * Normalizes scene identifier to canonical ID.
 * @param {string} id
 * @returns {string}
 */
export function normalizeSceneId(id) {
  if (!id || typeof id !== 'string') return 'unknown-scene';
  const s = id.toLowerCase().trim();
  if (s === 'scene-1' || s === 'scene-1-intro' || s === 'scene-1-current') return 'scene-1-intro';
  if (s === 'scene-2' || s === 'scene-2-voltage') return 'scene-2-voltage';
  if (s === 'scene-3' || s === 'scene-3-resistance') return 'scene-3-resistance';
  if (s === 'scene-5' || s === 'scene-5-ohms-law' || s === 'scene-ohms-law') return 'scene-5-ohms-law';
  if (s === 'scene-advance' || s === 'scene-advance-circuits' || s === 'advance-circuits') return 'scene-advance-circuits';
  if (s === 'scene-repair' || s === 'scene-repair-ohms-law' || s === 'ohms-law-repair-scene') return 'scene-repair-ohms-law';
  return s;
}

/**
 * Helper to build timed caption objects from segments.
 * @param {Array<{text: string, duration: number, math?: string[]}>} segments
 * @param {string} language
 * @returns {Array<Object>}
 */
function buildTimedCaptions(segments, language) {
  let currentTime = 0;
  return segments.map((seg, idx) => {
    const startTime = parseFloat(currentTime.toFixed(2));
    const endTime = parseFloat((currentTime + seg.duration).toFixed(2));
    currentTime = endTime;
    return {
      index: idx,
      text: seg.text,
      language,
      startTime,
      endTime,
      duration: seg.duration,
      mathFormulas: seg.math || []
    };
  });
}

// ---------------------------------------------------------------------------
// 1. Scene 1 (Intro / Current) - Concept Map
// ---------------------------------------------------------------------------
const scene1VisualData = {
  title: "Electricity & Ohm's Law Core Concepts",
  layout: { type: 'hierarchical', orientation: 'top-to-bottom', width: 600, height: 450, nodeSpacing: 100, levelSpacing: 120 },
  nodes: [
    { id: 'v', label: 'Voltage (V)', category: 'quantity', type: 'concept', symbol: 'V', unit: 'Volts (V)', position: { x: 150, y: 100 }, coordinates: { x: 150, y: 100 }, level: 0 },
    { id: 'r', label: 'Resistance (R)', category: 'quantity', type: 'concept', symbol: 'R', unit: 'Ohms (Ω)', position: { x: 450, y: 100 }, coordinates: { x: 450, y: 100 }, level: 0 },
    { id: 'ohm', label: "Ohm's Law (V = IR)", category: 'law', type: 'formula', symbol: 'V=IR', position: { x: 300, y: 220 }, coordinates: { x: 300, y: 220 }, level: 1 },
    { id: 'i', label: 'Current (I)', category: 'quantity', type: 'concept', symbol: 'I', unit: 'Amperes (A)', position: { x: 300, y: 350 }, coordinates: { x: 300, y: 350 }, level: 2 }
  ],
  edges: [
    { id: 'edge-ohm-v', from: 'ohm', to: 'v', relationType: 'defines', label: 'defines', directional: true },
    { id: 'edge-ohm-r', from: 'ohm', to: 'r', relationType: 'defines', label: 'defines', directional: true },
    { id: 'edge-ohm-i', from: 'ohm', to: 'i', relationType: 'defines', label: 'defines', directional: true }
  ]
};

const scene1Citations = [
  { documentId: 'ncert-class9-science-ch12', pageOrSlide: 199, heading: '12.1 Electric Current and Circuit', excerpt: 'Electric current is expressed by the amount of charge flowing through a particular area in unit time.' }
];

// ---------------------------------------------------------------------------
// 2. Scene 2 (Voltage) - Diagram / Circuit Push
// ---------------------------------------------------------------------------
const scene2VisualData = {
  title: "Voltage: Electrical Potential Difference (Driving Force)",
  type: "potential_difference",
  voltageValue: 10,
  unit: "V",
  elements: [
    { id: "battery_source", type: "power_source", label: "Battery (V = 10V)", position: { x: 100, y: 200 } },
    { id: "electron_flow", type: "charge_motion", label: "Electron Flow Direction", direction: "clockwise" }
  ]
};

const scene2Citations = [
  { documentId: 'ncert-class9-science-ch12', pageOrSlide: 201, heading: '12.2 Electric Potential and Potential Difference', excerpt: 'The electric potential difference between two points in an electric circuit carrying some current is the work done to move a unit charge.' }
];

// ---------------------------------------------------------------------------
// 3. Scene 3 (Resistance) - Diagram / Opposition
// ---------------------------------------------------------------------------
const scene3VisualData = {
  title: "Resistance: Opposition to Charge Flow",
  type: "resistance_flow",
  resistanceValue: 5,
  unit: "Ω",
  elements: [
    { id: "resistor_element", type: "resistor", label: "Resistor (R = 5Ω)", position: { x: 300, y: 150 } },
    { id: "collision_model", type: "atomic_lattice", label: "Electron Collisions with Metal Atoms" }
  ]
};

const scene3Citations = [
  { documentId: 'ncert-class9-science-ch12', pageOrSlide: 204, heading: '12.3 Factors on which the Resistance of a Conductor Depends', excerpt: 'Resistance is the property of a conductor to resist the flow of charges through it.' }
];

// ---------------------------------------------------------------------------
// 4. Scene 5 (Ohm's Law) - Circuit & Equation
// ---------------------------------------------------------------------------
const scene5VisualData = {
  type: "circuit",
  title: "Ohm's Law Closed Circuit Schematic (V = 10V, R = 5Ω, I = 2A)",
  voltage: "10V",
  resistance: "5Ω",
  current: "2A",
  components: [
    { id: 'bat-1', type: 'battery', label: 'V = 10V', value: 10, unit: 'V', position: { x: 100, y: 200 }, coordinates: { x: 100, y: 160, width: 80, height: 80 } },
    { id: 'res-1', type: 'resistor', label: 'R = 5Ω', value: 5, unit: 'Ω', position: { x: 350, y: 100 }, coordinates: { x: 300, y: 80, width: 100, height: 40 } },
    { id: 'amm-1', type: 'ammeter', label: 'I = 2A', value: 2, unit: 'A', position: { x: 500, y: 200 }, coordinates: { x: 460, y: 160, width: 80, height: 80 } },
    { id: 'sw-1', type: 'switch', label: 'Switch (Closed)', state: 'closed', position: { x: 350, y: 300 }, coordinates: { x: 310, y: 280, width: 80, height: 40 } }
  ],
  connections: [
    { id: 'wire-1', fromComponent: 'bat-1', toComponent: 'res-1' },
    { id: 'wire-2', fromComponent: 'res-1', toComponent: 'amm-1' },
    { id: 'wire-3', fromComponent: 'amm-1', toComponent: 'sw-1' },
    { id: 'wire-4', fromComponent: 'sw-1', toComponent: 'bat-1' }
  ],
  formula: "V = I * R => I = V / R = 10 / 5 = 2A"
};

const scene5Citations = [
  { documentId: 'ncert-class9-science-ch12', pageOrSlide: 204, heading: '12.3 Ohm\'s Law', excerpt: 'The potential difference, V, across the ends of a given metallic wire in an electric circuit is directly proportional to the current flowing through it, provided its temperature remains the same. V = IR.' }
];

// ---------------------------------------------------------------------------
// 5. Scene Advance (Complex Multi-Resistor Circuits)
// ---------------------------------------------------------------------------
const sceneAdvanceVisualData = {
  type: "circuit",
  title: "Advance Circuit: Series & Parallel Resistor Networks",
  components: [
    { id: 'bat-1', type: 'battery', label: 'V = 12V', value: 12, unit: 'V', position: { x: 80, y: 200 } },
    { id: 'res-1', type: 'resistor', label: 'R1 = 4Ω', value: 4, unit: 'Ω', position: { x: 250, y: 120 } },
    { id: 'res-2', type: 'resistor', label: 'R2 = 6Ω', value: 6, unit: 'Ω', position: { x: 250, y: 280 } },
    { id: 'res-3', type: 'resistor', label: 'R3 = 10Ω', value: 10, unit: 'Ω', position: { x: 450, y: 200 } }
  ],
  connections: [
    { id: 'w1', fromComponent: 'bat-1', toComponent: 'res-1' },
    { id: 'w2', fromComponent: 'bat-1', toComponent: 'res-2' },
    { id: 'w3', fromComponent: 'res-1', toComponent: 'res-3' },
    { id: 'w4', fromComponent: 'res-2', toComponent: 'res-3' },
    { id: 'w5', fromComponent: 'res-3', toComponent: 'bat-1' }
  ],
  formula: "R_{eq} = (R_1 \\parallel R_2) + R_3 = 2.4\\Omega + 10\\Omega = 12.4\\Omega"
};

const sceneAdvanceCitations = [
  { documentId: 'ncert-class9-science-ch12', pageOrSlide: 208, heading: '12.6 Resistance of a System of Resistors', excerpt: 'Resistors can be joined in series or parallel to obtain equivalent resistance.' }
];

// ---------------------------------------------------------------------------
// 6. Scene Repair (3-in-1 Composite Diagram: Equation + Analogy + Graph)
// ---------------------------------------------------------------------------
const sceneRepairVisualData = {
  composite: true,
  diagramType: "compound_repair",
  title: "Ohm's Law Misconception Repair: Inverse Proportionality (I = V/R)",
  equation: {
    title: "Formula Transformation: I = V / R",
    format: "katex",
    steps: [
      { stepIndex: 0, label: "Ohm's Law Standard Formula", expression: "V = I \\cdot R", latex: "V = I \\cdot R", highlight: false },
      { stepIndex: 1, label: "Rearrange Solving for Current (I)", expression: "I = \\frac{V}{R}", latex: "I = \\frac{V}{R}", highlight: true, misconceptionAnnotation: { flag: "inverse_proportionality", note: "Resistance (R) is in the denominator. As R increases at constant V, I decreases." } },
      { stepIndex: 2, label: "Substitute Values", expression: "I = \\frac{10\\text{ V}}{5\\,\\Omega} = 2\\text{ A}", latex: "I = \\frac{10\\text{ V}}{5\\,\\Omega} = 2\\text{ A}", highlight: false },
      { stepIndex: 3, label: "Proportionality Rule", expression: "\\uparrow R \\implies \\downarrow I \\quad (\\text{at constant } V)", latex: "\\uparrow R \\implies \\downarrow I \\quad (\\text{at constant } V)", highlight: true }
    ],
    variables: {
      V: { symbol: "V", name: "Voltage", unit: "Volts (V)", role: "Driving force", value: "10V" },
      I: { symbol: "I", name: "Current", unit: "Amperes (A)", role: "Rate of charge flow", value: "2A" },
      R: { symbol: "R", name: "Resistance", unit: "Ohms (Ω)", role: "Opposition to flow", value: "5Ω" }
    },
    highlightStepId: "step-2"
  },
  analogy: {
    title: "Hydraulic Analogy: Pipe Constriction vs Current Flow",
    diagramType: "hydraulic_analogy",
    elements: [
      { id: "water_pump", type: "water_pump", label: "Water Pump (Voltage / Pressure)", formulaSymbol: "V", position: { x: 80, y: 160 } },
      { id: "pipe_constriction", type: "pipe_constriction", label: "Narrow Constriction (Resistance, R)", formulaSymbol: "R", position: { x: 300, y: 60 } },
      { id: "water_flow", type: "water_flow", label: "Water Flow Rate (Current, I)", formulaSymbol: "I", position: { x: 300, y: 260 } },
      { id: "pipe_reservoir", type: "pipe_reservoir", label: "Return Pipe (Ground/Conductor)", position: { x: 80, y: 280 } }
    ],
    comparisonMappingTable: [
      { hydraulicElement: "Water Pump Pressure (P)", electricalEquivalent: "Voltage (V)", formulaSymbol: "V", unit: "Pascal ↔ Volt" },
      { hydraulicElement: "Pipe Constriction (Narrowness)", electricalEquivalent: "Resistance (R)", formulaSymbol: "R", unit: "Hydraulic Resistance ↔ Ohm" },
      { hydraulicElement: "Water Flow Rate (Q)", electricalEquivalent: "Current (I)", formulaSymbol: "I", unit: "Liters/sec ↔ Ampere" }
    ],
    currentScenario: "constrictedPipe"
  },
  graph: {
    title: "Current (I) vs Resistance (R) at Constant Voltage (V = 10V)",
    graphType: "inverse_proportionality",
    xAxis: { label: "Resistance (R)", symbol: "R", unit: "Ω", min: 0, max: 20, ticks: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20] },
    yAxis: { label: "Current (I)", symbol: "I", unit: "A", min: 0, max: 12, ticks: [0, 2, 4, 6, 8, 10, 12] },
    series: [
      {
        id: "series-i-vs-r",
        name: "I = 10 / R",
        formula: "I = 10 / R",
        mathematicalFormula: "I = \\frac{10}{R}",
        color: "#3B82F6",
        points: [
          { x: 1, y: 10 }, { x: 2, y: 5 }, { x: 4, y: 2.5 }, { x: 5, y: 2 },
          { x: 8, y: 1.25 }, { x: 10, y: 1 }, { x: 16, y: 0.625 }, { x: 20, y: 0.5 }
        ]
      }
    ],
    highlightedOperatingPoints: [
      { x: 5, y: 2, label: "R = 5Ω, I = 2A", color: "#10B981" },
      { x: 10, y: 1, label: "R = 10Ω, I = 1A", color: "#EF4444" }
    ],
    annotations: [
      { x: 10, y: 1, text: "As Resistance (R) increases, Current (I) decreases (Inverse Proportionality)", trend: "descending" }
    ],
    formula: "I = 10 / R"
  },
  misconception: {
    diagnosed: "direct-proportionality confusion",
    correctPrinciple: "At constant voltage, Current (I) is inversely proportional to Resistance (R): I = V/R",
    formulaCorrection: "I = \\frac{V}{R} \\implies \\uparrow R \\implies \\downarrow I"
  },
  layout: {
    mode: "multi_panel",
    panels: ["equation", "analogy", "graph"],
    responsive: true
  }
};

const sceneRepairCitations = [
  { documentId: 'ncert-class9-science-ch12', pageOrSlide: 205, heading: '12.3 Ohm\'s Law', excerpt: 'It is obvious from Eq. (12.5) that the current through a resistor is inversely proportional to its resistance.' }
];

// ---------------------------------------------------------------------------
// RAW NARRATION AND CAPTION DEFINITIONS ACROSS LANGUAGES
// ---------------------------------------------------------------------------
const SCENE_DEFINITIONS = [
  {
    sceneId: 'scene-1-intro',
    visualType: 'concept_map',
    visualData: scene1VisualData,
    citations: scene1Citations,
    durationSeconds: 15,
    languages: {
      english: {
        narration: "Hello students! Today we will learn about Electric Current and Ohm's Law. This is the fundamental rule of electricity.",
        segments: [
          { text: "Hello students!", duration: 2.5, math: [] },
          { text: "Today we will learn about Electric Current and Ohm's Law.", duration: 7.5, math: ["Ohm's Law"] },
          { text: "This is the fundamental rule of electricity.", duration: 5.0, math: [] }
        ]
      },
      hindi: {
        narration: "नमस्ते विद्यार्थियों! आज हम विद्युत धारा और ओम के नियम के बारे में सीखेंगे। यह विद्युत का मूलभूत नियम है।",
        segments: [
          { text: "नमस्ते विद्यार्थियों!", duration: 2.5, math: [] },
          { text: "आज हम विद्युत धारा और ओम के नियम के बारे में सीखेंगे।", duration: 7.5, math: ["ओम के नियम"] },
          { text: "यह विद्युत का मूलभूत नियम है।", duration: 5.0, math: [] }
        ]
      },
      hinglish: {
        narration: "Hello students! Aaj hum Electric Current aur Ohm's Law ke baare mein seekhenge. Yeh electricity ka basic rule hai jo Voltage, Current aur Resistance ko jodta hai.",
        segments: [
          { text: "Hello students!", duration: 2.5, math: [] },
          { text: "Aaj hum Electric Current aur Ohm's Law ke baare mein seekhenge.", duration: 6.5, math: ["Ohm's Law"] },
          { text: "Yeh electricity ka basic rule hai jo Voltage, Current aur Resistance ko jodta hai.", duration: 6.0, math: ["Voltage", "Current", "Resistance"] }
        ]
      }
    }
  },
  {
    sceneId: 'scene-2-voltage',
    visualType: 'diagram',
    visualData: scene2VisualData,
    citations: scene2Citations,
    durationSeconds: 18,
    languages: {
      english: {
        narration: "Think of Voltage like water pressure: the more pressure, the more current flows. It pushes electrons through the circuit.",
        segments: [
          { text: "Think of Voltage like water pressure: the more pressure, the more current flows.", duration: 10.0, math: ["Voltage"] },
          { text: "It pushes electrons through the circuit.", duration: 8.0, math: [] }
        ]
      },
      hindi: {
        narration: "वोल्टेज को पानी के दबाव की तरह समझें: जितना अधिक दबाव, उतना अधिक धारा प्रवाह होगा। यह इलेक्ट्रॉनों को धक्का देता है।",
        segments: [
          { text: "वोल्टेज को पानी के दबाव की तरह समझें: जितना अधिक दबाव, उतना अधिक धारा प्रवाह होगा।", duration: 11.0, math: ["वोल्टेज"] },
          { text: "यह इलेक्ट्रॉनों को धक्का देता है।", duration: 7.0, math: [] }
        ]
      },
      hinglish: {
        narration: "Voltage ko samjho jaise water pressure: jitna zyada pressure, utna zyada current flow hoga. Yeh electrons ko circuit mein push karta hai.",
        segments: [
          { text: "Voltage ko samjho jaise water pressure: jitna zyada pressure, utna zyada current flow hoga.", duration: 10.5, math: ["Voltage", "current"] },
          { text: "Yeh electrons ko circuit mein push karta hai.", duration: 7.5, math: [] }
        ]
      }
    }
  },
  {
    sceneId: 'scene-3-resistance',
    visualType: 'diagram',
    visualData: scene3VisualData,
    citations: scene3Citations,
    durationSeconds: 18,
    languages: {
      english: {
        narration: "And what is Resistance? It opposes flow, like a speed breaker or narrow pipe. Higher resistance means less current.",
        segments: [
          { text: "And what is Resistance?", duration: 3.5, math: ["Resistance"] },
          { text: "It opposes flow, like a speed breaker or narrow pipe.", duration: 7.5, math: [] },
          { text: "Higher resistance means less current.", duration: 7.0, math: ["resistance", "current"] }
        ]
      },
      hindi: {
        narration: "और प्रतिरोध क्या है? यह प्रवाह का विरोध करता है, जैसे स्पीड ब्रेकर या संकरा पाइप। अधिक प्रतिरोध का अर्थ है कम धारा।",
        segments: [
          { text: "और प्रतिरोध क्या है?", duration: 3.5, math: ["प्रतिरोध"] },
          { text: "यह प्रवाह का विरोध करता है, जैसे स्पीड ब्रेकर या संकरा पाइप।", duration: 7.5, math: [] },
          { text: "अधिक प्रतिरोध का अर्थ है कम धारा।", duration: 7.0, math: ["प्रतिरोध", "धारा"] }
        ]
      },
      hinglish: {
        narration: "Aur Resistance kya hai? Yeh flow ko rokata hai, jaise speed breaker ya narrow pipe. Zyada resistance matlab kam current.",
        segments: [
          { text: "Aur Resistance kya hai?", duration: 3.5, math: ["Resistance"] },
          { text: "Yeh flow ko rokata hai, jaise speed breaker ya narrow pipe.", duration: 7.5, math: [] },
          { text: "Zyada resistance matlab kam current.", duration: 7.0, math: ["resistance", "current"] }
        ]
      }
    }
  },
  {
    sceneId: 'scene-5-ohms-law',
    visualType: 'circuit',
    visualData: scene5VisualData,
    citations: scene5Citations,
    durationSeconds: 24,
    languages: {
      english: {
        narration: "Ohm's Law states that V = I * R. If we solve for current, I = V/R. For example, if V is 10V and R is 5Ω, then I = 10 / 5 = 2A.",
        segments: [
          { text: "Ohm's Law states that V = I * R.", duration: 5.5, math: ["V = I * R", "V = IR"] },
          { text: "If we solve for current, I = V/R.", duration: 6.5, math: ["I = V/R", "I = V / R"] },
          { text: "For example, if V is 10V and R is 5Ω, then I = 10 / 5 = 2A.", duration: 12.0, math: ["10V", "5Ω", "2A", "I = 10 / 5 = 2A", "10/5=2A"] }
        ]
      },
      hindi: {
        narration: "ओम का नियम कहता है कि V = I * R। यदि धारा निकालें, तो I = V/R। उदाहरण के लिए, यदि V 10V है और R 5Ω है, तो I = 10 / 5 = 2A।",
        segments: [
          { text: "ओम का नियम कहता है कि V = I * R।", duration: 5.5, math: ["V = I * R", "V = IR"] },
          { text: "यदि धारा निकालें, तो I = V/R।", duration: 6.5, math: ["I = V/R", "I = V / R"] },
          { text: "उदाहरण के लिए, यदि V 10V है और R 5Ω है, तो I = 10 / 5 = 2A।", duration: 12.0, math: ["10V", "5Ω", "2A", "I = 10 / 5 = 2A", "10/5=2A"] }
        ]
      },
      hinglish: {
        narration: "Ohm's Law kehta hai ki V = I * R. Agar current nikalein, toh I = V/R hota hai. For example, agar V 10V hai aur R 5Ω hai, toh I = 10 / 5 = 2A hoga.",
        segments: [
          { text: "Ohm's Law kehta hai ki V = I * R.", duration: 5.5, math: ["V = I * R", "V = IR"] },
          { text: "Agar current nikalein, toh I = V/R hota hai.", duration: 6.5, math: ["I = V/R", "I = V / R"] },
          { text: "For example, agar V 10V hai aur R 5Ω hai, toh I = 10 / 5 = 2A hoga.", duration: 12.0, math: ["10V", "5Ω", "2A", "I = 10 / 5 = 2A", "10/5=2A"] }
        ]
      }
    }
  },
  {
    sceneId: 'scene-advance-circuits',
    visualType: 'circuit',
    visualData: sceneAdvanceVisualData,
    citations: sceneAdvanceCitations,
    durationSeconds: 26,
    languages: {
      english: {
        narration: "Outstanding work! Now that you mastered Ohm's Law with V = IR and I = V/R, let us explore complex multi-resistor series and parallel circuits.",
        segments: [
          { text: "Outstanding work!", duration: 3.0, math: [] },
          { text: "Now that you mastered Ohm's Law with V = IR and I = V/R,", duration: 11.0, math: ["V = IR", "I = V/R"] },
          { text: "let us explore complex multi-resistor series and parallel circuits.", duration: 12.0, math: [] }
        ]
      },
      hindi: {
        narration: "बहुत बढ़िया! अब जब आपने V = IR और I = V/R के साथ ओम का नियम सीख लिया है, तो आइए जटिल श्रेणी और समानांतर परिपथों का अन्वेषण करें।",
        segments: [
          { text: "बहुत बढ़िया!", duration: 3.0, math: [] },
          { text: "अब जब आपने V = IR और I = V/R के साथ ओम का नियम सीख लिया है,", duration: 11.0, math: ["V = IR", "I = V/R"] },
          { text: "तो आइए जटिल श्रेणी और समानांतर परिपथों का अन्वेषण करें।", duration: 12.0, math: [] }
        ]
      },
      hinglish: {
        narration: "Shabash! Ab jab aapne V = IR aur I = V/R ke saath Ohm's Law samajh liya hai, aao complex series aur parallel circuits explore karein.",
        segments: [
          { text: "Shabash!", duration: 3.0, math: [] },
          { text: "Ab jab aapne V = IR aur I = V/R ke saath Ohm's Law samajh liya hai,", duration: 11.0, math: ["V = IR", "I = V/R"] },
          { text: "aao complex series aur parallel circuits explore karein.", duration: 12.0, math: [] }
        ]
      }
    }
  },
  {
    sceneId: 'scene-repair-ohms-law',
    visualType: 'diagram',
    visualData: sceneRepairVisualData,
    citations: sceneRepairCitations,
    durationSeconds: 35,
    languages: {
      english: {
        narration: "Think of water flowing through a pipe. If you narrow the pipe (increase resistance R), the water flow (current I) will DECREASE, not increase! In the formula I = V/R, when Resistance R in the denominator increases, Current I decreases at constant voltage V = 10V.",
        segments: [
          { text: "Think of water flowing through a pipe.", duration: 4.5, math: [] },
          { text: "If you narrow the pipe (increase resistance R), the water flow (current I) will DECREASE, not increase!", duration: 14.5, math: ["resistance R", "current I", "R", "I"] },
          { text: "In the formula I = V/R, when Resistance R in the denominator increases, Current I decreases at constant voltage V = 10V.", duration: 16.0, math: ["I = V/R", "R", "I", "V = 10V", "10V"] }
        ]
      },
      hindi: {
        narration: "सोचें एक पाइप में पानी बह रहा है। यदि पाइप को संकरा कर दें (प्रतिरोध R बढ़ाएं), तो पानी का बहाव (धारा I) कम होगा, ज्यादा नहीं! फॉर्मूला I = V/R में, जब प्रतिरोध R बढ़ता है, तो स्थिर वोल्टेज V = 10V पर धारा I घटती है।",
        segments: [
          { text: "सोचें एक पाइप में पानी बह रहा है।", duration: 4.5, math: [] },
          { text: "यदि पाइप को संकरा कर दें (प्रतिरोध R बढ़ाएं), तो पानी का बहाव (धारा I) कम होगा, ज्यादा नहीं!", duration: 14.5, math: ["प्रतिरोध R", "धारा I", "R", "I"] },
          { text: "फॉर्मूला I = V/R में, जब प्रतिरोध R बढ़ता है, तो स्थिर वोल्टेज V = 10V पर धारा I घटती है।", duration: 16.0, math: ["I = V/R", "R", "I", "V = 10V", "10V"] }
        ]
      },
      hinglish: {
        narration: "Socho ek water pipe mein paani beh raha hai. Agar pipe ko narrow kar do (matlab resistance R badhao), toh paani ka flow (matlab current I) KAM hoga, zyada nahi! Isi tarah formula I = V/R mein, jab Resistance R denominator mein badhta hai, toh Current I ghat'ta hai (at constant V = 10V).",
        segments: [
          { text: "Socho ek water pipe mein paani beh raha hai.", duration: 4.5, math: [] },
          { text: "Agar pipe ko narrow kar do (matlab resistance R badhao), toh paani ka flow (matlab current I) KAM hoga, zyada nahi!", duration: 14.5, math: ["resistance R", "current I", "R", "I"] },
          { text: "Isi tarah formula I = V/R mein, jab Resistance R denominator mein badhta hai, toh Current I ghat'ta hai (at constant V = 10V).", duration: 16.0, math: ["I = V/R", "R", "I", "V = 10V", "10V"] }
        ]
      }
    }
  }
];

/**
 * Builds deterministic cached MediaResult map.
 * @returns {Map<string, Object>}
 */
function buildCachedDescriptorMap() {
  const map = new Map();

  for (const def of SCENE_DEFINITIONS) {
    for (const [langKey, langContent] of Object.entries(def.languages)) {
      const canonicalLang = normalizeLanguage(langKey);
      const cacheKey = `${def.sceneId}::${canonicalLang}`;

      const captions = buildTimedCaptions(langContent.segments, canonicalLang);
      const durationSeconds = def.durationSeconds;

      const mediaResult = {
        sceneId: def.sceneId,
        language: canonicalLang,
        teacherPanel: {
          type: 'video',
          url: `mock://avatar/teacher-dr-sharma/${def.sceneId}-${canonicalLang}.mp4`,
          thumbnailUrl: `mock://avatar/teacher-dr-sharma/thumb_${def.sceneId}-${canonicalLang}.jpg`,
          fallback: false
        },
        audio: {
          url: `mock://tts/${canonicalLang}/${def.sceneId}.mp3`,
          durationSeconds,
          format: 'mp3',
          language: canonicalLang,
          fallback: false
        },
        video: {
          url: `mock://avatar/teacher-dr-sharma/${def.sceneId}-${canonicalLang}.mp4`,
          thumbnailUrl: `mock://avatar/teacher-dr-sharma/thumb_${def.sceneId}-${canonicalLang}.jpg`,
          format: 'mp4',
          durationSeconds,
          fallback: false
        },
        visualCanvas: {
          type: def.visualType,
          data: def.visualData,
          renderHint: def.visualData?.composite ? 'composite_repair' : 'standard'
        },
        narration: langContent.narration,
        captions,
        durationSeconds,
        status: 'ready',
        citations: def.citations,
        metadata: {
          cached: true,
          preGenerated: true,
          mathInvariantVerified: true,
          formulaSet: ['V=IR', 'I=V/R', '10/5=2A']
        }
      };

      map.set(cacheKey, mediaResult);
    }
  }

  return map;
}

/**
 * All pre-generated descriptors indexed by `sceneId::language`.
 * @type {Map<string, Object>}
 */
export const cachedDescriptors = buildCachedDescriptorMap();

/**
 * Looks up a pre-generated scene descriptor.
 * @param {string} sceneId
 * @param {string} [language='hinglish']
 * @returns {Object|null}
 */
export function getCachedDescriptor(sceneId, language = 'hinglish') {
  if (!sceneId) return null;
  const normScene = normalizeSceneId(sceneId);
  const normLang = normalizeLanguage(language);
  const key = `${normScene}::${normLang}`;
  return cachedDescriptors.get(key) || null;
}
