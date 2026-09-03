const fs = require('fs');
const path = require('path');

const schemaPath = path.join(__dirname, 'lesson-contract.schema.json');
const schemaStr = fs.readFileSync(schemaPath, 'utf8');
const schema = JSON.parse(schemaStr);
const definitions = schema.definitions || schema.$defs || {};

/**
 * Resolves a schema definition or reference.
 * @param {Object} schemaDef
 * @returns {Object}
 */
function resolveRef(schemaDef) {
  if (!schemaDef) return {};
  if (schemaDef.$ref) {
    const parts = schemaDef.$ref.split('/');
    const refName = parts[parts.length - 1];
    if (definitions[refName]) {
      return resolveRef(definitions[refName]);
    }
    if (schema.$defs && schema.$defs[refName]) {
      return resolveRef(schema.$defs[refName]);
    }
  }
  return schemaDef;
}

/**
 * Infers the root contract definition name for a given JSON object.
 * @param {Object} data
 * @returns {string|null}
 */
function inferType(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }
  if (data.scenes && data.learner) {
    return 'LessonPlan';
  }
  if (data.narration && data.visual && data.conceptId) {
    return 'Scene';
  }
  if ('correct' in data && data.nextAction) {
    return 'EvaluationResult';
  }
  if (data.studentId && ('score' in data || data.strongConcepts || data.misconceptions)) {
    return 'LearningReport';
  }
  if (data.checkpointId && data.studentAnswer) {
    return 'CheckpointSubmission';
  }
  if (data.type && data.data && ['circuit', 'equation', 'graph', 'timeline', 'diagram', 'code_trace', 'concept_map'].includes(data.type)) {
    return 'VisualSpec';
  }
  if (data.level && data.language && data.goal) {
    return 'LearnerProfile';
  }
  if (data.documentId && data.excerpt && 'pageOrSlide' in data) {
    return 'SourceCitation';
  }
  return null;
}

/**
 * Validates a value against a subschema.
 * @param {*} value
 * @param {Object} schemaDef
 * @param {string} pathStr
 * @param {string[]} errors
 */
function validateValue(value, schemaDef, pathStr, errors) {
  if (!schemaDef) return;
  const resolved = resolveRef(schemaDef);

  if (resolved.oneOf && Array.isArray(resolved.oneOf)) {
    const oneOfErrors = [];
    let matchCount = 0;
    for (const alt of resolved.oneOf) {
      const subErrors = [];
      validateValue(value, alt, pathStr, subErrors);
      if (subErrors.length === 0) {
        matchCount++;
      } else {
        oneOfErrors.push(subErrors.join('; '));
      }
    }
    if (matchCount !== 1) {
      errors.push(`${pathStr} must match exactly one of the alternative schemas (matched: ${matchCount})`);
    }
    return;
  }

  if (resolved.anyOf && Array.isArray(resolved.anyOf)) {
    let matched = false;
    for (const alt of resolved.anyOf) {
      const subErrors = [];
      validateValue(value, alt, pathStr, subErrors);
      if (subErrors.length === 0) {
        matched = true;
        break;
      }
    }
    if (!matched) {
      errors.push(`${pathStr} did not match any of the allowed schemas`);
    }
    return;
  }

  // Validate enum constraints regardless of whether an explicit type is declared
  if (resolved.enum && Array.isArray(resolved.enum)) {
    if (!resolved.enum.includes(value)) {
      const formattedValue = typeof value === 'string' ? `"${value}"` : value;
      errors.push(`${pathStr} should be one of [${resolved.enum.join(', ')}], got ${formattedValue}`);
    }
  }

  const expectedType = resolved.type;

  if (expectedType === 'string') {
    if (typeof value !== 'string') {
      errors.push(`${pathStr} should be string, got ${typeof value}`);
      return;
    }
    if (resolved.minLength !== undefined && value.length < resolved.minLength) {
      errors.push(`${pathStr} length (${value.length}) is less than minimum length ${resolved.minLength}`);
    }
    if (resolved.maxLength !== undefined && value.length > resolved.maxLength) {
      errors.push(`${pathStr} length (${value.length}) exceeds maximum length ${resolved.maxLength}`);
    }
  } else if (expectedType === 'integer') {
    if (typeof value !== 'number' || !Number.isInteger(value)) {
      errors.push(`${pathStr} should be integer, got ${typeof value === 'number' ? value : typeof value}`);
      return;
    }
    if (resolved.minimum !== undefined && value < resolved.minimum) {
      errors.push(`${pathStr} (${value}) is less than minimum ${resolved.minimum}`);
    }
    if (resolved.maximum !== undefined && value > resolved.maximum) {
      errors.push(`${pathStr} (${value}) exceeds maximum ${resolved.maximum}`);
    }
  } else if (expectedType === 'number') {
    if (typeof value !== 'number' || Number.isNaN(value)) {
      errors.push(`${pathStr} should be number, got ${typeof value}`);
      return;
    }
    if (resolved.minimum !== undefined && value < resolved.minimum) {
      errors.push(`${pathStr} (${value}) is less than minimum ${resolved.minimum}`);
    }
    if (resolved.maximum !== undefined && value > resolved.maximum) {
      errors.push(`${pathStr} (${value}) exceeds maximum ${resolved.maximum}`);
    }
  } else if (expectedType === 'boolean') {
    if (typeof value !== 'boolean') {
      errors.push(`${pathStr} should be boolean, got ${typeof value}`);
    }
  } else if (expectedType === 'object') {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
      errors.push(`${pathStr} should be object, got ${Array.isArray(value) ? 'array' : typeof value}`);
      return;
    }
    validateObject(value, resolved, pathStr, errors);
  } else if (expectedType === 'array') {
    if (!Array.isArray(value)) {
      errors.push(`${pathStr} should be array, got ${typeof value}`);
      return;
    }
    if (resolved.minItems !== undefined && value.length < resolved.minItems) {
      errors.push(`${pathStr} has ${value.length} items, requires at least ${resolved.minItems}`);
    }
    if (resolved.maxItems !== undefined && value.length > resolved.maxItems) {
      errors.push(`${pathStr} has ${value.length} items, exceeds maximum ${resolved.maxItems}`);
    }
    if (resolved.items) {
      value.forEach((item, index) => {
        validateValue(item, resolved.items, `${pathStr}[${index}]`, errors);
      });
    }
  } else if (!expectedType && resolved.properties) {
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      validateObject(value, resolved, pathStr, errors);
    }
  }
}

/**
 * Validates an object against a schema definition.
 * @param {Object} obj
 * @param {Object} schemaDef
 * @param {string} pathStr
 * @param {string[]} errors
 */
function validateObject(obj, schemaDef, pathStr, errors) {
  const resolved = resolveRef(schemaDef);

  if (resolved.required && Array.isArray(resolved.required)) {
    resolved.required.forEach(req => {
      if (!(req in obj) || obj[req] === undefined) {
        errors.push(`${pathStr} missing required field: "${req}"`);
      }
    });
  }

  if (resolved.properties) {
    for (const key of Object.keys(obj)) {
      if (resolved.properties[key]) {
        const propSchema = resolved.properties[key];
        validateValue(obj[key], propSchema, `${pathStr}.${key}`, errors);
      }
    }
  }
}

/**
 * Validates data against a named schema definition or inferred type.
 * @param {Object} data
 * @param {string|null} [typeName=null]
 * @returns {{ valid: boolean, errors: string[], type: string }}
 */
function validateData(data, typeName = null) {
  const targetType = typeName || inferType(data);
  if (!targetType) {
    return {
      valid: false,
      errors: ['Could not determine schema type for data payload'],
      type: 'Unknown'
    };
  }

  const def = definitions[targetType];
  if (!def) {
    return {
      valid: false,
      errors: [`Schema definition "${targetType}" not found in contract schema`],
      type: targetType
    };
  }

  const errors = [];
  validateValue(data, def, targetType, errors);
  return {
    valid: errors.length === 0,
    errors,
    type: targetType
  };
}

/**
 * Validates an arbitrary data object directly against a schema definition.
 * @param {*} data
 * @param {Object} schemaDef
 * @param {string} [path='root']
 * @returns {{ valid: boolean, errors: string[] }}
 */
function validateAgainstSchema(data, schemaDef, path = 'root') {
  const errors = [];
  validateValue(data, schemaDef, path, errors);
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates a fixture file on disk.
 * @param {string} filePath
 * @returns {{ valid: boolean, errors: string[], file: string, type: string }}
 */
function validateFixture(filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      return {
        valid: false,
        errors: [`File not found: ${filePath}`],
        file: filePath,
        type: 'FileNotFound'
      };
    }
    const content = fs.readFileSync(filePath, 'utf8');
    const data = JSON.parse(content);
    const result = validateData(data);
    return {
      ...result,
      file: filePath
    };
  } catch (err) {
    return {
      valid: false,
      errors: [`JSON parse or read error: ${err.message}`],
      file: filePath,
      type: 'ParseError'
    };
  }
}

/**
 * Backward-compatible CLI validation function for a single file path.
 * @param {string} filePath
 * @returns {boolean}
 */
function validate(filePath) {
  const result = validateFixture(filePath);
  if (result.valid) {
    console.log(`✅ PASS: ${filePath} (${result.type})`);
    return true;
  } else {
    console.error(`❌ FAIL: ${filePath} (${result.type})`);
    result.errors.forEach(err => console.error(`   - ${err}`));
    return false;
  }
}

/**
 * Resolves file paths from arguments, expanding any globs if necessary.
 * @param {string[]} args
 * @returns {string[]}
 */
function resolveFiles(args) {
  const resolved = [];
  for (const arg of args) {
    if (arg.includes('*')) {
      // Basic glob resolver for directories
      const dir = path.dirname(arg) || '.';
      const filePattern = path.basename(arg);
      const regexStr = '^' + filePattern.replace(/\./g, '\\.').replace(/\*/g, '.*') + '$';
      const regex = new RegExp(regexStr);
      if (fs.existsSync(dir)) {
        const entries = fs.readdirSync(dir);
        for (const entry of entries) {
          if (regex.test(entry)) {
            resolved.push(path.join(dir, entry));
          }
        }
      }
    } else {
      resolved.push(arg);
    }
  }
  return resolved;
}

// CLI Execution Handler
if (require.main === module) {
  const args = process.argv.slice(2);
  const files = resolveFiles(args);

  if (files.length === 0) {
    console.log('Usage: node validate.js <file1.json> <file2.json> ... [or glob: demo-fixtures/*.json]');
    process.exit(1);
  }

  let allPassed = true;
  let passedCount = 0;
  let failedCount = 0;

  files.forEach(file => {
    if (validate(file)) {
      passedCount++;
    } else {
      allPassed = false;
      failedCount++;
    }
  });

  console.log(`\nValidation Summary: ${passedCount} passed, ${failedCount} failed (${files.length} total)`);
  if (!allPassed) {
    process.exit(1);
  }
}

module.exports = {
  validate,
  validateFixture,
  validateData,
  validateAgainstSchema,
  inferType,
  getSchema: () => schema,
  getDefinitions: () => definitions
};
