const fs = require('fs');
const path = require('path');

const WORKFLOWS_DIR = path.join(__dirname, '..', 'workflows');

const items = fs.readdirSync(WORKFLOWS_DIR);

let generated = 0;

items.forEach(item => {
    if (item.endsWith('.md')) {
        const baseName = item.replace('.md', '');
        const jsonPath = path.join(WORKFLOWS_DIR, `${baseName}.json`);
        
        if (!fs.existsSync(jsonPath)) {
            const template = {
                "id": baseName,
                "description": `Auto-generated sidecar for ${baseName}`,
                "risk": "low",
                "required_agents": ["orchestrator"],
                "optional_agents": [],
                "required_skills": [],
                "preconditions": [],
                "steps": [
                    {
                        "id": "init",
                        "agent": "orchestrator",
                        "action": "log_init"
                    }
                ],
                "completion_gates": ["all_steps_completed"],
                "memory_policy": "none"
            };
            
            fs.writeFileSync(jsonPath, JSON.stringify(template, null, 2));
            generated++;
            console.log(`Generated: ${baseName}.json`);
        }
    }
});

console.log(`Successfully generated ${generated} sidecars.`);
