const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.join(__dirname, '..', '..');
const VAULT_DIR = path.join(PROJECT_ROOT, 'Obsidian_Vault');
const MEMORY_DIR = path.join(VAULT_DIR, 'Memory');

const CATEGORIES = {
    'Projects': '100_Projects_MoC.md',
    'Tech_Stack': '200_Tech_Stack_MoC.md',
    'Sessions': '000_Omni_Logs_MoC.md',
    'Research': '300_Research_MoC.md'
};

function parseArgs() {
    const args = process.argv.slice(2);
    const params = {};
    for (let i = 0; i < args.length; i++) {
        if (args[i].startsWith('--')) {
            const key = args[i].substring(2);
            params[key] = args[i + 1] || '';
            i++;
        }
    }
    return params;
}

function sanitizeFilename(name) {
    // Xóa các ký tự cấm trên Windows: \ / : * ? " < > |
    return name.replace(/[\\/:*?"<>|]/g, '-').trim();
}

function ensureStructure() {
    if (!fs.existsSync(MEMORY_DIR)) {
        fs.mkdirSync(MEMORY_DIR, { recursive: true });
    }
    for (const [cat, mocFile] of Object.entries(CATEGORIES)) {
        const catDir = path.join(MEMORY_DIR, cat);
        if (!fs.existsSync(catDir)) {
            fs.mkdirSync(catDir, { recursive: true });
        }
        const mocPath = path.join(MEMORY_DIR, mocFile);
        if (!fs.existsSync(mocPath)) {
            fs.writeFileSync(mocPath, `# ${cat} Map of Content\n\n## Entries\n`, 'utf8');
        }
    }
}

function generateZettelkasten(title, content, tags) {
    const date = new Date().toISOString().split('T')[0];
    const tagString = tags ? tags.split(',').map(t => `#${t.trim()}`).join(', ') : '#omni-memory';
    return `---
aliases: [${title}]
tags: [${tagString}]
date: ${date}
---

# ${title}

${content}

## Liên kết (Related)
`;
}

function appendToMoC(category, filename) {
    const mocFile = CATEGORIES[category];
    if (!mocFile) return;
    
    const mocPath = path.join(MEMORY_DIR, mocFile);
    if (fs.existsSync(mocPath)) {
        fs.appendFileSync(mocPath, `- [[${filename}]]\n`, 'utf8');
        console.log(`[MoC] Đã cập nhật ${mocFile}`);
    }
}

function runSync() {
    const params = parseArgs();
    
    if (!params.title || !params.category || !params.content) {
        console.error("Usage: node memory-sync.js --category <Projects|Tech_Stack|Sessions|Research> --title \"<title>\" --content \"<content>\" [--tags \"tag1,tag2\"]");
        process.exit(1);
    }

    if (!CATEGORIES[params.category]) {
        console.error(`Invalid category. Must be one of: ${Object.keys(CATEGORIES).join(', ')}`);
        process.exit(1);
    }

    ensureStructure();

    const safeTitle = sanitizeFilename(params.title);
    const filename = `${safeTitle}.md`;
    const targetPath = path.join(MEMORY_DIR, params.category, filename);

    const fileContent = generateZettelkasten(params.title, params.content, params.tags);
    
    fs.writeFileSync(targetPath, fileContent, 'utf8');
    console.log(`[Memory Sync] Đã lưu trí nhớ vào: Obsidian_Vault/Memory/${params.category}/${filename}`);

    appendToMoC(params.category, safeTitle); // Obsidian links exclude .md
}

if (require.main === module) {
    runSync();
}

module.exports = { sanitizeFilename, generateZettelkasten };
