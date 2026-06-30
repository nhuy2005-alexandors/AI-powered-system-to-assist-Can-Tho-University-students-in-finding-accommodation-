const fs = require('fs');
const path = require('path');
const os = require('os');

const WORKSPACE_DIR = process.cwd();
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const FLAG_PATH = path.join(STATE_DIR, 'coop-mode.flag');

function ensureStateDir() {
  if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });
}

function atomicWrite(targetPath, content) {
  const tmp = `${targetPath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmp, content);
  fs.renameSync(tmp, targetPath);
}

const action = process.argv[2];

if (action === 'set') {
  ensureStateDir();
  const planner = process.argv[3] || process.env.OMNI_AGENT || 'claude-code';
  const payload = {
    active: true,
    planner,
    executor: 'gemini',
    set_at: new Date().toISOString(),
    set_by_pid: process.pid,
    host: os.hostname()
  };
  atomicWrite(FLAG_PATH, JSON.stringify(payload, null, 2));
  console.log(`Co-op mode ACTIVE. Planner=${planner}, Executor=gemini.`);
} else if (action === 'clear') {
  if (fs.existsSync(FLAG_PATH)) fs.unlinkSync(FLAG_PATH);
  console.log("Co-op mode CLEARED. Solo-Ninja restored.");
} else if (action === 'status') {
  if (!fs.existsSync(FLAG_PATH)) {
    console.log(JSON.stringify({ active: false, mode: 'solo-ninja' }));
  } else {
    try {
      const data = JSON.parse(fs.readFileSync(FLAG_PATH, 'utf8'));
      console.log(JSON.stringify({ ...data, mode: 'co-op' }));
    } catch (e) {
      console.log(JSON.stringify({ active: false, error: 'corrupt flag', detail: e.message }));
    }
  }
} else {
  console.error("Usage: node coop-mode.js <set|clear|status> [planner]");
  process.exit(1);
}
