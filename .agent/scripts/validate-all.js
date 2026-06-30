const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PROJECT_ROOT = path.join(__dirname, '..', '..');
const AGENT_DIR = path.join(PROJECT_ROOT, '.agent');
const FRONTEND_DIR = path.join(PROJECT_ROOT, 'omni-agents-system');

let errors = 0;
let warnings = 0;

function logStatus(task, status, message = "") {
    if (status === 'PASS') {
        console.log(`\x1b[32m[PASS]\x1b[0m ${task}`);
    } else if (status === 'WARN') {
        console.log(`\x1b[33m[WARN]\x1b[0m ${task} ${message ? '- ' + message : ''}`);
        warnings++;
    } else {
        console.log(`\x1b[31m[FAIL]\x1b[0m ${task} ${message ? '- ' + message : ''}`);
        errors++;
    }
}

console.log("==========================================");
console.log("  OMNI ASSISTANT - CONTINUOUS VALIDATION  ");
console.log("==========================================\n");

// 1. Check registry.json using strict schema validator
try {
    console.log(`\n\x1b[36m=> Running Strict Schema Validation...\x1b[0m`);
    execSync('node .agent/scripts/validate-registry.js', { cwd: PROJECT_ROOT, stdio: 'pipe' });
    logStatus("Registry Strict Schema Validation", "PASS");
} catch (e) {
    const errorMsg = e.stderr ? e.stderr.toString() : e.message;
    logStatus("Registry Strict Schema Validation", "FAIL", "Schema error");
    console.error(e.stdout ? e.stdout.toString() : errorMsg);
}
// 1.5 Check Doc Drift
try {
    console.log(`\n\x1b[36m=> Checking Doc Drift...\x1b[0m`);
    const architecturePath = path.join(PROJECT_ROOT, '.agent', 'ARCHITECTURE.md');
    let oldDocs = "";
    if (fs.existsSync(architecturePath)) {
        oldDocs = fs.readFileSync(architecturePath, 'utf8');
    }
    execSync('node .agent/scripts/build-docs.js', { cwd: PROJECT_ROOT, stdio: 'ignore' });
    const newDocs = fs.readFileSync(architecturePath, 'utf8');
    if (oldDocs !== newDocs) {
        logStatus("Doc Drift Check", "FAIL", "ARCHITECTURE.md was out of sync with registry. Run build-docs.js");
    } else {
        logStatus("Doc Drift Check", "PASS");
    }
} catch (e) {
    logStatus("Doc Drift Check", "FAIL", e.message);
}

// 2. Check policies.json
try {
    const policiesPath = path.join(AGENT_DIR, 'rules', 'policies.json');
    if (fs.existsSync(policiesPath)) {
        const policies = JSON.parse(fs.readFileSync(policiesPath, 'utf8'));
        if (!Array.isArray(policies.policies.forbidden_commands)) throw new Error("Invalid structure");
        logStatus("Policies Validation", "PASS");
    } else {
        logStatus("Policies Validation", "WARN", "policies.json not found");
    }
} catch (e) {
    logStatus("Policies Validation", "FAIL", e.message);
}

// 3. Check Workflows metadata sidecars
try {
    const workflowsDir = path.join(AGENT_DIR, 'workflows');
    const registryPath = path.join(AGENT_DIR, 'registry.json');
    const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
    const validAgents = Object.keys(registry.agents);

    if (fs.existsSync(workflowsDir)) {
        const files = fs.readdirSync(workflowsDir);
        const mds = files.filter(f => f.endsWith('.md'));
        const jsons = files.filter(f => f.endsWith('.json'));
        
        let missingSidecars = 0;
        let invalidAgents = 0;

        mds.forEach(md => {
            const base = path.basename(md, '.md');
            if (!jsons.includes(`${base}.json`)) missingSidecars++;

            // Extract Agent from md file
            const mdContent = fs.readFileSync(path.join(workflowsDir, md), 'utf8');
            const agentMatch = mdContent.match(/\*\*Agent\*\*:\s*(.*)/);
            if (agentMatch) {
                // Parse out words that look like `agent-name`
                const mentionedAgents = [...agentMatch[1].matchAll(/`([^`]+)`/g)].map(m => m[1]);
                mentionedAgents.forEach(agent => {
                    if (!validAgents.includes(agent) && agent !== 'specific specialist') {
                        console.error(`\x1b[31m[FAIL]\x1b[0m Invalid agent '${agent}' in workflow ${md}`);
                        invalidAgents++;
                    }
                });
            }
        });

        if (missingSidecars > 0 || invalidAgents > 0) {
            logStatus("Workflows Sidecar & MD Match", "FAIL", `${missingSidecars} missing sidecars, ${invalidAgents} invalid agents`);
            throw new Error("Workflows validation failed");
        } else {
            logStatus("Workflows Sidecar & MD Match", "PASS");
        }
    } else {
        throw new Error("Workflows directory not found");
    }
} catch (e) {
    logStatus("Workflows Sidecar & MD Match", "FAIL", e.message);
}

// 4. Check Skill Hashes
try {
    const registryPath = path.join(AGENT_DIR, 'registry.json');
    if (fs.existsSync(registryPath)) {
        const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
        let unknownHashes = 0;
        for (const [skillName, skill] of Object.entries(registry.skills)) {
            if (skill.skill_hash === "unknown" || skill.directory_hash === "unknown") {
                unknownHashes++;
            }
        }
        if (unknownHashes > 0) {
            logStatus("Skill Integrity Check", "FAIL", `${unknownHashes} skills have 'unknown' hashes`);
            throw new Error("Unknown skill hashes detected");
        } else {
            logStatus("Skill Integrity Check", "PASS");
        }
    }
} catch (e) {
    logStatus("Skill Integrity Check", "FAIL", e.message);
}

// 5. Frontend Check (omni-agents-system)
try {
    console.log(`\n\x1b[36m=> Running Frontend Code Quality Checks...\x1b[0m`);
    if (fs.existsSync(FRONTEND_DIR)) {
        execSync('npm run lint', { cwd: FRONTEND_DIR, stdio: 'ignore' });
        logStatus("Frontend Linting", "PASS");
        execSync('npm run build', { cwd: FRONTEND_DIR, stdio: 'ignore' });
        logStatus("Frontend Build Check", "PASS");
    } else {
        throw new Error("Frontend directory not found");
    }
} catch (e) {
    logStatus("Frontend Check", "FAIL", "Lint or Build failed. Check syntax in omni-agents-system.");
}

console.log("\n==========================================");
if (errors > 0) {
    console.log(`\x1b[31mValidation Failed with ${errors} error(s).\nSystem state: FAILED\x1b[0m`);
    process.exitCode = 1;
    process.exit(1);
} else if (warnings > 0) {
    console.log(`\x1b[33mValidation Passed but with ${warnings} warning(s).\nSystem state: DEGRADED\x1b[0m`);
    process.exit(0);
} else {
    console.log(`\x1b[32mAll validations passed successfully!\nSystem state: HEALTHY\x1b[0m`);
    process.exit(0);
}
