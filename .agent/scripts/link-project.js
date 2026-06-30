const fs = require('fs');
const path = require('path');

const targetPath = process.argv[2];
const isUpdate = process.argv.includes('--update');

if (!targetPath || targetPath === '--update') {
  console.error("Lỗi: Yêu cầu cung cấp đường dẫn dự án đích.");
  console.log("Usage: node link-project.js <target_path> [--update]");
  process.exit(1);
}

const BRAIN_ROOT = path.resolve(__dirname, '../..');
const targetDir = path.resolve(targetPath);
const isSelfLink = targetDir === BRAIN_ROOT;

if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
  console.log(`[+] Đã tạo thư mục dự án mới: ${targetDir}`);
}

const omniMcpPath = path.resolve(__dirname, '../mcp-servers/omni-mcp/index.js').replace(/\\/g, '/');
const mcpConfig = {
  mcpServers: {
    "omni-assistant": { command: "node", args: [omniMcpPath] }
  }
};
const mcpDest = path.join(targetDir, '.mcp.json');
if (!fs.existsSync(mcpDest) || isUpdate) {
  fs.writeFileSync(mcpDest, JSON.stringify(mcpConfig, null, 2));
  console.log(`[+] Đã ${isUpdate ? 'cập nhật' : 'khởi tạo'} .mcp.json`);
}

function syncFile(src, dest) {
  if (path.resolve(src) === path.resolve(dest)) {
    return { mode: 'skip-self' };
  }
  if (fs.existsSync(dest)) {
    if (!isUpdate) {
      console.log(`[i] Bỏ qua ${path.basename(dest)} (dùng --update để ghi đè).`);
      return { mode: 'skip-exists' };
    }
    fs.unlinkSync(dest);
  }
  try {
    fs.linkSync(src, dest);
    console.log(`[+] Đã Hardlink ${path.basename(dest)}`);
    return { mode: 'hardlink' };
  } catch (err) {
    if (err.code === 'EXDEV' || err.code === 'EPERM') {
      fs.copyFileSync(src, dest);
      console.warn(`[!] Fallback copy cho ${path.basename(dest)} (${err.code}).`);
      return { mode: 'copy-fallback' };
    }
    console.error(`[-] Lỗi link:`, err.message);
    return { mode: 'failed', reason: err.message };
  }
}

function syncDir(src, dest) {
  if (path.resolve(src) === path.resolve(dest)) return;
  if (fs.existsSync(dest)) {
    if (!isUpdate) return;
    try { fs.unlinkSync(dest); } catch { try { fs.rmSync(dest, { recursive: true, force: true }); } catch {} }
  }
  try {
    fs.symlinkSync(src, dest, 'junction');
    console.log(`[+] Đã Junction Directory ${path.basename(dest)}`);
  } catch (err) {
    console.error(`[-] Lỗi link Directory ${path.basename(dest)}:`, err.message);
  }
}

const geminiSrc = path.resolve(BRAIN_ROOT, 'GEMINI.md');
const geminiDest = path.join(targetDir, 'GEMINI.md');
let linkResult = null;
if (fs.existsSync(geminiSrc)) {
  linkResult = syncFile(geminiSrc, geminiDest);
} else {
  console.warn(`[!] Không tìm thấy GEMINI.md tại ${geminiSrc}`);
}

// Sync Directory Junctions
const agentDir = path.join(targetDir, '.agent');
if (!fs.existsSync(agentDir)) fs.mkdirSync(agentDir, { recursive: true });

['rules', 'skills', 'workflows', 'scripts'].forEach(dirName => {
  const src = path.join(BRAIN_ROOT, '.agent', dirName);
  const dest = path.join(agentDir, dirName);
  if (fs.existsSync(src)) syncDir(src, dest);
});

const taskTemplate = {
  task_id: "AUTO-GENERATED/ASSIGNED",
  phase: "SCOPE",
  spec: "Mô tả chi tiết yêu cầu kỹ thuật, luồng logic, và giới hạn",
  investigate_targets: [],
  findings: "",
  decisions: [],
  acceptance: [
    { desc: "Criteria 1", done: false },
    { desc: "Criteria 2", done: false }
  ],
  status: "Chưa bắt đầu",
  evidence: "Link đến PR, Log Output, hoặc Artifact chứng minh task đã hoạt động"
};
const taskDest = path.join(targetDir, 'task.json');
if (!fs.existsSync(taskDest) || isUpdate) {
  fs.writeFileSync(taskDest, JSON.stringify(taskTemplate, null, 2));
  console.log(`[+] Đã ${isUpdate ? 'cập nhật' : 'tạo'} task.json skeleton (phase-aware)`);
}

const stateDir = path.join(targetDir, '.agent', 'state');
if (!fs.existsSync(stateDir)) {
  fs.mkdirSync(stateDir, { recursive: true });
  console.log(`[+] Đã khởi tạo .agent/state/`);
}

// Seed executor-mode.json (per-limb, copy not link - operators may override locally)
const execModeSrc = path.join(BRAIN_ROOT, '.agent', 'schemas', 'executor-mode.template.json');
const execModeDest = path.join(stateDir, 'executor-mode.json');
if (fs.existsSync(execModeSrc) && (!fs.existsSync(execModeDest) || isUpdate)) {
  fs.copyFileSync(execModeSrc, execModeDest);
  console.log(`[+] Đã ${isUpdate ? 'cập nhật' : 'tạo'} executor-mode.json (mode=ide default)`);
}

// Deploy convenience wrappers (cmd for Windows, sh for bash/POSIX)
const wrappers = [
  { src: 'omni-coop.cmd.template', dest: 'omni-coop.cmd' },
  { src: 'omni-coop.sh.template',  dest: 'omni-coop.sh' }
];
for (const w of wrappers) {
  const wSrc = path.join(BRAIN_ROOT, '.agent', 'schemas', w.src);
  const wDest = path.join(targetDir, w.dest);
  if (fs.existsSync(wSrc) && (!fs.existsSync(wDest) || isUpdate)) {
    fs.copyFileSync(wSrc, wDest);
    if (w.dest.endsWith('.sh')) {
      try { fs.chmodSync(wDest, 0o755); } catch {}
    }
    console.log(`[+] Đã deploy wrapper ${w.dest}`);
  }
}

const registryPath = path.join(BRAIN_ROOT, '.agent', 'state', 'linked-projects.json');
let registry = { projects: [] };
if (fs.existsSync(registryPath)) {
  try { registry = JSON.parse(fs.readFileSync(registryPath, 'utf8')); }
  catch { registry = { projects: [] }; }
}
const idx = registry.projects.findIndex(p => path.resolve(p.path) === targetDir);
const entry = {
  path: targetDir,
  linked_at: new Date().toISOString(),
  link_mode: linkResult ? linkResult.mode : 'unknown',
  is_self: isSelfLink
};
if (idx >= 0) registry.projects[idx] = entry;
else registry.projects.push(entry);
fs.writeFileSync(registryPath, JSON.stringify(registry, null, 2));
console.log(`[+] Registry updated: ${registryPath}`);

console.log('✅ Hoàn tất liên kết Brain-Limb!');
