const fs = require('fs');
const path = require('path');

const WORKSPACE_DIR = process.cwd();
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const COST_LOG = path.join(STATE_DIR, 'cost-meter.json');

const PHASE_BUDGETS = {
  SCOPE:   1000,
  DECIDE:  2000,
  REVIEW:  1000,
  TOTAL_CLAUDE_PER_TASK: 5000
};

function ensureStateDir() {
  if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });
}

function readLog() {
  if (!fs.existsSync(COST_LOG)) return { tasks: {} };
  try { return JSON.parse(fs.readFileSync(COST_LOG, 'utf8')); } catch { return { tasks: {} }; }
}

function writeLog(data) {
  fs.writeFileSync(COST_LOG, JSON.stringify(data, null, 2));
}

function estimateTokens(charCount) {
  return Math.ceil(charCount / 4);
}

const action = process.argv[2];

if (action === 'log') {
  const taskId = process.argv[3];
  const phase = process.argv[4];
  const charsRead = parseInt(process.argv[5], 10) || 0;
  const charsWritten = parseInt(process.argv[6], 10) || 0;

  if (!taskId || !phase) {
    console.error('Usage: node cost-meter.js log <task_id> <phase> <chars_read> <chars_written>');
    process.exit(1);
  }

  ensureStateDir();
  const log = readLog();
  if (!log.tasks[taskId]) log.tasks[taskId] = { phases: [], total_in: 0, total_out: 0 };

  const tokensIn = estimateTokens(charsRead);
  const tokensOut = estimateTokens(charsWritten);
  log.tasks[taskId].phases.push({
    phase,
    ts: new Date().toISOString(),
    chars_read: charsRead,
    chars_written: charsWritten,
    tokens_in: tokensIn,
    tokens_out: tokensOut
  });
  log.tasks[taskId].total_in += tokensIn;
  log.tasks[taskId].total_out += tokensOut;

  writeLog(log);

  const phaseBudget = PHASE_BUDGETS[phase];
  const totalBudget = PHASE_BUDGETS.TOTAL_CLAUDE_PER_TASK;
  const phaseSum = tokensIn + tokensOut;
  const taskTotal = log.tasks[taskId].total_in + log.tasks[taskId].total_out;

  const warnings = [];
  if (phaseBudget && phaseSum > phaseBudget) {
    warnings.push(`Phase ${phase}: ${phaseSum} tok > budget ${phaseBudget}`);
  }
  if (taskTotal > totalBudget) {
    warnings.push(`Task ${taskId}: ${taskTotal} tok > total budget ${totalBudget}`);
  }

  console.log(JSON.stringify({
    logged: true,
    task_id: taskId,
    phase,
    tokens_in: tokensIn,
    tokens_out: tokensOut,
    phase_total: phaseSum,
    task_total: taskTotal,
    warnings
  }, null, 2));

} else if (action === 'report') {
  const taskId = process.argv[3];
  const log = readLog();

  if (taskId) {
    const t = log.tasks[taskId];
    if (!t) { console.log(JSON.stringify({ error: 'no task' })); process.exit(1); }
    console.log(JSON.stringify({
      task_id: taskId,
      total_in: t.total_in,
      total_out: t.total_out,
      total: t.total_in + t.total_out,
      budget: PHASE_BUDGETS.TOTAL_CLAUDE_PER_TASK,
      pct: (((t.total_in + t.total_out) / PHASE_BUDGETS.TOTAL_CLAUDE_PER_TASK) * 100).toFixed(1) + '%',
      phases: t.phases
    }, null, 2));
  } else {
    const tasks = Object.entries(log.tasks).map(([id, t]) => ({
      id,
      total: t.total_in + t.total_out,
      budget: PHASE_BUDGETS.TOTAL_CLAUDE_PER_TASK,
      over_budget: (t.total_in + t.total_out) > PHASE_BUDGETS.TOTAL_CLAUDE_PER_TASK
    }));
    console.log(JSON.stringify({ tasks, count: tasks.length }, null, 2));
  }

} else if (action === 'budget') {
  console.log(JSON.stringify(PHASE_BUDGETS, null, 2));

} else if (action === 'reset') {
  if (fs.existsSync(COST_LOG)) fs.unlinkSync(COST_LOG);
  console.log('Cost log reset.');

} else {
  console.error('Usage:');
  console.error('  node cost-meter.js log <task_id> <phase> <chars_read> <chars_written>');
  console.error('  node cost-meter.js report [task_id]');
  console.error('  node cost-meter.js budget');
  console.error('  node cost-meter.js reset');
  process.exit(1);
}
