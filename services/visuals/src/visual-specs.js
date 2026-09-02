/**
 * Visual specification templates for GuruFlow.
 * @module visual-specs
 */

/**
 * Creates a circuit diagram visual specification.
 * @param {Object} options - Configuration options.
 * @param {string} [options.voltage='10V'] - Voltage value.
 * @param {string} [options.resistance='5Ω'] - Resistance value.
 * @param {string} [options.highlight] - Component to highlight (e.g., 'ammeter').
 * @returns {Object} The circuit visual specification.
 */
export function createCircuitSpec(options = {}) {
  const { voltage = '10V', resistance = '5Ω', highlight = 'ammeter' } = options;
  return {
    type: 'circuit',
    data: {
      components: [
        { type: 'battery', label: `V = ${voltage}` },
        { type: 'resistor', label: `R = ${resistance}` },
        { type: 'ammeter', label: 'I = ?' }
      ],
      connections: [
        { from: 'battery', to: 'resistor' },
        { from: 'resistor', to: 'ammeter' },
        { from: 'ammeter', to: 'battery' }
      ],
      annotations: ['Current flows from + to -'],
      highlight
    }
  };
}

/**
 * Creates an equation transformation specification.
 * @param {Object} options - Configuration options.
 * @param {string} [options.highlight='result'] - Step to highlight.
 * @returns {Object} The equation visual specification.
 */
export function createEquationSpec(options = {}) {
  const { highlight = 'result' } = options;
  return {
    type: 'equation',
    data: {
      steps: [
        { expression: 'V = IR', label: "Ohm's Law" },
        { expression: 'I = V/R', label: 'Solve for current' },
        { expression: 'I = 10/5 = 2A', label: 'Substitute values' }
      ],
      format: 'katex',
      highlight
    }
  };
}

/**
 * Creates a graph specification showing I vs R at constant V.
 * @param {Object} options - Configuration options.
 * @param {number} [options.voltage=10] - Constant voltage value.
 * @returns {Object} The graph visual specification.
 */
export function createGraphSpec(options = {}) {
  const { voltage = 10 } = options;
  return {
    type: 'graph',
    data: {
      xAxis: { label: 'Resistance (Ω)', min: 1, max: 20 },
      yAxis: { label: 'Current (A)', min: 0, max: 10 },
      series: [
        {
          name: `I = V/R (V=${voltage}V)`,
          points: [
            { x: 1, y: voltage / 1 },
            { x: 2, y: voltage / 2 },
            { x: 5, y: voltage / 5 },
            { x: 10, y: voltage / 10 }
          ],
          type: 'curve'
        }
      ],
      annotations: [
        { text: 'As R increases, I decreases', position: 'top-right' }
      ],
      title: `Current vs Resistance at V = ${voltage}V`
    }
  };
}

/**
 * Creates a concept map specification for Ohm's Law.
 * @param {Object} [options] - Configuration options (unused for now, but kept for consistency).
 * @returns {Object} The concept map visual specification.
 */
export function createConceptMapSpec(options = {}) {
  return {
    type: 'concept_map',
    data: {
      nodes: [
        { id: 'v', label: 'Voltage (V)', type: 'concept' },
        { id: 'i', label: 'Current (I)', type: 'concept' },
        { id: 'r', label: 'Resistance (R)', type: 'concept' },
        { id: 'ohm', label: "Ohm's Law (V=IR)", type: 'formula' }
      ],
      edges: [
        { from: 'ohm', to: 'v', label: 'defines' },
        { from: 'ohm', to: 'i', label: 'defines' },
        { from: 'ohm', to: 'r', label: 'defines' },
        { from: 'v', to: 'i', label: 'causes' },
        { from: 'r', to: 'i', label: 'opposes' }
      ],
      layout: 'hierarchical'
    }
  };
}

/**
 * Creates a water pipe analogy specification for Ohm's Law.
 * @param {Object} [options] - Configuration options.
 * @returns {Object} The diagram visual specification.
 */
export function createWaterPipeAnalogySpec(options = {}) {
  return {
    type: 'diagram',
    data: {
      elements: [
        { type: 'pipe', label: 'Pipe width (Resistance, R)' },
        { type: 'pump', label: 'Water pressure (Voltage, V)' },
        { type: 'flow', label: 'Flow rate (Current, I)' }
      ],
      description: 'Water pipe analogy for Ohm\'s Law: Pressure drives flow, but narrower pipes restrict it.'
    }
  };
}
