/**
 * Render hint generators and UI component configuration for visual specifications.
 * @module render-hints
 */

/**
 * Palette configurations for different UI themes.
 */
const THEME_CONFIGS = {
  dark: {
    name: 'dark',
    background: '#0F172A',
    surface: '#1E293B',
    primary: '#3B82F6',
    secondary: '#8B5CF6',
    accent: '#F59E0B',
    success: '#10B981',
    danger: '#EF4444',
    text: '#F8FAFC',
    textMuted: '#94A3B8',
    border: '#334155',
    grid: '#1E293B'
  },
  light: {
    name: 'light',
    background: '#FFFFFF',
    surface: '#F8FAFC',
    primary: '#2563EB',
    secondary: '#7C3AED',
    accent: '#D97706',
    success: '#059669',
    danger: '#DC2626',
    text: '#0F172A',
    textMuted: '#64748B',
    border: '#E2E8F0',
    grid: '#F1F5F9'
  },
  'high-contrast': {
    name: 'high-contrast',
    background: '#000000',
    surface: '#121212',
    primary: '#FFFF00',
    secondary: '#00FFFF',
    accent: '#FF00FF',
    success: '#00FF00',
    danger: '#FF0000',
    text: '#FFFFFF',
    textMuted: '#E0E0E0',
    border: '#FFFFFF',
    grid: '#333333'
  }
};

/**
 * Returns supported visual specification types.
 *
 * @returns {Array<string>} Array of supported visual spec types.
 */
export function getSupportedVisualTypes() {
  return [
    'circuit',
    'equation',
    'graph',
    'concept_map',
    'diagram',
    'timeline',
    'code_trace'
  ];
}

/**
 * Retrieves styling configuration for a named theme.
 *
 * @param {string} [themeName='dark'] - Theme name ('dark', 'light', 'high-contrast').
 * @returns {Object} Theme configuration palette.
 */
export function getThemeConfig(themeName = 'dark') {
  return THEME_CONFIGS[themeName] || THEME_CONFIGS.dark;
}

/**
 * Returns the recommended rendering library for a given visual type.
 *
 * @param {string} visualType - The visual type.
 * @returns {string} Library name ('katex', 'svg', 'chartjs', 'd3', 'prism').
 */
export function getRecommendedLibrary(visualType) {
  switch (visualType) {
    case 'equation':
      return 'katex';
    case 'circuit':
    case 'diagram':
      return 'svg';
    case 'graph':
      return 'chartjs';
    case 'concept_map':
    case 'timeline':
      return 'd3';
    case 'code_trace':
      return 'prism';
    default:
      return 'svg';
  }
}

/**
 * Returns rich rendering hints for frontend and media renderer based on visual specification.
 *
 * @param {Object} visualSpec - The visual specification object.
 * @param {string} visualSpec.type - The type of visual spec.
 * @param {Object} [visualSpec.data] - Type-specific visual data.
 * @param {Object} [options={}] - Additional options (theme, device, width, height).
 * @returns {Object} Rendering hints.
 */
export function getRenderHint(visualSpec, options = {}) {
  if (!visualSpec || !visualSpec.type) {
    return {
      error: 'Invalid visual specification',
      library: 'html',
      component: 'ErrorFallbackViewer',
      responsive: true
    };
  }

  const {
    theme = 'dark',
    aspectRatio = '16:9',
    device = 'desktop'
  } = options;

  const themePalette = getThemeConfig(theme);

  const baseHints = {
    dimensions: {
      width: '100%',
      height: 'auto',
      maxWidth: 960,
      aspectRatio
    },
    responsive: true,
    theme: themePalette.name,
    palette: themePalette,
    device
  };

  switch (visualSpec.type) {
    case 'equation':
      return {
        ...baseHints,
        library: 'katex',
        component: 'MathEquationViewer',
        animation: 'fade-in-steps',
        interactive: true,
        katexOptions: {
          displayMode: true,
          throwOnError: false,
          errorColor: themePalette.danger,
          macros: {
            '\\ohm': '\\Omega',
            '\\degree': '^\\circ'
          }
        },
        stepTransitionMs: 400,
        capabilities: ['step_stepper', 'zoom_math', 'copy_latex']
      };

    case 'circuit':
      return {
        ...baseHints,
        library: 'svg',
        component: 'CircuitViewer',
        animation: 'draw-paths',
        interactive: true,
        renderer: 'svg-canvas',
        viewBox: visualSpec.data?.viewBox || '0 0 580 400',
        capabilities: [
          'toggle_switch',
          'hover_component_tooltip',
          'highlight_current_loop',
          'pan_zoom'
        ],
        particleAnimation: {
          enabled: true,
          speed: 1.0,
          color: themePalette.accent
        }
      };

    case 'graph':
      return {
        ...baseHints,
        library: 'chartjs',
        component: 'CartesianGraphViewer',
        animation: 'draw-series',
        chartType: 'scatter-line',
        interactive: true,
        capabilities: [
          'hover_point_tooltip',
          'drag_operating_point',
          'toggle_gridlines',
          'zoom_pan_curve'
        ],
        options: {
          responsive: true,
          maintainAspectRatio: true,
          scales: {
            x: { grid: { color: themePalette.grid } },
            y: { grid: { color: themePalette.grid } }
          }
        }
      };

    case 'concept_map':
      return {
        ...baseHints,
        library: 'd3',
        component: 'ConceptMapViewer',
        animation: 'node-reveal',
        layoutEngine: 'force-directed',
        interactive: true,
        capabilities: [
          'drag_node',
          'highlight_subgraph',
          'expand_node_details',
          'pan_zoom'
        ],
        nodeRevealDelayMs: 200
      };

    case 'diagram': {
      const data = visualSpec.data || {};
      if (data.composite) {
        return {
          ...baseHints,
          library: 'composite',
          component: 'CompositeRepairViewer',
          animation: 'staggered-reveal',
          layout: 'multi_panel',
          subRenderers: {
            equation: 'katex',
            analogy: 'svg',
            graph: 'chartjs'
          },
          interactive: true,
          capabilities: [
            'sync_scrubbing',
            'highlight_misconception_flow',
            'compare_scenarios'
          ]
        };
      }

      if (data.diagramType === 'hydraulic_analogy') {
        return {
          ...baseHints,
          library: 'svg',
          component: 'HydraulicAnalogyViewer',
          animation: 'flow-simulation',
          interactive: true,
          viewBox: data.coordinateBounds?.viewBox || '0 0 600 420',
          capabilities: [
            'toggle_pipe_constriction',
            'adjust_pump_pressure',
            'simulate_water_particles',
            'view_electrical_mapping_table'
          ]
        };
      }

      return {
        ...baseHints,
        library: 'svg',
        component: 'DiagramViewer',
        animation: 'draw-paths',
        interactive: true
      };
    }

    case 'timeline':
      return {
        ...baseHints,
        library: 'd3',
        component: 'TimelineViewer',
        animation: 'step-progress',
        interactive: true
      };

    case 'code_trace':
      return {
        ...baseHints,
        library: 'prism',
        component: 'CodeTraceViewer',
        animation: 'line-highlight',
        interactive: true,
        language: 'javascript'
      };

    default:
      return {
        ...baseHints,
        library: 'html',
        component: 'GenericContentCard',
        animation: 'none',
        interactive: false
      };
  }
}
