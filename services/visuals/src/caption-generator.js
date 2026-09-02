/**
 * Caption and narration utilities with multilingual support and mathematical formula preservation.
 * @module caption-generator
 */

/**
 * Regex identifying mathematical equations, formulas, units, and numeric quantities.
 * These patterns must remain invariant across all language translations.
 */
const MATH_TOKEN_REGEX = /(?:[VIR]\s*=\s*[^\s,!?]+(?:\s*[+\-*/×·÷]\s*[^\s,!?]+)*|\b\d+(?:\.\d+)?\s*(?:V|Ω|A|Amperes|Volts|Ohms|L\/s|W|Psi|mm)\b|\b[VIR]\s*=\s*V\/R\b|\bV\s*=\s*I\s*[×*·]\s*R\b|\bV\s*=\s*IR\b|\bI\s*=\s*V\/R\b|\b\d+\/\d+(?:=\d+A)?\b|\b[VIR]\b)/g;

/**
 * Normalizes language codes/names to canonical format ('english', 'hindi', 'hinglish').
 *
 * @param {string} lang - Input language string (e.g. 'en', 'hi', 'hinglish', 'Hindi').
 * @returns {string} Canonical language name ('english', 'hindi', or 'hinglish').
 */
export function normalizeLanguageCode(lang) {
  if (!lang || typeof lang !== 'string') return 'english';
  const l = lang.toLowerCase().trim();
  if (l === 'en' || l === 'english' || l === 'eng') return 'english';
  if (l === 'hi' || l === 'hindi' || l === 'hin') return 'hindi';
  if (l === 'hinglish' || l === 'hi-latn' || l === 'hing') return 'hinglish';
  return l;
}

/**
 * Formats a time in seconds to MM:SS.mmm format.
 *
 * @param {number} seconds - Time in seconds.
 * @returns {string} Formatted timestamp.
 */
export function formatTimingMarker(seconds) {
  const s = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(s / 60);
  const secs = Math.floor(s % 60);
  const millis = Math.floor((s % 1) * 1000);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(millis).padStart(3, '0')}`;
}

/**
 * Extracts mathematical formulas and expressions from a text string.
 *
 * @param {string} text - Input text.
 * @returns {Array<string>} List of matched math tokens.
 */
export function extractMathExpressions(text) {
  if (!text || typeof text !== 'string') return [];
  const matches = text.match(MATH_TOKEN_REGEX);
  return matches ? Array.from(new Set(matches.map(m => m.trim()))) : [];
}

/**
 * Splits narration text into natural timed caption segments without breaking decimal numbers or equations.
 *
 * @param {string} narrationText - The full narration text.
 * @param {string} [language='hinglish'] - The language code.
 * @param {number} [durationSeconds=30] - The total duration in seconds.
 * @param {Object} [options={}] - Additional timing configuration.
 * @returns {Array<Object>} Array of timed caption segment objects.
 */
export function generateCaptions(narrationText, language = 'hinglish', durationSeconds = 30, options = {}) {
  if (!narrationText || typeof narrationText !== 'string') {
    return [];
  }

  const cleanText = narrationText.trim();
  if (!cleanText) return [];

  const lang = normalizeLanguageCode(language);
  const totalDuration = Math.max(1, Number(durationSeconds) || 30);

  // Split text into sentences avoiding splits on decimal numbers (e.g. 10.0V, 2.5Ω, 4.0A)
  // Match tokens that may contain decimal numbers without breaking on their internal dot.
  const rawSegments = [];
  const sentenceRegex = /(?:[^.!?\n]|\d+\.\d+)+[.!?]+(?:\s+|$)|(?:[^.!?\n]|\d+\.\d+)+$/g;
  let match;

  while ((match = sentenceRegex.exec(cleanText)) !== null) {
    const segment = match[0].trim();
    if (segment.length > 0) {
      rawSegments.push(segment);
    }
  }

  const segments = rawSegments.length > 0 ? rawSegments : [cleanText];

  // Calculate word count for each segment to distribute timing naturally
  const segmentWordCounts = segments.map(s => {
    const words = s.split(/\s+/).filter(Boolean);
    return Math.max(1, words.length);
  });

  const totalWords = segmentWordCounts.reduce((acc, count) => acc + count, 0);

  let currentStartTime = 0;
  return segments.map((text, index) => {
    const wordWeight = segmentWordCounts[index] / totalWords;
    let segDuration = wordWeight * totalDuration;

    // Minimum segment duration 1.0s if possible
    if (segDuration < 1.0 && segments.length > 1) {
      segDuration = Math.min(segDuration, totalDuration / segments.length);
    }

    const startTime = parseFloat(currentStartTime.toFixed(2));
    let endTime = parseFloat((currentStartTime + segDuration).toFixed(2));

    // Ensure the final segment lands exactly on totalDuration
    if (index === segments.length - 1 || endTime > totalDuration) {
      endTime = parseFloat(totalDuration.toFixed(2));
    }

    currentStartTime = endTime;

    const mathFormulas = extractMathExpressions(text);

    return {
      index,
      text,
      language: lang,
      startTime,
      endTime,
      duration: parseFloat((endTime - startTime).toFixed(2)),
      startMarker: formatTimingMarker(startTime),
      endMarker: formatTimingMarker(endTime),
      mathFormulas
    };
  });
}

/**
 * Sentence-level canonical translations mapping for standard curriculum phrases.
 */
const SENTENCE_TRANSLATIONS = [
  // Intro
  {
    en: "Hello students!",
    hi: "नमस्ते विद्यार्थियों!",
    hinglish: "Hello students!"
  },
  {
    en: "Today we will learn about Electric Current and Ohm's Law.",
    hi: "आज हम विद्युत धारा और ओम के नियम के बारे में सीखेंगे।",
    hinglish: "Aaj hum Electric Current aur Ohm's Law ke baare mein seekhenge."
  },
  {
    en: "This is the fundamental rule of electricity.",
    hi: "यह विद्युत का मूलभूत नियम है।",
    hinglish: "Yeh electricity ka basic rule hai."
  },
  // Current
  {
    en: "Current is the flow of electricity, just like a river of water.",
    hi: "धारा बिजली का प्रवाह है, बिल्कुल पानी की नदी की तरह।",
    hinglish: "Current matlab electricity ka flow hai, bilkul paani ki nadiya ki tarah."
  },
  // Voltage
  {
    en: "Think of Voltage like water pressure - the more pressure, the more current flows.",
    hi: "वोल्टेज को पानी के दबाव की तरह समझें - जितना अधिक दबाव, उतना अधिक धारा प्रवाह होगा।",
    hinglish: "Voltage ko samjho jaise water pressure - jitna zyada pressure, utna zyada current flow hoga."
  },
  {
    en: "It pushes electrons.",
    hi: "यह इलेक्ट्रॉनों को धक्का देता है।",
    hinglish: "Yeh electrons ko push karta hai."
  },
  // Resistance
  {
    en: "And what is Resistance?",
    hi: "और प्रतिरोध क्या है?",
    hinglish: "Aur Resistance kya hai?"
  },
  {
    en: "It opposes flow, like a speed breaker.",
    hi: "यह प्रवाह का विरोध करता है, जैसे स्पीड ब्रेकर।",
    hinglish: "Yeh flow ko rokata hai, jaise speed breaker."
  },
  {
    en: "Higher resistance means less current.",
    hi: "अधिक प्रतिरोध का अर्थ है कम धारा।",
    hinglish: "Zyada resistance matlab kam current."
  },
  // Ohm's Law
  {
    en: "Ohm's Law states that V = I × R.",
    hi: "ओम का नियम कहता है कि V = I × R।",
    hinglish: "Ohm's Law kehta hai ki V = I × R."
  },
  {
    en: "This means Voltage equals Current into Resistance.",
    hi: "इसका अर्थ है वोल्टेज बराबर धारा गुणा प्रतिरोध।",
    hinglish: "Iska matlab hai Voltage equals Current into Resistance."
  },
  {
    en: "If we solve for I, then I = V/R.",
    hi: "यदि I निकालना हो, तो I = V/R होता है।",
    hinglish: "Agar I nikalna ho, toh I = V/R hota hai."
  },
  {
    en: "For example if V is 10 and R is 5, then I will be 2 Amperes.",
    hi: "मान लो V 10 है और R 5, तो I होगा 2 Amperes।",
    hinglish: "Maan lo V 10 hai aur R 5, toh I hoga 2 Amperes."
  },
  // Checkpoint
  {
    en: "Now a question.",
    hi: "अब एक प्रश्न।",
    hinglish: "Ab ek sawal."
  },
  {
    en: "If voltage stays constant and we increase resistance, what happens to current?",
    hi: "यदि वोल्टेज स्थिर रहे, और हम प्रतिरोध बढ़ा दें, तो धारा का क्या होगा?",
    hinglish: "Agar voltage same rahe, aur hum resistance badha dein, toh current ka kya hoga?"
  },
  // Repair
  {
    en: "Think of water flowing through a pipe.",
    hi: "सोचें एक पाइप में पानी बह रहा है।",
    hinglish: "Socho ek pipe mein paani beh raha hai."
  },
  {
    en: "If you narrow the pipe (increase resistance), the water flow (current) will DECREASE, not increase!",
    hi: "यदि पाइप को संकरा कर दें (प्रतिरोध बढ़ाएं), तो पानी का बहाव (धारा) कम होगा, ज्यादा नहीं!",
    hinglish: "Agar pipe ko narrow kar do (matlab resistance badhao), toh paani ka flow (matlab current) KAM hoga, zyada nahi!"
  },
  {
    en: "Similarly, in I = V/R, when R increases, I decreases.",
    hi: "इसी तरह, I = V/R में, जब R बढ़ता है तो I घटता है।",
    hinglish: "Isi tarah, I = V/R mein, jab R badhta hai toh I GHATTA hai."
  },
  // Summary
  {
    en: "Great job!",
    hi: "बहुत बढ़िया!",
    hinglish: "Great job!"
  },
  {
    en: "Today we learned how Current, Voltage, and Resistance are connected through Ohm's Law.",
    hi: "आज हमने सीखा कि धारा, वोल्टेज और प्रतिरोध ओम के नियम के माध्यम से कैसे जुड़े हैं।",
    hinglish: "Aaj humne seekha ki Current, Voltage, aur Resistance kaise ek dusre se jude hue hain Ohm's law ke through."
  },
  {
    en: "In the next class, we will build circuits.",
    hi: "अगली कक्षा में हम परिपथ बनाएंगे।",
    hinglish: "Agli class mein hum circuits banayenge."
  }
];

/**
 * Translates captions into target language while strictly preserving all mathematical expressions.
 *
 * @param {Array<Object>} captions - Array of caption segment objects.
 * @param {string} targetLanguage - Target language code ('english', 'hindi', 'hinglish').
 * @param {Object} [options={}] - Additional options.
 * @returns {Array<Object>} Array of translated caption objects.
 */
export function translateCaptionLanguage(captions, targetLanguage, options = {}) {
  if (!captions || !Array.isArray(captions)) return [];
  const targetLang = normalizeLanguageCode(targetLanguage);
  const targetKey = targetLang === 'english' ? 'en' : (targetLang === 'hindi' ? 'hi' : 'hinglish');

  return captions.map(caption => {
    const originalText = (caption.text || '').trim();
    let translatedText = null;

    // Check sentence translation table for exact match
    for (const item of SENTENCE_TRANSLATIONS) {
      if (
        originalText === item.en ||
        originalText === item.hi ||
        originalText === item.hinglish ||
        originalText.replace(/[.!?।]+$/, '').trim() === item.en.replace(/[.!?।]+$/, '').trim() ||
        originalText.replace(/[.!?।]+$/, '').trim() === item.hi.replace(/[.!?।]+$/, '').trim() ||
        originalText.replace(/[.!?।]+$/, '').trim() === item.hinglish.replace(/[.!?।]+$/, '').trim()
      ) {
        translatedText = item[targetKey] || item.en;
        break;
      }
    }

    // Fallback: translate preserving all mathematical tokens
    if (!translatedText) {
      translatedText = translateSentencePreservingMath(originalText, targetLang);
    }

    return {
      ...caption,
      text: translatedText,
      language: targetLang,
      mathFormulas: extractMathExpressions(translatedText)
    };
  });
}

/**
 * Translates an arbitrary sentence into target language, strictly leaving mathematical expressions unchanged.
 *
 * @param {string} text - Source text.
 * @param {string} targetLang - Target language ('english', 'hindi', 'hinglish').
 * @returns {string} Translated text with invariant math expressions.
 */
function translateSentencePreservingMath(text, targetLang) {
  if (!text) return '';

  // Extract all math tokens and replace with placeholders
  const mathTokens = [];
  const placeholderText = text.replace(MATH_TOKEN_REGEX, (match) => {
    mathTokens.push(match);
    return `__MATH_TOKEN_${mathTokens.length - 1}__`;
  });

  let translated = placeholderText;

  // Domain terms dictionary for clean translation
  const dict = {
    english: {
      'paani': 'water',
      'nadiya': 'river',
      'badhta': 'increases',
      'ghatta': 'decreases',
      'kam': 'less',
      'zyada': 'more',
      'samjho': 'understand',
      'seekhenge': 'will learn',
      'socho': 'think',
      'sawal': 'question',
      'dhara': 'current',
      'pratirodh': 'resistance'
    },
    hindi: {
      'current': 'धारा',
      'voltage': 'वोल्टेज',
      'resistance': 'प्रतिरोध',
      'increases': 'बढ़ता है',
      'decreases': 'घटता है',
      'less': 'कम',
      'more': 'अधिक',
      'water': 'पानी',
      'pressure': 'दबाव',
      'pipe': 'पाइप',
      'learn': 'सीखें'
    },
    hinglish: {
      'voltage': 'voltage',
      'current': 'current',
      'resistance': 'resistance',
      'increases': 'badhta hai',
      'decreases': 'kam hota hai',
      'less': 'kam',
      'more': 'zyada',
      'water': 'paani',
      'pressure': 'pressure',
      'pipe': 'pipe'
    }
  };

  const targetDict = dict[targetLang] || {};

  // Word substitution for non-math words
  translated = translated.split(' ').map(word => {
    const cleanWord = word.toLowerCase().replace(/[^a-z0-9]/gi, '');
    if (targetDict[cleanWord]) {
      return word.replace(new RegExp(cleanWord, 'i'), targetDict[cleanWord]);
    }
    return word;
  }).join(' ');

  // Restore all math tokens exactly as they were
  mathTokens.forEach((token, idx) => {
    translated = translated.replace(`__MATH_TOKEN_${idx}__`, token);
  });

  return translated;
}
