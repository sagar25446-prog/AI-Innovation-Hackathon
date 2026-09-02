import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  getRenderHint,
  getSupportedVisualTypes,
  getThemeConfig,
  getRecommendedLibrary
} from '../src/render-hints.js';

describe('render-hints suite', () => {
  describe('getRenderHint', () => {
    test('returns KaTeX hints for equation visual specifications', () => {
      const hint = getRenderHint({ type: 'equation', data: { steps: [] } });
      assert.equal(hint.library, 'katex');
      assert.equal(hint.component, 'MathEquationViewer');
      assert.equal(hint.animation, 'fade-in-steps');
      assert.ok(hint.katexOptions);
      assert.equal(hint.katexOptions.displayMode, true);
      assert.ok(Array.isArray(hint.capabilities));
      assert.ok(hint.responsive);
    });

    test('returns SVG hints for circuit visual specifications', () => {
      const hint = getRenderHint({ type: 'circuit', data: { viewBox: '0 0 580 400' } });
      assert.equal(hint.library, 'svg');
      assert.equal(hint.component, 'CircuitViewer');
      assert.equal(hint.animation, 'draw-paths');
      assert.equal(hint.viewBox, '0 0 580 400');
      assert.ok(hint.particleAnimation);
      assert.equal(hint.particleAnimation.enabled, true);
    });

    test('returns Chart.js hints for graph visual specifications', () => {
      const hint = getRenderHint({ type: 'graph', data: {} });
      assert.equal(hint.library, 'chartjs');
      assert.equal(hint.component, 'CartesianGraphViewer');
      assert.equal(hint.animation, 'draw-series');
      assert.equal(hint.chartType, 'scatter-line');
      assert.ok(hint.capabilities.includes('hover_point_tooltip'));
    });

    test('returns D3 hints for concept map visual specifications', () => {
      const hint = getRenderHint({ type: 'concept_map', data: {} });
      assert.equal(hint.library, 'd3');
      assert.equal(hint.component, 'ConceptMapViewer');
      assert.equal(hint.animation, 'node-reveal');
      assert.equal(hint.layoutEngine, 'force-directed');
    });

    test('distinguishes hydraulic analogy diagram hints', () => {
      const hint = getRenderHint({
        type: 'diagram',
        data: { diagramType: 'hydraulic_analogy' }
      });
      assert.equal(hint.library, 'svg');
      assert.equal(hint.component, 'HydraulicAnalogyViewer');
      assert.equal(hint.animation, 'flow-simulation');
      assert.ok(hint.capabilities.includes('toggle_pipe_constriction'));
    });

    test('distinguishes composite 3-in-1 repair diagram hints', () => {
      const hint = getRenderHint({
        type: 'diagram',
        data: { composite: true, diagramType: 'compound_repair' }
      });
      assert.equal(hint.library, 'composite');
      assert.equal(hint.component, 'CompositeRepairViewer');
      assert.equal(hint.animation, 'staggered-reveal');
      assert.equal(hint.layout, 'multi_panel');
      assert.equal(hint.subRenderers.equation, 'katex');
      assert.equal(hint.subRenderers.analogy, 'svg');
      assert.equal(hint.subRenderers.graph, 'chartjs');
    });

    test('handles timeline and code_trace visual types', () => {
      const timelineHint = getRenderHint({ type: 'timeline', data: {} });
      assert.equal(timelineHint.library, 'd3');
      assert.equal(timelineHint.component, 'TimelineViewer');

      const codeTraceHint = getRenderHint({ type: 'code_trace', data: {} });
      assert.equal(codeTraceHint.library, 'prism');
      assert.equal(codeTraceHint.component, 'CodeTraceViewer');
    });

    test('applies theme palettes correctly (dark, light, high-contrast)', () => {
      const darkHint = getRenderHint({ type: 'circuit', data: {} }, { theme: 'dark' });
      assert.equal(darkHint.theme, 'dark');
      assert.equal(darkHint.palette.background, '#0F172A');

      const lightHint = getRenderHint({ type: 'circuit', data: {} }, { theme: 'light' });
      assert.equal(lightHint.theme, 'light');
      assert.equal(lightHint.palette.background, '#FFFFFF');

      const hcHint = getRenderHint({ type: 'circuit', data: {} }, { theme: 'high-contrast' });
      assert.equal(hcHint.theme, 'high-contrast');
      assert.equal(hcHint.palette.background, '#000000');
    });

    test('handles invalid or empty spec gracefully', () => {
      const errorHint = getRenderHint(null);
      assert.ok(errorHint.error);
      assert.equal(errorHint.library, 'html');
    });
  });

  describe('helper utilities', () => {
    test('getSupportedVisualTypes returns all 7 supported types', () => {
      const types = getSupportedVisualTypes();
      assert.ok(Array.isArray(types));
      assert.ok(types.includes('circuit'));
      assert.ok(types.includes('equation'));
      assert.ok(types.includes('graph'));
      assert.ok(types.includes('concept_map'));
      assert.ok(types.includes('diagram'));
      assert.ok(types.includes('timeline'));
      assert.ok(types.includes('code_trace'));
    });

    test('getThemeConfig returns palette for requested theme', () => {
      const dark = getThemeConfig('dark');
      assert.equal(dark.name, 'dark');
      assert.ok(dark.primary);

      const fallback = getThemeConfig('unknown-theme');
      assert.equal(fallback.name, 'dark');
    });

    test('getRecommendedLibrary returns correct library for type', () => {
      assert.equal(getRecommendedLibrary('equation'), 'katex');
      assert.equal(getRecommendedLibrary('circuit'), 'svg');
      assert.equal(getRecommendedLibrary('graph'), 'chartjs');
      assert.equal(getRecommendedLibrary('concept_map'), 'd3');
      assert.equal(getRecommendedLibrary('code_trace'), 'prism');
    });
  });
});
