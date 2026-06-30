const fs = require('fs');
const path = require('path');

const AGENT_DIR = path.join(__dirname, '..');
const REGISTRY_FILE = path.join(AGENT_DIR, 'registry.json');

function scanDirectory(dirPath, isWorkflow = false) {
    if (!fs.existsSync(dirPath)) return [];
    const items = fs.readdirSync(dirPath);
    const result = [];
    
    items.forEach(item => {
        const fullPath = path.join(dirPath, item);
        const stat = fs.statSync(fullPath);
        
        if (isWorkflow && stat.isFile() && item.endsWith('.md')) {
            result.push(item.replace('.md', ''));
        } else if (!isWorkflow && stat.isDirectory()) {
            result.push(item);
        }
    });
    return result;
}

function scanAgents() {
    const agentsDir = path.join(AGENT_DIR, 'agents');
    if (!fs.existsSync(agentsDir)) return {};
    
    const items = fs.readdirSync(agentsDir);
    const agents = {};
    
    items.forEach(item => {
        if (item.endsWith('.json')) {
            try {
                const fullPath = path.join(agentsDir, item);
                const data = JSON.parse(fs.readFileSync(fullPath, 'utf8'));
                if (data.id) {
                    agents[data.id] = data;
                }
            } catch (e) {
                console.error(`Error parsing agent manifest: ${item}`, e);
            }
        }
    });
    
    return agents;
}

function buildRegistry() {
    console.log('Building machine-readable registry...');
    
    // Load existing registry to preserve metadata
    let existingRegistry = {};
    if (fs.existsSync(REGISTRY_FILE)) {
        try {
            existingRegistry = JSON.parse(fs.readFileSync(REGISTRY_FILE, 'utf8'));
        } catch (e) {
            console.warn('Could not parse existing registry.json. Starting fresh.');
        }
    }
    const currentSkills = scanDirectory(path.join(AGENT_DIR, 'skills'));
    
    const crypto = require('crypto');
    function computeFileHash(filePath) {
        if (!fs.existsSync(filePath)) return "unknown";
        return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
    }
    
    function computeDirHash(dirPath) {
        if (!fs.existsSync(dirPath)) return "unknown";
        const files = fs.readdirSync(dirPath);
        let hash = crypto.createHash('sha256');
        files.sort().forEach(file => {
            const fullPath = path.join(dirPath, file);
            if (fs.statSync(fullPath).isFile()) {
                hash.update(fs.readFileSync(fullPath));
            }
        });
        return hash.digest('hex');
    }

    // Preserve skill metadata or initialize
    const skillsObj = {};
    currentSkills.forEach(skillName => {
        const skillDir = path.join(AGENT_DIR, 'skills', skillName);
        const skillHash = computeFileHash(path.join(skillDir, 'SKILL.md'));
        const dirHash = computeDirHash(skillDir);
        
        skillsObj[skillName] = {
            source: `.agent/skills/${skillName}`,
            loaded_at: new Date().toISOString(),
            skill_hash: skillHash,
            directory_hash: dirHash,
            status: "loaded"
        };
    });

    // Load workflow metadata if JSON sidecars exist
    const workflowsObj = {};
    const workflowNames = scanDirectory(path.join(AGENT_DIR, 'workflows'), true);
    
    workflowNames.forEach(wf => {
        const jsonPath = path.join(AGENT_DIR, 'workflows', `${wf}.json`);
        if (fs.existsSync(jsonPath)) {
            try {
                workflowsObj[wf] = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
            } catch (e) {
                workflowsObj[wf] = { status: "invalid_json" };
            }
        } else {
            workflowsObj[wf] = {
                id: wf,
                description: "Legacy text-only workflow",
                status: "needs_metadata"
            };
        }
    });

    const agents = scanAgents();

    const registry = {
        "version": "2.0",
        "last_updated": new Date().toISOString(),
        "agents": agents,
        "skills": skillsObj,
        "workflows": workflowsObj,
        "metadata": {
            "total_agents": Object.keys(agents).length,
            "total_skills": currentSkills.length,
            "total_workflows": workflowNames.length
        }
    };

    fs.writeFileSync(REGISTRY_FILE, JSON.stringify(registry, null, 4));
    console.log(`Registry built successfully: ${currentSkills.length} skills, ${workflowNames.length} workflows, ${Object.keys(agents).length} agents.`);
}

buildRegistry();
