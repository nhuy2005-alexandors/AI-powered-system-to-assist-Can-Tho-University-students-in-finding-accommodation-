const fs = require('fs');
const path = require('path');

const REGISTRY_FILE = path.join(__dirname, '..', 'registry.json');

function loadRegistry() {
    if (!fs.existsSync(REGISTRY_FILE)) {
        console.error('Error: registry.json not found. Run build-registry.js first.');
        process.exit(1);
    }
    return JSON.parse(fs.readFileSync(REGISTRY_FILE, 'utf8'));
}

function routeAgent(intent, isJsonOut = false) {
    const registry = loadRegistry();
    const intentLower = intent.toLowerCase();
    const tokens = intentLower.split(/\W+/);
    
    if (!isJsonOut) console.error(`\n[Orchestrator] Analyzing intent: "${intent}"`);
    
    // 1. Scored Routing based on Keywords
    let bestAgent = "orchestrator";
    let maxScore = 0;
    const scores = {};
    const matchedCapabilities = new Set();

    for (const [agentName, profile] of Object.entries(registry.agents)) {
        let score = 0;
        if (profile.keywords) {
            for (const kw of profile.keywords) {
                // Use exact word boundary matching instead of naive includes
                const regex = new RegExp(`\\b${kw}\\b`, 'i');
                if (regex.test(intentLower)) {
                    score += 1;
                    if (profile.capabilities) {
                        profile.capabilities.forEach(c => matchedCapabilities.add(c));
                    }
                }
            }
        }
        scores[agentName] = score;
        if (score > maxScore) {
            maxScore = score;
            bestAgent = agentName;
        }
    }

    const confidence = maxScore > 0 ? Math.min(maxScore / 5, 1.0) : 0.5;
    
    // Determine supporting agents
    const supportingAgents = [];
    for (const [agentName, score] of Object.entries(scores)) {
        if (score > 0 && agentName !== bestAgent) {
            supportingAgents.push(agentName);
        }
    }

    const agentProfile = registry.agents[bestAgent];
    
    // 2. Risk Assessment
    const riskKeywords = ['login', 'auth', 'password', 'database', 'security', 'crypto', 'core', 'config'];
    let riskLevel = 'low';
    let requiredReviewers = new Set();
    
    for (const rk of riskKeywords) {
        const regex = new RegExp(`\\b${rk}\\b`, 'i');
        if (regex.test(intentLower)) {
            riskLevel = 'high';
            requiredReviewers.add('quality-inspector');
            if (registry.agents['security-auditor']) {
                requiredReviewers.add('security-auditor');
            }
            break;
        }
    }

    // Force reviewers from profile
    if (agentProfile.risk_limits && agentProfile.risk_limits.requires_reviewers) {
        agentProfile.risk_limits.requires_reviewers.forEach(r => requiredReviewers.add(r));
    }

    requiredReviewers = Array.from(requiredReviewers);

    if (!isJsonOut && riskLevel === 'high') {
        console.error(`[Orchestrator] ⚠️ High Risk Task Detected. Required Reviewers: ${requiredReviewers.join(', ')}`);
    }

    // 3. Skills and Workflow
    const requiredSkills = agentProfile.allowed_skills ? agentProfile.allowed_skills.filter(skill => Object.keys(registry.skills).includes(skill)) : [];
    
    // Find matched workflow
    let matchedWorkflow = "task";
    
    // Explicit priority aliases for core system restructuring
    const isRefactorAlias = intentLower.includes('refactor') && (intentLower.includes('system') || intentLower.includes('runtime') || intentLower.includes('core'));
    
    if (isRefactorAlias) {
        matchedWorkflow = "refactor-system";
    } else if (registry.workflows) {
        for (const [wfName, wfData] of Object.entries(registry.workflows)) {
            // Check exact name or space-separated name (e.g. refactor-system vs refactor system)
            if (intentLower.includes(wfName) || intentLower.includes(wfName.replace(/-/g, ' '))) {
                matchedWorkflow = wfName;
                break;
            }
        }
    }

    const routingResult = {
        intent: intent,
        primary_agent: bestAgent,
        supporting_agents: supportingAgents,
        required_reviewers: requiredReviewers,
        risk_level: riskLevel,
        confidence: confidence,
        matched_capabilities: Array.from(matchedCapabilities),
        required_skills: requiredSkills,
        workflow: matchedWorkflow
    };

    if (isJsonOut) {
        console.log(JSON.stringify(routingResult, null, 2));
    } else {
        console.error(`[Orchestrator] Selected Expert: @${bestAgent} (${agentProfile.role})`);
        console.error(`[Orchestrator] Pre-loading skills: ${requiredSkills.join(', ') || 'None'}`);
    }

    return routingResult;
}

// CLI Execution
if (require.main === module) {
    const args = process.argv.slice(2);
    const isJsonOut = args.includes('--json');
    const intentArgs = args.filter(a => a !== '--json');
    
    if (intentArgs.length === 0) {
        console.error("Usage: node orchestrator.js <user_intent> [--json]");
        process.exit(1);
    }
    
    routeAgent(intentArgs.join(' '), isJsonOut);
}

module.exports = { routeAgent };
