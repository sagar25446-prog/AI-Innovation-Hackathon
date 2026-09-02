/**
 * Render hint generators for visual specifications.
 * @module render-hints
 */

/**
 * Returns rendering hints for the frontend based on the visual specification.
 * @param {Object} visualSpec - The visual specification object.
 * @param {string} visualSpec.type - The type of visual spec.
 * @returns {Object} Rendering hints.
 */
export function getRenderHint(visualSpec) {
  if (!visualSpec || !visualSpec.type) {
    return { error: 'Invalid visual specification' };
  }

  const baseHints = {
    dimensions: { width: '100%', height: 'auto' },
    responsive: true
  };

  switch (visualSpec.type) {
    case 'equation':
      return {
        ...baseHints,
        library: 'katex',
        animation: 'fade-in-steps'
      };
    case 'circuit':
    case 'diagram':
      return {
        ...baseHints,
        library: 'svg',
        animation: 'draw-paths'
      };
    case 'graph':
      return {
        ...baseHints,
        library: 'chartjs',
        animation: 'draw-series'
      };
    case 'concept_map':
    case 'timeline':
    case 'code_trace':
      return {
        ...baseHints,
        library: 'd3',
        animation: 'node-reveal'
      };
    default:
      return {
        ...baseHints,
        library: 'html',
        animation: 'none'
      };
  }
}
