import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  createCircuitSpec,
  createEquationSpec,
  createGraphSpec,
  createConceptMapSpec,
  createWaterPipeAnalogySpec,
  createRepairVisualSpec
} from '../src/visual-specs.js';

describe('visual-specs generator suite', () => {
  describe('createCircuitSpec', () => {
    test('creates default circuit specification with rich structure', () => {
      const spec = createCircuitSpec();
      assert.equal(spec.type, 'circuit');
      assert.ok(spec.data);
      assert.ok(Array.isArray(spec.data.components));
      assert.ok(Array.isArray(spec.data.connections));
      assert.ok(spec.data.currentFlow);
      assert.ok(spec.data.layout);
      assert.ok(spec.data.dimensions);
      assert.ok(spec.data.viewBox);
      assert.ok(Array.isArray(spec.data.annotations));

      // Check default components
      const compTypes = spec.data.components.map(c => c.type);
      assert.ok(compTypes.includes('battery'));
      assert.ok(compTypes.includes('resistor'));
      assert.ok(compTypes.includes('ammeter'));
      assert.ok(compTypes.includes('switch'));

      // Check battery structure
      const bat = spec.data.components.find(c => c.type === 'battery');
      assert.equal(bat.id, 'bat-1');
      assert.equal(bat.value, 10);
      assert.equal(bat.unit, 'V');
      assert.ok(bat.position && typeof bat.position.x === 'number');
      assert.ok(bat.coordinates && typeof bat.coordinates.width === 'number');
      assert.ok(bat.terminals && bat.terminals.positive && bat.terminals.negative);
      assert.ok(Array.isArray(bat.ports));

      // Check resistor structure
      const res = spec.data.components.find(c => c.type === 'resistor');
      assert.equal(res.id, 'res-1');
      assert.equal(res.value, 5);
      assert.equal(res.unit, 'Ω');
      assert.ok(res.terminals && res.terminals.terminal_a);

      // Check ammeter structure
      const amm = spec.data.components.find(c => c.type === 'ammeter');
      assert.equal(amm.id, 'amm-1');
      assert.equal(amm.value, 2);
      assert.equal(amm.unit, 'A');

      // Check connections
      assert.ok(spec.data.connections.length >= 4);
      for (const conn of spec.data.connections) {
        assert.ok(conn.id);
        assert.ok(conn.fromComponent);
        assert.ok(conn.toComponent);
        assert.ok(conn.fromPort);
        assert.ok(conn.toPort);
        assert.ok(Array.isArray(conn.waypoints));
        assert.ok(typeof conn.path === 'string');
      }

      // Check current flow
      assert.equal(spec.data.currentFlow.direction, 'clockwise');
      assert.equal(spec.data.currentFlow.active, true);
      assert.ok(Array.isArray(spec.data.currentFlow.path));
    });

    test('supports custom voltage, resistance, and bulb inclusion', () => {
      const spec = createCircuitSpec({
        voltage: '24V',
        resistance: '8Ω',
        highlight: 'resistor',
        includeBulb: true,
        switchState: 'open'
      });

      assert.equal(spec.type, 'circuit');
      const bat = spec.data.components.find(c => c.type === 'battery');
      assert.equal(bat.value, 24);
      assert.equal(bat.label, 'V = 24V');

      const res = spec.data.components.find(c => c.type === 'resistor');
      assert.equal(res.value, 8);
      assert.equal(res.label, 'R = 8Ω');

      const bulb = spec.data.components.find(c => c.type === 'bulb');
      assert.ok(bulb);
      assert.equal(bulb.state, 'off');

      assert.equal(spec.data.currentFlow.active, false);
      assert.equal(spec.data.highlight, 'resistor');
    });

    test('accepts custom components array directly', () => {
      const customComps = [
        { id: 'c1', type: 'battery', label: '12V', position: { x: 10, y: 10 } },
        { id: 'c2', type: 'resistor', label: '4Ω', position: { x: 100, y: 10 } }
      ];
      const spec = createCircuitSpec(customComps, { title: 'Custom Circuit' });
      assert.equal(spec.data.title, 'Custom Circuit');
      assert.equal(spec.data.components.length, 2);
      assert.equal(spec.data.components[0].id, 'c1');
    });
  });

  describe('createEquationSpec', () => {
    test('creates default KaTeX-compatible equation specification', () => {
      const spec = createEquationSpec();
      assert.equal(spec.type, 'equation');
      assert.equal(spec.data.format, 'katex');
      assert.ok(Array.isArray(spec.data.steps));
      assert.ok(spec.data.steps.length >= 3);

      // Check step 1 (V = IR)
      const step1 = spec.data.steps[0];
      assert.equal(step1.stepIndex, 0);
      assert.equal(step1.id, 'step-1');
      assert.ok(step1.expression.includes('V') && step1.expression.includes('\\cdot'));
      assert.equal(step1.latex, step1.expression);
      assert.ok(step1.title);
      assert.ok(step1.explanation);

      // Check step 2 (I = V/R)
      const step2 = spec.data.steps[1];
      assert.equal(step2.stepIndex, 1);
      assert.equal(step2.id, 'step-2');
      assert.ok(step2.expression.includes('\\frac{V}{R}'));
      assert.ok(step2.misconceptionAnnotation);
      assert.equal(step2.misconceptionAnnotation.flag, 'inverse_proportionality');

      // Check step 3 (Substitution)
      const step3 = spec.data.steps[2];
      assert.equal(step3.stepIndex, 2);
      assert.equal(step3.id, 'step-3');
      assert.ok(step3.expression.includes('10\\text{ V}'));
      assert.ok(step3.expression.includes('5\\,\\Omega'));
      assert.ok(step3.expression.includes('2\\text{ A}'));

      // Check variable annotations
      assert.ok(spec.data.variables);
      assert.ok(spec.data.variables.V);
      assert.ok(spec.data.variables.I);
      assert.ok(spec.data.variables.R);
      assert.equal(spec.data.variables.V.unit, 'Volts (V)');
      assert.equal(spec.data.variables.I.unit, 'Amperes (A)');
      assert.equal(spec.data.variables.R.unit, 'Ohms (Ω)');

      // Check misconception annotations
      assert.ok(spec.data.misconceptionAnnotations);
      assert.equal(spec.data.misconceptionAnnotations.topic, 'direct_vs_inverse_proportionality');
    });

    test('supports misconception_repair mode with inverse rule step', () => {
      const spec = createEquationSpec({
        voltage: 12,
        resistance: 4,
        mode: 'misconception_repair'
      });

      assert.ok(spec.data.steps.length >= 4);
      const step4 = spec.data.steps[3];
      assert.ok(step4.expression.includes('\\uparrow R \\implies \\downarrow I'));
      assert.ok(step4.misconceptionAnnotation);
      assert.equal(step4.misconceptionAnnotation.flag, 'direct_vs_inverse_proportionality');
    });

    test('accepts custom step strings and normalizes them', () => {
      const customSteps = ['V = I * R', 'I = V / R'];
      const spec = createEquationSpec(customSteps);
      assert.equal(spec.data.steps.length, 2);
      assert.equal(spec.data.steps[0].stepIndex, 0);
      assert.ok(spec.data.steps[0].expression.includes('\\cdot'));
    });
  });

  describe('createGraphSpec', () => {
    test('creates Cartesian graph spec with mathematically accurate data points', () => {
      const voltage = 10;
      const spec = createGraphSpec({ voltage });

      assert.equal(spec.type, 'graph');
      assert.equal(spec.data.graphType, 'inverse_proportionality');
      assert.ok(spec.data.xAxis);
      assert.ok(spec.data.yAxis);
      assert.ok(spec.data.gridlines);
      assert.ok(Array.isArray(spec.data.series));
      assert.ok(Array.isArray(spec.data.points));

      // Verify mathematical correctness for every coordinate point: y = V / x
      const points = spec.data.points;
      assert.ok(points.length >= 10, 'Graph should have at least 10 sample points');

      for (const pt of points) {
        assert.ok(typeof pt.x === 'number');
        assert.ok(typeof pt.y === 'number');
        const expectedY = voltage / pt.x;
        assert.ok(
          Math.abs(pt.y - expectedY) < 0.005,
          `Point (${pt.x}, ${pt.y}) does not match formula y = ${voltage} / ${pt.x} (expected ${expectedY})`
        );
      }

      // Check axis properties
      assert.equal(spec.data.xAxis.unit, 'Ω');
      assert.equal(spec.data.xAxis.min, 0);
      assert.ok(spec.data.xAxis.max >= 20);
      assert.ok(Array.isArray(spec.data.xAxis.ticks));

      assert.equal(spec.data.yAxis.unit, 'A');
      assert.equal(spec.data.yAxis.min, 0);
      assert.ok(Array.isArray(spec.data.yAxis.ticks));

      // Check highlighted operating points
      assert.ok(Array.isArray(spec.data.highlightedOperatingPoints));
      const r5Point = spec.data.highlightedOperatingPoints.find(p => p.x === 5);
      assert.ok(r5Point);
      assert.equal(r5Point.y, 2);

      const r10Point = spec.data.highlightedOperatingPoints.find(p => p.x === 10);
      assert.ok(r10Point);
      assert.equal(r10Point.y, 1);

      // Check annotations
      assert.ok(Array.isArray(spec.data.annotations));
      assert.equal(spec.data.annotations[0].trend, 'descending');
    });

    test('recalculates points when custom voltage is provided', () => {
      const spec = createGraphSpec({ voltage: 24 });
      const pt4 = spec.data.points.find(p => p.x === 4);
      assert.ok(pt4);
      assert.equal(pt4.y, 6); // 24 / 4 = 6
    });
  });

  describe('createConceptMapSpec', () => {
    test('creates hierarchical concept map specification', () => {
      const spec = createConceptMapSpec();
      assert.equal(spec.type, 'concept_map');
      assert.ok(spec.data.layout);
      assert.equal(spec.data.layout.type, 'hierarchical');
      assert.ok(Array.isArray(spec.data.nodes));
      assert.ok(Array.isArray(spec.data.edges));

      // Verify node properties
      const nodeIds = spec.data.nodes.map(n => n.id);
      assert.ok(nodeIds.includes('v'));
      assert.ok(nodeIds.includes('i'));
      assert.ok(nodeIds.includes('r'));
      assert.ok(nodeIds.includes('ohm'));

      for (const node of spec.data.nodes) {
        assert.ok(node.id);
        assert.ok(node.label);
        assert.ok(node.category);
        assert.ok(node.type);
        assert.ok(node.description);
        assert.ok(node.position && typeof node.position.x === 'number');
        assert.ok(node.coordinates && typeof node.coordinates.x === 'number');
        assert.ok(typeof node.level === 'number');
        assert.ok(node.style && node.style.fill);
      }

      // Verify edges
      for (const edge of spec.data.edges) {
        assert.ok(edge.id);
        assert.ok(edge.from);
        assert.ok(edge.to);
        assert.ok(edge.relationType);
        assert.ok(edge.label);
        assert.equal(edge.directional, true);
      }
    });

    test('accepts custom nodes and edges', () => {
      const customNodes = [{ id: 'n1', label: 'Charge', position: { x: 50, y: 50 } }];
      const customEdges = [{ id: 'e1', from: 'n1', to: 'n1', label: 'self' }];
      const spec = createConceptMapSpec(customNodes, customEdges, { title: 'Custom Map' });
      assert.equal(spec.data.title, 'Custom Map');
      assert.equal(spec.data.nodes.length, 1);
      assert.equal(spec.data.edges.length, 1);
    });
  });

  describe('createWaterPipeAnalogySpec', () => {
    test('creates hydraulic analogy diagram specification', () => {
      const spec = createWaterPipeAnalogySpec();
      assert.equal(spec.type, 'diagram');
      assert.equal(spec.data.diagramType, 'hydraulic_analogy');
      assert.ok(Array.isArray(spec.data.elements));
      assert.ok(spec.data.coordinateBounds);
      assert.ok(spec.data.flowParticles);
      assert.ok(spec.data.velocityVector);
      assert.ok(Array.isArray(spec.data.comparisonMappingTable));
      assert.ok(spec.data.scenarioStates);
      assert.ok(Array.isArray(spec.data.annotations));

      // Check key hydraulic elements
      const elementTypes = spec.data.elements.map(e => e.type);
      assert.ok(elementTypes.includes('water_pump'));
      assert.ok(elementTypes.includes('pipe_constriction'));
      assert.ok(elementTypes.includes('water_flow'));

      const pump = spec.data.elements.find(e => e.type === 'water_pump');
      assert.equal(pump.electricalEquivalent, 'Battery / Voltage Source (V)');
      assert.equal(pump.formulaSymbol, 'V');

      const constriction = spec.data.elements.find(e => e.type === 'pipe_constriction');
      assert.equal(constriction.electricalEquivalent, 'Resistor (R)');
      assert.equal(constriction.formulaSymbol, 'R');

      const flow = spec.data.elements.find(e => e.type === 'water_flow');
      assert.equal(flow.electricalEquivalent, 'Current (I)');
      assert.equal(flow.formulaSymbol, 'I');

      // Check mapping table
      assert.ok(spec.data.comparisonMappingTable.length >= 3);
      for (const map of spec.data.comparisonMappingTable) {
        assert.ok(map.hydraulicElement);
        assert.ok(map.electricalEquivalent);
        assert.ok(map.formulaSymbol);
        assert.ok(map.concept);
      }

      // Check scenario states
      assert.ok(spec.data.scenarioStates.widePipe);
      assert.ok(spec.data.scenarioStates.constrictedPipe);
      assert.equal(spec.data.currentScenario, 'constrictedPipe');
    });
  });

  describe('createRepairVisualSpec', () => {
    test('creates compound 3-in-1 repair visual specification', () => {
      const spec = createRepairVisualSpec({ voltage: 10 });
      assert.equal(spec.type, 'diagram');
      assert.equal(spec.data.composite, true);
      assert.equal(spec.data.diagramType, 'compound_repair');

      // Part (a): Equation transformation
      assert.ok(spec.data.equation);
      assert.equal(spec.data.equation.format, 'katex');
      assert.ok(Array.isArray(spec.data.equation.steps));
      assert.ok(spec.data.equation.steps.length >= 3);

      // Part (b): Water-pipe analogy diagram
      assert.ok(spec.data.analogy);
      assert.equal(spec.data.analogy.diagramType, 'hydraulic_analogy');
      assert.ok(Array.isArray(spec.data.analogy.elements));
      assert.ok(spec.data.analogy.comparisonMappingTable);

      // Part (c): Descending I vs R graph
      assert.ok(spec.data.graph);
      assert.equal(spec.data.graph.graphType, 'inverse_proportionality');
      assert.ok(Array.isArray(spec.data.graph.points));
      assert.ok(spec.data.graph.points.length >= 10);

      // Misconception diagnostic details
      assert.ok(spec.data.misconception);
      assert.equal(spec.data.misconception.diagnosed, 'direct-proportionality confusion');
      assert.ok(spec.data.misconception.correctPrinciple.includes('I = V/R'));

      // Layout mode
      assert.equal(spec.data.layout.mode, 'multi_panel');
      assert.deepEqual(spec.data.layout.panels, ['equation', 'analogy', 'graph']);
    });
  });
});
