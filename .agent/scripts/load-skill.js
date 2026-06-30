const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PROJECT_ROOT = path.join(__dirname, '..', '..');
const AGENT_SKILLS_DIR = path.join(PROJECT_ROOT, '.agent', 'skills');
const LIBRARY_DIR = path.join(PROJECT_ROOT, 'Skills_Library');
const REGISTRY_FILE = path.join(PROJECT_ROOT, '.agent', 'registry.json');

// Recursive hash calculation for a directory
function hashDirectory(dirPath) {
    if (!fs.existsSync(dirPath)) return null;
    
    let files = [];
    function readDir(currentDir) {
        const entries = fs.readdirSync(currentDir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(currentDir, entry.name);
            if (entry.isDirectory()) {
                readDir(fullPath);
            } else {
                files.push(fullPath);
            }
        }
    }
    
    readDir(dirPath);
    files.sort(); // Sort to ensure consistent hashing
    
    const hash = crypto.createHash('sha256');
    for (const file of files) {
        const content = fs.readFileSync(file);
        hash.update(file);
        hash.update(content);
    }
    return hash.digest('hex');
}

function updateRegistry(skillName, metadata) {
    if (!fs.existsSync(REGISTRY_FILE)) return;
    const registry = JSON.parse(fs.readFileSync(REGISTRY_FILE, 'utf8'));
    
    if (!registry.skills) registry.skills = {};
    registry.skills[skillName] = metadata;
    
    fs.writeFileSync(REGISTRY_FILE, JSON.stringify(registry, null, 4));
}

function loadSkill(skillName, options) {
    const sourcePath = path.join(LIBRARY_DIR, skillName);
    const destPath = path.join(AGENT_SKILLS_DIR, skillName);
    const isDryRun = options.includes('--dry-run');
    const isForce = options.includes('--force');

    // 1. Path validation
    if (!fs.existsSync(sourcePath)) {
        console.error(`[Error] Skill '${skillName}' does not exist in Skills_Library.`);
        process.exit(1);
    }

    const skillFile = path.join(sourcePath, 'SKILL.md');
    if (!fs.existsSync(skillFile)) {
        console.error(`[Error] Invalid skill structure: SKILL.md missing in '${skillName}'.`);
        process.exit(1);
    }

    // 2. Hash Calculation
    const newDirHash = hashDirectory(sourcePath);
    let newSkillHash = crypto.createHash('sha256').update(fs.readFileSync(skillFile)).digest('hex');

    // 3. Compare with Registry
    let currentDirHash = null;
    if (fs.existsSync(REGISTRY_FILE)) {
        const registry = JSON.parse(fs.readFileSync(REGISTRY_FILE, 'utf8'));
        if (registry.skills && registry.skills[skillName]) {
            currentDirHash = registry.skills[skillName].directory_hash;
        }
    }

    if (!isForce && currentDirHash === newDirHash && fs.existsSync(destPath)) {
        console.log(`[No-Op] Skill '${skillName}' is already up-to-date (Hash matched).`);
        process.exit(0);
    }

    if (isDryRun) {
        console.log(`[Dry-Run] Would load skill '${skillName}' (Hash: ${newDirHash.substring(0, 8)}) into runtime context.`);
        process.exit(0);
    }

    // 4. Execution
    if (fs.existsSync(destPath)) {
        fs.rmSync(destPath, { recursive: true, force: true });
    }
    fs.cpSync(sourcePath, destPath, { recursive: true });
    
    const metadata = {
        source: `.agent/skills/${skillName}`,
        loaded_at: new Date().toISOString(),
        skill_hash: newSkillHash,
        directory_hash: newDirHash,
        status: "loaded"
    };

    updateRegistry(skillName, metadata);
    console.log(`[Success] Skill '${skillName}' has been loaded. Metadata written to registry.`);
}

// CLI Execution
if (require.main === module) {
    const args = process.argv.slice(2);
    const options = args.filter(a => a.startsWith('--'));
    const positional = args.filter(a => !a.startsWith('--'));

    if (positional.length !== 1) {
        console.log("Usage: node load-skill.js <skill-name> [--dry-run] [--force]");
        process.exit(1);
    }
    loadSkill(positional[0], options);
}

module.exports = { loadSkill };
