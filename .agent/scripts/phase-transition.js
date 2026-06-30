const fs = require('fs');
const path = require('path');

const WORKSPACE_DIR = process.cwd();
const TASK_JSON_PATH = path.join(WORKSPACE_DIR, 'task.json');
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const COOP_FLAG = path.join(STATE_DIR, 'coop-mode.flag');

const PHASE_OWNER = {
  SCOPE:   'planner',
  SCOUT:   'executor',
  DECIDE:  'planner',
  EXECUTE: 'executor',
  REVIEW:  'planner',
  DONE:    'planner'
};

const AGENT_ROLE = {
  'claude-code': 'planner',
  'claude':      'planner',
  'gemini':      'executor',
  'antigravity': 'executor'
};

function readJson(p) {
  if (!fs.existsSync(p)) return null;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

function detectAgent() {
  const env = (process.env.OMNI_AGENT || '').toLowerCase();
  if (AGENT_ROLE[env]) return env;
  return null;
}

function detectRole(agent) {
  if (!agent) return null;
  return AGENT_ROLE[agent] || null;
}

const action = process.argv[2];

if (action === 'check') {
  const task = readJson(TASK_JSON_PATH);
  const flag = readJson(COOP_FLAG);
  const agent = detectAgent();
  const role = detectRole(agent);
  const phase = task ? (task.phase || 'SCOPE') : null;
  const phaseOwner = phase ? PHASE_OWNER[phase] : null;

  const result = {
    coop_active: !!flag,
    planner: flag ? flag.planner : null,
    executor: flag ? flag.executor : null,
    current_agent_env: agent,
    current_role: role,
    task_phase: phase,
    phase_owner: phaseOwner,
    can_write: phaseOwner && role && phaseOwner === role,
    block_reason: null
  };

  if (!flag) {
    result.block_reason = 'Co-op flag absent. Solo-Ninja mode (no phase enforcement).';
  } else if (!agent) {
    result.block_reason = 'OMNI_AGENT env var not set. Cannot determine role. Set OMNI_AGENT=claude-code|gemini.';
  } else if (!task) {
    result.block_reason = 'No task.json yet. Planner must create one (phase=SCOPE).';
  } else if (!result.can_write) {
    result.block_reason = `Phase ${phase} is owned by ${phaseOwner}, but you are ${role}. Wait for handoff.`;
  }

  console.log(JSON.stringify(result, null, 2));
  process.exit(result.can_write ? 0 : 1);

} else if (action === 'next') {
  const task = readJson(TASK_JSON_PATH);
  if (!task) { console.error('No task.json'); process.exit(1); }
  const phase = task.phase || 'SCOPE';
  const TRANSITIONS = {
    SCOPE: 'SCOUT', SCOUT: 'DECIDE', DECIDE: 'EXECUTE',
    EXECUTE: 'REVIEW', REVIEW: 'DONE', DONE: 'DONE'
  };
  console.log(JSON.stringify({
    current: phase,
    next: TRANSITIONS[phase],
    owner_now: PHASE_OWNER[phase],
    owner_next: PHASE_OWNER[TRANSITIONS[phase]]
  }));

} else {
  console.error('Usage: node phase-transition.js <check|next>');
  console.error('  check : show current phase + role + can_write');
  console.error('  next  : show suggested next phase');
  console.error('Env var: OMNI_AGENT=claude-code|gemini');
  process.exit(1);
}
