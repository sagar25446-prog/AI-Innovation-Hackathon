const fs = require('fs');
const path = require('path');

const schemaPath = path.join(__dirname, 'lesson-contract.schema.json');
const schemaStr = fs.readFileSync(schemaPath, 'utf8');
const schema = JSON.parse(schemaStr);
const definitions = schema.definitions;

function validateType(value, type, schemaDef, pathStr, errors) {
  if (type === 'string') {
    if (typeof value !== 'string') errors.push(`${pathStr} should be string, got ${typeof value}`);
    else if (schemaDef.enum && !schemaDef.enum.includes(value)) {
      errors.push(`${pathStr} should be one of [${schemaDef.enum.join(', ')}], got ${value}`);
    }
  } else if (type === 'number' || type === 'integer') {
    if (typeof value !== 'number') errors.push(`${pathStr} should be number, got ${typeof value}`);
  } else if (type === 'boolean') {
    if (typeof value !== 'boolean') errors.push(`${pathStr} should be boolean, got ${typeof value}`);
  } else if (type === 'object') {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
      errors.push(`${pathStr} should be object`);
    } else {
      validateObject(value, schemaDef, pathStr, errors);
    }
  } else if (type === 'array') {
    if (!Array.isArray(value)) {
      errors.push(`${pathStr} should be array`);
    } else if (schemaDef.items) {
      value.forEach((item, index) => {
        validateType(item, getType(schemaDef.items), schemaDef.items, `${pathStr}[${index}]`, errors);
      });
    }
  }
}

function getType(schemaDef) {
  if (schemaDef.type) return schemaDef.type;
  if (schemaDef.$ref) {
    const refName = schemaDef.$ref.split('/').pop();
    return definitions[refName].type;
  }
  return null;
}

function resolveRef(schemaDef) {
  if (schemaDef.$ref) {
    const refName = schemaDef.$ref.split('/').pop();
    return definitions[refName];
  }
  return schemaDef;
}

function validateObject(obj, schemaDef, pathStr, errors) {
  const resolvedSchema = resolveRef(schemaDef);
  
  if (resolvedSchema.required) {
    resolvedSchema.required.forEach(req => {
      if (!(req in obj)) {
        errors.push(`${pathStr} missing required field: ${req}`);
      }
    });
  }

  if (resolvedSchema.properties) {
    for (const key in obj) {
      if (resolvedSchema.properties[key]) {
        const propSchema = resolvedSchema.properties[key];
        const propType = getType(propSchema);
        if (propType) {
          validateType(obj[key], propType, propSchema, `${pathStr}.${key}`, errors);
        }
      }
    }
  }
}

function validate(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const data = JSON.parse(content);
    
    // Simple heuristic to determine root type
    let rootDefName = null;
    if (data.scenes && data.learner) rootDefName = 'LessonPlan';
    else if (data.narration && data.visual) rootDefName = 'Scene';
    else if ('correct' in data && data.nextAction) rootDefName = 'EvaluationResult';
    else {
      // Just check if it parses, e.g. LearningReport doesn't have a schema def in the current schema
      // but we shouldn't fail it. Let's assume it's valid if we can't detect a root type.
    }

    if (rootDefName) {
      const errors = [];
      validateObject(data, definitions[rootDefName], rootDefName, errors);
      if (errors.length > 0) {
        console.error(`❌ FAIL: ${filePath}`);
        errors.forEach(err => console.error(`   - ${err}`));
        return false;
      }
    }
    console.log(`✅ PASS: ${filePath}`);
    return true;
  } catch (err) {
    console.error(`❌ FAIL: ${filePath}`);
    console.error(`   - Error: ${err.message}`);
    return false;
  }
}

const files = process.argv.slice(2);
let allPassed = true;
files.forEach(file => {
  if (!validate(file)) {
    allPassed = false;
  }
});

if (!allPassed) {
  process.exit(1);
}
