const fs = require('fs');
const path = require('path');

const POLICIES_FILE = path.join(__dirname, '..', 'rules', 'policies.json');

function loadPolicies() {
    if (!fs.existsSync(POLICIES_FILE)) {
        console.error(JSON.stringify({
            allowed: false,
            violation: "System Error",
            reason: "policies.json not found"
        }));
        process.exit(1);
    }
    try {
        return JSON.parse(fs.readFileSync(POLICIES_FILE, 'utf8'));
    } catch (e) {
        console.error(JSON.stringify({
            allowed: false,
            violation: "System Error",
            reason: "Invalid policies.json format"
        }));
        process.exit(1);
    }
}

function check(type, payload) {
    const data = loadPolicies();
    const rules = data.policies[type] || [];

    for (const rule of rules) {
        const regex = new RegExp(rule.pattern, 'i');
        if (regex.test(payload)) {
            return {
                allowed: false,
                violation: "Policy Enforcement",
                reason: rule.reason
            };
        }
    }

    return { allowed: true };
}

if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length !== 2) {
        console.error("Usage: node enforce-policy.js <check-command|check-path|check-link> \"<payload>\"");
        process.exit(1);
    }

    const mode = args[0];
    const payload = args[1];
    
    let typeMap = {
        "check-command": "forbidden_commands",
        "check-path": "forbidden_paths",
        "check-link": "malware_links"
    };

    if (!typeMap[mode]) {
        console.error(JSON.stringify({ allowed: false, reason: "Invalid mode" }));
        process.exit(1);
    }

    const result = check(typeMap[mode], payload);
    
    // Output JSON strictly to stdout
    console.log(JSON.stringify(result, null, 2));

    // Exit with code 1 if blocked, useful for shell piping
    if (!result.allowed) {
        process.exit(1);
    }
}

module.exports = { check };
