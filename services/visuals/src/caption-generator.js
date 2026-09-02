/**
 * Caption and narration utilities.
 * @module caption-generator
 */

/**
 * Splits narration into timed caption segments.
 * @param {string} narrationText - The full narration text.
 * @param {string} language - The language code (e.g., 'en', 'es').
 * @param {number} durationSeconds - The total duration in seconds.
 * @returns {Array<Object>} An array of timed caption segments.
 */
export function generateCaptions(narrationText, language, durationSeconds) {
  if (!narrationText) return [];
  
  // Simple mock: split by sentences (periods, question marks, exclamation marks)
  const sentences = narrationText.match(/[^.!?]+[.!?]+/g) || [narrationText];
  const segmentDuration = durationSeconds / sentences.length;
  
  return sentences.map((sentence, index) => {
    return {
      text: sentence.trim(),
      language,
      startTime: index * segmentDuration,
      endTime: (index + 1) * segmentDuration
    };
  });
}

/**
 * Translates captions to a target language, preserving formulae.
 * @param {Array<Object>} captions - The array of caption segments.
 * @param {string} targetLanguage - The target language code.
 * @returns {Array<Object>} The translated caption segments.
 */
export function translateCaptionLanguage(captions, targetLanguage) {
  if (!captions || !Array.isArray(captions)) return [];
  
  return captions.map(caption => {
    const text = caption.text;
    
    // Find equation-like substrings (simple heuristic: contains =)
    const words = text.split(' ');
    const translatedWords = words.map(word => {
      if (word.includes('=') || /^[A-Z0-9/]+$/.test(word)) {
        return word; // Preserve equations/formulae
      }
      return `[${targetLanguage}]${word}`; // Mock translation
    });
    
    return {
      ...caption,
      text: translatedWords.join(' '),
      language: targetLanguage
    };
  });
}
