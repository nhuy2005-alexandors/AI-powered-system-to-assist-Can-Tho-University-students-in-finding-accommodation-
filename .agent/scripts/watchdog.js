const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const STATE_DIR = path.resolve(__dirname, '../state');
const STATE_FILE = path.join(STATE_DIR, 'active-tasks.json');
const LOCK_FILE = path.join(STATE_DIR, 'task.lock');
const ERRORS_FILE = path.resolve(__dirname, '../../ERRORS.md');
const POLL_MS = 5000;
const DEFAULT_MAX_DURATION = 5 * 60 * 1000;

function atomicWrite(targetPath, content) {
  const tmp = `${targetPath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmp, content);
  fs.renameSync(tmp, targetPath);
}

function logError(message) {
  const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 16);
  const safe = String(message).replace(/```/g, '``​`');
  const logEntry = `\n## [${timestamp}] - System Error\n\n- **Type**: Watchdog Action\n- **Severity**: High\n- **File/Location**: \`watchdog.js\`\n- **Agent**: System Watchdog\n- **Error Message**:\n  \`\`\`\n  ${safe}\n  \`\`\`\n- **Status**: Investigating\n\n---\n`;
  try {
    fs.appendFileSync(ERRORS_FILE, logEntry);
  } catch (e) {
    console.error("[Watchdog] Failed to write ERRORS.md:", e.message);
  }
}

function killProcessTree(pid) {
  if (!pid) return { ok: false, reason: 'no-pid' };
  if (process.platform === 'win32') {
    const r = spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { encoding: 'utf8' });
    if (r.status === 0) return { ok: true };
    return { ok: false, reason: (r.stderr || r.stdout || '').trim() || `exit=${r.status}` };
  }
  try {
    process.kill(-pid, 'SIGKILL');
    return { ok: true };
  } catch (e) {
    if (e.code === 'ESRCH') {
      try { process.kill(pid, 'SIGKILL'); return { ok: true }; }
      catch (e2) { return { ok: false, reason: e2.message }; }
    }
    return { ok: false, reason: e.message };
  }
}

function clearLockIfOwnedBy(pid) {
  try {
    if (!fs.existsSync(LOCK_FILE)) return;
    const lockObj = JSON.parse(fs.readFileSync(LOCK_FILE, 'utf8'));
    if (lockObj.pid === pid) {
      fs.unlinkSync(LOCK_FILE);
      console.log(`[Watchdog] Cleared task.lock owned by killed PID=${pid}.`);
    }
  } catch {
    try { fs.unlinkSync(LOCK_FILE); } catch {}
  }
}

function checkTasks() {
  if (!fs.existsSync(STATE_FILE)) return;
  let state;
  try {
    state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  } catch (err) {
    console.error("[Watchdog] Parse state failed:", err.message);
    return;
  }
  if (!state.active_tasks || !Array.isArray(state.active_tasks)) return;

  const now = Date.now();
  let modified = false;

  state.active_tasks = state.active_tasks.filter(task => {
    if (!task.pid || !task.start_time) return true;
    const duration = now - task.start_time;
    const maxDuration = task.max_duration || DEFAULT_MAX_DURATION;
    if (duration <= maxDuration) return true;

    console.log(`[Watchdog] Task ${task.id} (PID=${task.pid}) exceeded ${maxDuration}ms. Killing tree.`);
    const result = killProcessTree(task.pid);
    if (result.ok) {
      logError(`Killed PID=${task.pid} task=${task.id} duration=${duration}ms.`);
      clearLockIfOwnedBy(task.pid);
    } else {
      logError(`Kill failed for PID=${task.pid} task=${task.id}: ${result.reason}`);
    }
    modified = true;
    return false;
  });

  if (modified) {
    try { atomicWrite(STATE_FILE, JSON.stringify(state, null, 2)); }
    catch (err) { console.error("[Watchdog] Persist state failed:", err.message); }
  }
}

console.log(`[Watchdog] Daemon started (PID=${process.pid}). Polling every ${POLL_MS}ms...`);
setInterval(checkTasks, POLL_MS);
