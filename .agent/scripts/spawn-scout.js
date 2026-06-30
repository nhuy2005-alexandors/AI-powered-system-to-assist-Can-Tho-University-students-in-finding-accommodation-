const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const WORKSPACE_DIR = process.cwd();
const TASK_MD = path.join(WORKSPACE_DIR, 'task.md');
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const SCOUT_LOG = path.join(STATE_DIR, 'scout.log');
const SCOUT_PID = path.join(STATE_DIR, 'scout.pid');
const ACTIVE_TASKS = path.join(STATE_DIR, 'active-tasks.json');

function ensureStateDir() {
  if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });
}

function registerActiveTask(pid, taskId) {
  let state = { active_tasks: [], locked_by: null, timestamp: null };
  try {
    if (fs.existsSync(ACTIVE_TASKS)) state = JSON.parse(fs.readFileSync(ACTIVE_TASKS, 'utf8'));
  } catch {}
  state.active_tasks = state.active_tasks.filter(t => t.id !== taskId);
  state.active_tasks.push({
    id: taskId,
    pid,
    start_time: Date.now(),
    max_duration: 5 * 60 * 1000,
    kind: 'scout'
  });
  state.timestamp = Date.now();
  fs.writeFileSync(ACTIVE_TASKS, JSON.stringify(state, null, 2));
}

function readTaskId() {
  try {
    const j = JSON.parse(fs.readFileSync(path.join(WORKSPACE_DIR, 'task.json'), 'utf8'));
    return j.task_id || 'unknown';
  } catch { return 'unknown'; }
}

if (!fs.existsSync(TASK_MD)) {
  console.error('No task.md. Planner must write task.json first.');
  process.exit(1);
}

ensureStateDir();

const taskMdContent = fs.readFileSync(TASK_MD, 'utf8');
const taskId = readTaskId();

const cmd = process.env.GEMINI_CMD || 'gemini';
const args = ['-p', `Read this task and follow GEMINI.md Compression Mandate. Write findings via: node .agent/scripts/task-manager.js write '<json>'. Task:\n\n${taskMdContent}`];

const useApiKey = !!process.env.GEMINI_API_KEY;
if (!useApiKey && !process.env.SCOUT_FORCE) {
  console.error('GEMINI_API_KEY not set. Set it or pass SCOUT_FORCE=1 to attempt OAuth.');
  process.exit(2);
}

const logStream = fs.openSync(SCOUT_LOG, 'w');
const child = spawn(cmd, args, {
  detached: true,
  stdio: ['ignore', logStream, logStream],
  env: { ...process.env, OMNI_AGENT: 'gemini' },
  shell: process.platform === 'win32'
});

fs.writeFileSync(SCOUT_PID, String(child.pid));
registerActiveTask(child.pid, taskId);
child.unref();

console.log(JSON.stringify({
  spawned: true,
  pid: child.pid,
  task_id: taskId,
  log: SCOUT_LOG,
  cmd: `${cmd} ${args[0]} "<task.md>"`
}));
