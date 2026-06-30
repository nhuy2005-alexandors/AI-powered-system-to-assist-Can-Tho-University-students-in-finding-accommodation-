const fs = require('fs');
const path = require('path');

const VAULT_DIR = path.join(__dirname, '../../Obsidian_Vault');

let totalFiles = 0;
let errors = [];

function scanDirectory(dir) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const fullPath = path.join(dir, file);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
            scanDirectory(fullPath);
        } else if (file.endsWith('.md')) {
            lintFile(fullPath);
        }
    }
}

function lintFile(filePath) {
    totalFiles++;
    const content = fs.readFileSync(filePath, 'utf-8');
    
    // Ignore MoC files which might not have full frontmatter
    const fileName = path.basename(filePath);
    if (fileName.includes('MoC') || fileName === '000_Omni_Logs_MoC.md') return;

    const match = content.match(/^---\n([\s\S]*?)\n---/);
    if (!match) {
        errors.push({ file: filePath, issue: 'Thiếu cấu hình YAML Frontmatter hoàn toàn.' });
        return;
    }

    const frontmatter = match[1];
    
    if (!frontmatter.includes('aliases:')) {
        errors.push({ file: filePath, issue: 'Thiếu thuộc tính "aliases" trong YAML.' });
    }
    
    if (!frontmatter.includes('tags:')) {
        errors.push({ file: filePath, issue: 'Thiếu thuộc tính "tags" trong YAML.' });
    }
}

console.log('🔍 Bắt đầu quét và kiểm tra (Linting) toàn bộ Obsidian Vault...');
scanDirectory(VAULT_DIR);

console.log('--------------------------------------------------');
console.log(`Đã kiểm tra tổng cộng: ${totalFiles} files.`);
if (errors.length === 0) {
    console.log('✅ TUYỆT VỜI! Vault của bạn hoàn hảo, không phát hiện lỗi cấu trúc.');
} else {
    console.log(`⚠️ Phát hiện ${errors.length} cảnh báo về cấu trúc:`);
    errors.slice(0, 10).forEach((err, idx) => {
        console.log(`  [${idx + 1}] File: ${path.basename(err.file)}`);
        console.log(`      Lỗi: ${err.issue}`);
    });
    if (errors.length > 10) {
        console.log(`  ... và ${errors.length - 10} file khác.`);
    }
}
console.log('--------------------------------------------------');
