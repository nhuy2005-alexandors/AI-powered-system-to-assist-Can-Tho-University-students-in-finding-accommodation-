const Ajv = require("ajv");
const addFormats = require("ajv-formats");
const fs = require('fs');
const path = require('path');

const ajv = new Ajv({ strict: false });
addFormats(ajv);

const AGENT_DIR = path.join(__dirname, '..');
const SCHEMAS_DIR = path.join(AGENT_DIR, 'schemas');
const REGISTRY_FILE = path.join(AGENT_DIR, 'registry.json');

try {
    const agentSchema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'agent.schema.json'), 'utf8'));
    const registrySchema = JSON.parse(fs.readFileSync(path.join(SCHEMAS_DIR, 'registry.schema.json'), 'utf8'));

    ajv.addSchema(agentSchema, "agent.schema.json");

    const validate = ajv.compile(registrySchema);

    const registryData = JSON.parse(fs.readFileSync(REGISTRY_FILE, 'utf8'));

    const valid = validate(registryData);

    if (!valid) {
        console.error("\x1b[31mRegistry validation failed with errors:\x1b[0m");
        validate.errors.forEach(err => {
            console.error(`- ${err.instancePath} ${err.message}`);
        });
        process.exit(1);
    } else {
        console.log("\x1b[32mRegistry is valid against schemas.\x1b[0m");
        process.exit(0);
    }
} catch (e) {
    console.error(`\x1b[31mError during validation:\x1b[0m ${e.message}`);
    process.exit(1);
}
