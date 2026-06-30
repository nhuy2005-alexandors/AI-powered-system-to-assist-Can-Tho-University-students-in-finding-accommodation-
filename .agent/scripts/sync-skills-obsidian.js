const fs = require('fs');
const path = require('path');

const WORKSPACE_DIR = 'd:/Dev/Workspaces/Omni_Assistant';
const SOURCE_DIRS = [
    path.join(WORKSPACE_DIR, 'Skills_Library'),
    path.join(WORKSPACE_DIR, '.agent/skills')
];
const OBSIDIAN_VAULT = path.join(WORKSPACE_DIR, 'Obsidian_Vault/Memory/Tech_Stack');
const SKILLS_VAULT_DIR = path.join(OBSIDIAN_VAULT, 'Skills_Vault');

// Refined keywords with more specific targeting
const CATEGORIES = {
    'Frontend & Mobile': ['frontend', 'react', 'mobile', 'tailwind', 'css', 'ios', 'android', 'flutter', 'nextjs', 'vue', 'svelte', 'avalonia', 'ui-ux'],
    'Backend & API': ['backend', 'api', 'database', 'sql', 'postgres', 'nodejs', 'python', 'django', 'fastapi', 'java ', 'csharp', 'go ', 'ruby', 'graphql', 'rest', 'prisma'],
    'Cloud & DevOps': ['cloud', 'devops', 'cicd', 'docker', 'aws', 'azure', 'gcp', 'kubernetes', 'k8s', 'terraform', 'infrastructure', 'deployment', 'serverless', 'github-actions'],
    'AI & Data': [' ai ', '-ai', 'llm', 'data', 'machine learning', 'prompt', 'agent', 'model', 'analytics', 'langchain', 'crewai', 'notebooklm', 'rag', 'vector'],
    'Security': ['security', 'pentest', 'audit', 'vulnerability', 'hacking', 'threat', 'compliance', 'red-team', 'xss', 'sql-injection', 'malware'],
    'Business & Strategy': ['business', 'seo', 'marketing', 'startup', 'sales', 'cro ', 'growth', 'finance', 'market'],
    'Testing & QA': ['testing', 'qa', 'tdd', 'e2e', 'automation', 'playwright', 'cypress', 'unit-test'],
    'Architecture': ['architecture', 'patterns', 'system design', 'c4', 'monorepo', 'microservices', 'event-sourcing', 'cqrs'],
    'Scripts & Tools': ['bash', 'powershell', 'cli', 'linux', 'git', 'terminal', 'mcp']
};

function ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}

function extractFrontmatter(content) {
    const match = content.match(/^---\n([\s\S]*?)\n---/);
    if (!match) return {};
    
    const lines = match[1].split('\n');
    const fm = {};
    lines.forEach(line => {
        const idx = line.indexOf(':');
        if (idx > -1) {
            const key = line.slice(0, idx).trim();
            const val = line.slice(idx + 1).trim();
            fm[key] = val;
        }
    });
    return fm;
}

function extractMainContent(content) {
    // Xóa khối frontmatter YAML
    let mainContent = content.replace(/^---\n([\s\S]*?)\n---/, '').trim();
    // Xóa các khối mã code (để tránh rác file Obsidian)
    mainContent = mainContent.replace(/```[\s\S]*?```/g, '\n[Code Block Bị Lược Bỏ]\n');
    
    // Giới hạn chiều dài khoảng 1200 ký tự để không quá dài
    if (mainContent.length > 1200) {
        return mainContent.substring(0, 1200) + '...\n\n*(Xem thêm chi tiết tại file gốc)*';
    }
    return mainContent;
}

function inferCategory(folderName, content) {
    const textToAnalyze = (' ' + folderName.replace(/-/g, ' ') + ' ' + content).toLowerCase();
    
    let bestCategory = 'Other';
    let maxScore = 0;
    
    for (const [category, keywords] of Object.entries(CATEGORIES)) {
        let score = 0;
        for (const kw of keywords) {
            // Count occurrences of keyword
            const regex = new RegExp(kw.replace(/-/g, '\\-'), 'g');
            const matches = textToAnalyze.match(regex);
            if (matches) {
                score += matches.length;
            }
        }
        if (score > maxScore) {
            maxScore = score;
            bestCategory = category;
        }
    }
    
    return maxScore > 0 ? bestCategory : 'Other';
}

function getSanitizedName(str) {
    return str.replace(/[^a-zA-Z0-9-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
}

async function syncSkills() {
    console.log('Bắt đầu đồng bộ kỹ năng vào Obsidian (v3 - Có chi tiết)...');
    ensureDir(SKILLS_VAULT_DIR);
    
    const categorizedSkills = {};
    Object.keys(CATEGORIES).concat(['Other']).forEach(cat => categorizedSkills[cat] = []);

    let totalProcessed = 0;

    for (const sourceDir of SOURCE_DIRS) {
        if (!fs.existsSync(sourceDir)) continue;
        
        const folders = fs.readdirSync(sourceDir, { withFileTypes: true })
            .filter(dirent => dirent.isDirectory())
            .map(dirent => dirent.name);
            
        for (const folder of folders) {
            const skillPath = path.join(sourceDir, folder);
            const mdPath = path.join(skillPath, 'SKILL.md');
            
            if (!fs.existsSync(mdPath)) continue;
            
            const content = fs.readFileSync(mdPath, 'utf-8');
            const frontmatter = extractFrontmatter(content);
            const category = inferCategory(folder, content);
            const details = extractMainContent(content);
            
            const description = frontmatter.description || frontmatter.name || `Kỹ năng ${folder}`;
            
            const dateStr = new Date().toISOString().split('T')[0];
            const obsidianFileName = `skill-${getSanitizedName(folder)}.md`;
            const obsidianFilePath = path.join(SKILLS_VAULT_DIR, obsidianFileName);
            
            const obsidianContent = `---
aliases: [${folder}]
tags: [#omni-memory, #skill, #category-${getSanitizedName(category).toLowerCase()}]
date: ${dateStr}
---

# ${folder}

## Tóm tắt (Summary)
${description.replace(/^"|"$/g, '')}

## Chi tiết Kỹ năng (Details)
${details}

## Phân loại (Category)
[[401_Skills_${getSanitizedName(category)}_MoC]]

## Link đến nguồn
[${folder}/SKILL.md](file:///${mdPath.replace(/\\/g, '/')})
`;
            
            fs.writeFileSync(obsidianFilePath, obsidianContent);
            categorizedSkills[category].push({ name: folder, file: obsidianFileName });
            totalProcessed++;
        }
    }
    
    const rootMoCPath = path.join(OBSIDIAN_VAULT, '400_Skills_MoC.md');
    let rootMoCContent = `# 400 - Map of Content: Skills Library\n\nTổng hợp toàn bộ ${totalProcessed} kỹ năng đã được lưu trữ trong hệ thống Omni Assistant.\n\n## Danh mục các lĩnh vực\n\n`;
    
    for (const [category, skills] of Object.entries(categorizedSkills)) {
        if (skills.length === 0) continue;
        
        const catFileName = `401_Skills_${getSanitizedName(category)}_MoC.md`;
        const catFilePath = path.join(OBSIDIAN_VAULT, catFileName);
        
        rootMoCContent += `- [[${catFileName.replace('.md', '')}]] (${skills.length} skills)\n`;
        
        let catContent = `# ${category} Skills MoC\n\nDanh sách các kỹ năng thuộc lĩnh vực **${category}**.\n\n## Danh sách Kỹ năng\n\n`;
        skills.sort((a, b) => a.name.localeCompare(b.name)).forEach(skill => {
            catContent += `- [[${skill.file.replace('.md', '')}]] - ${skill.name}\n`;
        });
        
        fs.writeFileSync(catFilePath, catContent);
    }
    
    fs.writeFileSync(rootMoCPath, rootMoCContent);
    console.log(`Đã đồng bộ thành công ${totalProcessed} kỹ năng vào Obsidian!`);
}

syncSkills().catch(console.error);
