const fs = require('fs');
const path = require('path');

const WORKSPACE_DIR = process.cwd();
const TASK_JSON = path.join(WORKSPACE_DIR, 'task.json');
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const ACTIVE_TASKS = path.join(STATE_DIR, 'active-tasks.json');
const SCOUT_LOG = path.join(STATE_DIR, 'scout.log');
const MODE_FILE = path.join(STATE_DIR, 'executor-mode.json');

const DEFAULT_TIMEOUT_MS = 5 * 60 * 1000;
const POLL_MS = 2000;

const PHASE_OWNER = {
  SCOPE:   'planner',
  SCOUT:   'executor',
  DECIDE:  'planner',
  EXECUTE: 'executor',
  REVIEW:  'planner',
  DONE:    'planner'
};

function readJson(p) {
  if (!fs.existsSync(p)) return null;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

function isScoutAlive(pid) {
  if (!pid) return false;
  try { process.kill(pid, 0); return true; }
  catch (e) { return e.code !== 'ESRCH'; }
}

function getScoutPid() {
  const state = readJson(ACTIVE_TASKS);
  if (!state || !Array.isArray(state.active_tasks)) return null;
  const scout = state.active_tasks.find(t => t.kind === 'scout');
  return scout ? scout.pid : null;
}

const waitFor = process.argv[2] || 'planner';
const timeoutMs = parseInt(process.argv[3], 10) || DEFAULT_TIMEOUT_MS;
const start = Date.now();

const modeCfg = readJson(MODE_FILE);
const isIdeMode = modeCfg && modeCfg.mode === 'ide';

console.error(`[await] Waiting for handoff to '${waitFor}' (timeout=${timeoutMs}ms, mode=${isIdeMode ? 'ide' : 'cli'})...`);

const interval = setInterval(() => {
  const task = readJson(TASK_JSON);
  const elapsed = Date.now() - start;

  if (!task) {
    if (elapsed > timeoutMs) {
      clearInterval(interval);
      console.error('[await] Timeout: no task.json appeared.');
      process.exit(2);
    }
    return;
  }

  const phase = task.phase || 'SCOPE';
  const owner = PHASE_OWNER[phase];

  if (owner === waitFor) {
    clearInterval(interval);
    const result = {
      handoff: true,
      phase,
      owner,
      task_id: task.task_id,
      status: task.status,
      findings_len: task.findings ? task.findings.length : 0,
      decisions_count: Array.isArray(task.decisions) ? task.decisions.length : 0,
      acceptance_done: Array.isArray(task.acceptance)
        ? task.acceptance.filter(a => a.done).length + '/' + task.acceptance.length
        : 'n/a',
      evidence_len: task.evidence ? task.evidence.length : 0,
      elapsed_ms: elapsed
    };
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  }

  const scoutPid = getScoutPid();
  if (!isIdeMode && scoutPid && !isScoutAlive(scoutPid) && owner !== waitFor) {
    clearInterval(interval);
    console.error(`[await] Scout PID=${scoutPid} died before handoff. Phase still ${phase}.`);
    let logTail = '';
    if (fs.existsSync(SCOUT_LOG)) {
      const raw = fs.readFileSync(SCOUT_LOG, 'utf8');
      logTail = raw.split('\n').slice(-10).join('\n');
    }
    console.log(JSON.stringify({
      handoff: false,
      error: 'scout_died',
      phase,
      owner,
      scout_log_tail: logTail
    }, null, 2));
    process.exit(3);
  }

  if (elapsed > timeoutMs) {
    clearInterval(interval);
    console.error(`[await] Timeout: phase=${phase} owner=${owner}, waited ${elapsed}ms.`);
    console.log(JSON.stringify({
      handoff: false,
      error: 'timeout',
      phase,
      owner
    }, null, 2));
    process.exit(4);
  }
}, POLL_MS);
