const fs = require('fs');
const path = require('path');
const os = require('os');

const WORKSPACE_DIR = process.cwd();
const TASK_JSON_PATH = path.join(WORKSPACE_DIR, 'task.json');
const TASK_MD_PATH = path.join(WORKSPACE_DIR, 'task.md');
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const LOCK_PATH = path.join(STATE_DIR, 'task.lock');
const STALE_MS = 10 * 60 * 1000;

const VALID_PHASES = ['SCOPE', 'SCOUT', 'DECIDE', 'EXECUTE', 'REVIEW', 'DONE'];
const PHASE_TRANSITIONS = {
  SCOPE:   ['SCOUT', 'EXECUTE'],
  SCOUT:   ['DECIDE', 'REVIEW'],
  DECIDE:  ['EXECUTE', 'SCOUT'],
  EXECUTE: ['REVIEW', 'DONE'],
  REVIEW:  ['EXECUTE', 'DONE', 'SCOUT'],
  DONE:    []
};

const PHASE_OWNER = {
  SCOPE:   'planner',
  SCOUT:   'executor',
  DECIDE:  'planner',
  EXECUTE: 'executor',
  REVIEW:  'planner',
  DONE:    'planner'
};

function ensureStateDir() {
  if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });
}

function atomicWrite(targetPath, content) {
  const tmp = `${targetPath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tmp, content);
  fs.renameSync(tmp, targetPath);
}

function readLock() {
  if (!fs.existsSync(LOCK_PATH)) return null;
  try {
    return JSON.parse(fs.readFileSync(LOCK_PATH, 'utf8'));
  } catch {
    return { pid: 0, ts: 0, owner: 'corrupt' };
  }
}

function isLockStale(lockObj) {
  if (!lockObj) return true;
  if (Date.now() - (lockObj.ts || 0) > STALE_MS) return true;
  if (lockObj.pid && lockObj.pid !== process.pid) {
    try {
      process.kill(lockObj.pid, 0);
      return false;
    } catch (e) {
      return e.code === 'ESRCH';
    }
  }
  return false;
}

function readPrior() {
  if (!fs.existsSync(TASK_JSON_PATH)) return null;
  try {
    return JSON.parse(fs.readFileSync(TASK_JSON_PATH, 'utf8'));
  } catch {
    return null;
  }
}

function validatePhaseTransition(prior, next) {
  if (!prior) return { ok: true };
  const prevPhase = prior.phase || 'SCOPE';
  const nextPhase = next.phase || prevPhase;
  if (prevPhase === nextPhase) return { ok: true };
  if (!VALID_PHASES.includes(nextPhase)) {
    return { ok: false, reason: `Invalid phase '${nextPhase}'. Allowed: ${VALID_PHASES.join(',')}` };
  }
  const allowed = PHASE_TRANSITIONS[prevPhase] || [];
  if (!allowed.includes(nextPhase)) {
    return { ok: false, reason: `Illegal transition ${prevPhase} -> ${nextPhase}. Allowed next: [${allowed.join(',')}]` };
  }
  return { ok: true };
}

function validatePhaseInvariants(payload) {
  const phase = payload.phase || 'SCOPE';
  const errs = [];

  if (phase === 'DECIDE' || phase === 'EXECUTE') {
    if (!payload.findings || String(payload.findings).trim().length === 0) {
      errs.push(`Phase ${phase} requires non-empty 'findings' (Scout output).`);
    }
  }
  if (phase === 'EXECUTE') {
    if (!Array.isArray(payload.decisions) || payload.decisions.length === 0) {
      errs.push(`Phase EXECUTE requires non-empty 'decisions[]' from Planner.`);
    }
  }
  if (phase === 'DONE') {
    if (!payload.evidence || String(payload.evidence).trim().length === 0) {
      errs.push(`Phase DONE requires 'evidence' (terminal log / artifact path).`);
    }
    if (Array.isArray(payload.acceptance)) {
      const undone = payload.acceptance.filter(a => !a.done);
      if (undone.length > 0) errs.push(`Phase DONE has ${undone.length} unchecked acceptance items.`);
    }
  }
  return errs;
}

function compressionGuard(payload) {
  const warnings = [];
  if (payload.findings) {
    const len = String(payload.findings).length;
    if (len > 1500) warnings.push(`findings is ${len} chars (>1500). Compression mandate violated.`);
  }
  return warnings;
}

function renderMarkdown(taskObj) {
  const phase = taskObj.phase || 'SCOPE';
  const owner = PHASE_OWNER[phase] || '?';
  let md = `# Master Task Document (Auto-rendered from task.json)\n\n`;
  md += `## Task ID\n${taskObj.task_id || 'N/A'}\n\n`;
  md += `## Phase\n**${phase}** (owner: ${owner})\n\n`;
  md += `## Spec\n${taskObj.spec || 'N/A'}\n\n`;

  if (Array.isArray(taskObj.investigate_targets) && taskObj.investigate_targets.length > 0) {
    md += `## Investigate Targets (Scout TODO)\n`;
    taskObj.investigate_targets.forEach((t, i) => { md += `${i + 1}. ${t}\n`; });
    md += `\n`;
  }

  if (taskObj.findings) {
    md += `## Findings (Scout output - compressed)\n${taskObj.findings}\n\n`;
  }

  if (Array.isArray(taskObj.decisions) && taskObj.decisions.length > 0) {
    md += `## Decisions (Planner)\n`;
    taskObj.decisions.forEach((d, i) => { md += `${i + 1}. ${d}\n`; });
    md += `\n`;
  }

  md += `## Acceptance\n`;
  if (Array.isArray(taskObj.acceptance) && taskObj.acceptance.length > 0) {
    taskObj.acceptance.forEach(item => {
      const checkbox = item.done ? '[x]' : '[ ]';
      md += `- ${checkbox} ${item.desc}\n`;
    });
  } else {
    md += `*None*\n`;
  }
  md += `\n## Status\n${taskObj.status || 'Chưa bắt đầu'}\n\n`;
  md += `## Evidence\n${taskObj.evidence || 'None'}\n`;
  return md;
}

const action = process.argv[2];

if (action === 'write') {
  ensureStateDir();
  try {
    const payload = JSON.parse(process.argv[3]);
    const force = process.argv.includes('--force');

    const prior = readPrior();
    const transition = validatePhaseTransition(prior, payload);
    if (!transition.ok && !force) {
      console.error(`[Phase] ${transition.reason} (use --force to override)`);
      process.exit(3);
    }

    const errs = validatePhaseInvariants(payload);
    if (errs.length > 0 && !force) {
      console.error(`[Phase] Invariant violations:\n  - ${errs.join('\n  - ')}\n(use --force to override)`);
      process.exit(4);
    }

    const warnings = compressionGuard(payload);
    if (warnings.length > 0) {
      warnings.forEach(w => console.warn(`[!] ${w}`));
    }

    const lock = readLock();
    if (lock && !isLockStale(lock) && lock.pid !== process.pid) {
      console.error(`Task locked by PID=${lock.pid} owner=${lock.owner} since ${new Date(lock.ts).toISOString()}. Refusing write.`);
      process.exit(2);
    }
    if (lock && isLockStale(lock)) {
      console.warn(`[!] Stale lock detected (PID=${lock.pid}). Reclaiming.`);
      try { fs.unlinkSync(LOCK_PATH); } catch {}
    }
    atomicWrite(TASK_JSON_PATH, JSON.stringify(payload, null, 2));
    atomicWrite(TASK_MD_PATH, renderMarkdown(payload));
    console.log(`Task written. Phase=${payload.phase || 'SCOPE'} owner=${PHASE_OWNER[payload.phase || 'SCOPE']}.`);
  } catch (e) {
    console.error("Failed to write task:", e.message);
    process.exit(1);
  }
} else if (action === 'read') {
  try {
    if (fs.existsSync(TASK_JSON_PATH)) {
      console.log(fs.readFileSync(TASK_JSON_PATH, 'utf8'));
    } else {
      console.log(JSON.stringify({ error: "task.json not found" }));
    }
  } catch (e) {
    console.error("Failed to read task:", e.message);
    process.exit(1);
  }
} else if (action === 'phase') {
  const prior = readPrior();
  if (!prior) {
    console.log(JSON.stringify({ phase: null, owner: null, error: 'no task.json' }));
  } else {
    const phase = prior.phase || 'SCOPE';
    console.log(JSON.stringify({
      phase,
      owner: PHASE_OWNER[phase],
      next_allowed: PHASE_TRANSITIONS[phase] || [],
      status: prior.status
    }));
  }
} else if (action === 'lock') {
  ensureStateDir();
  const isLock = process.argv[3] === 'true';
  if (isLock) {
    const existing = readLock();
    if (existing && !isLockStale(existing) && existing.pid !== process.pid) {
      console.error(`Lock held by PID=${existing.pid}. Use force-unlock if stuck.`);
      process.exit(2);
    }
    const owner = process.env.OMNI_AGENT || os.userInfo().username || 'unknown';
    atomicWrite(LOCK_PATH, JSON.stringify({ pid: process.pid, ts: Date.now(), owner }));
    console.log(`Task locked by PID=${process.pid} owner=${owner}.`);
  } else {
    if (fs.existsSync(LOCK_PATH)) fs.unlinkSync(LOCK_PATH);
    console.log("Task unlocked.");
  }
} else if (action === 'force-unlock') {
  if (fs.existsSync(LOCK_PATH)) fs.unlinkSync(LOCK_PATH);
  console.log("Lock force-removed.");
} else {
  console.error("Usage: node task-manager.js <read|write|phase|lock|force-unlock> [payload|true/false] [--force]");
  process.exit(1);
}
