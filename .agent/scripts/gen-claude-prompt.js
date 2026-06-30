const fs = require('fs');
const path = require('path');

const WORKSPACE_DIR = process.cwd();
const TASK_JSON = path.join(WORKSPACE_DIR, 'task.json');
const TASK_MD = path.join(WORKSPACE_DIR, 'task.md');
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const MODE_FILE = path.join(STATE_DIR, 'executor-mode.json');
const PROMPT_OUT = path.join(STATE_DIR, 'claude-paste-prompt.md');
const COOP_FLAG = path.join(STATE_DIR, 'coop-mode.flag');

function readJson(p) {
  if (!fs.existsSync(p)) return null;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

const CWD_POSIX = WORKSPACE_DIR.replace(/\\/g, '/');

const PHASE_INSTRUCTIONS = {
  SCOPE: `# YOUR JOB: SCOPE phase (Planner = Claude)
You are the Architect. Decompose the user goal into an atomic task with investigate_targets for Gemini (Executor) to scout.

## WORKFLOW
1. Read user goal (below) + current task.md reference.
2. Draft: task_id, spec (scope + constraints), investigate_targets[] (specific grep/scan queries, NOT vague), acceptance[] (exit criteria as {desc, done:false}).
3. Call this exact command in terminal:
\`\`\`bash
cd "${CWD_POSIX}"
OMNI_AGENT=claude node .agent/scripts/task-manager.js write '<json-payload>'
\`\`\`
   Payload fields:
   - "task_id": "OMNI-XXXX"
   - "spec": "<scope + constraints>"
   - "investigate_targets": ["query 1", "query 2", ...]
   - "acceptance": [{"desc": "...", "done": false}, ...]
   - "phase": "SCOUT"
   - "status": "Đang thực thi"
4. After write: STOP. Tell operator to paste gemini-paste-prompt.md (regen it first via gen-gemini-prompt.js).

## FORBIDDEN
- Reading large source files yourself (that burns API tokens — that is Gemini's SCOUT job, free on Google Pro)
- Editing source code (you are Planner, not Executor)
- Vague investigate_targets ("look at the code") — be specific so Gemini returns compressed facts
`,
  DECIDE: `# YOUR JOB: DECIDE phase (Planner = Claude)
Gemini finished SCOUT. Read ONLY the 'Findings' section. Make architectural decisions.

## WORKFLOW
1. Read 'Findings' (compressed, <=1500 chars) in task.md below. Do NOT re-scan the codebase.
2. Based on findings, write decisions[] — concrete, ordered, implementable steps for Gemini.
3. Call this exact command in terminal:
\`\`\`bash
cd "${CWD_POSIX}"
OMNI_AGENT=claude node .agent/scripts/task-manager.js write '<json-payload>'
\`\`\`
   Payload must PRESERVE all prior fields (task_id, spec, investigate_targets, findings, acceptance) AND add/update:
   - "decisions": ["step 1", "step 2", ...]
   - "phase": "EXECUTE"
   - "status": "Đang thực thi"
4. After write: STOP. Tell operator to regen + paste gemini-paste-prompt.md (now EXECUTE).

## FORBIDDEN
- Re-reading source files (findings are your only input — trust the SCOUT)
- Writing code yourself (Gemini executes)
- Empty decisions[] (task-manager rejects EXECUTE without decisions)
`,
  REVIEW: `# YOUR JOB: REVIEW phase (Planner = Claude)
Gemini finished EXECUTE. Read 'Evidence' + acceptance ticks. Verify and close.

## WORKFLOW
1. Read 'Evidence' (<=800 chars) + acceptance[] in task.md below.
2. Verify evidence actually proves each acceptance item. Spot-check via ONE terminal command if needed (e.g. re-run the test, wc -l a file) — keep it cheap.
3. Decide outcome:
   - PASS → set phase=DONE, ensure all acceptance[].done=true, keep evidence.
   - FAIL → set phase=EXECUTE (send back with corrected decisions[]) OR phase=SCOUT (need more recon).
4. Call this exact command:
\`\`\`bash
cd "${CWD_POSIX}"
OMNI_AGENT=claude node .agent/scripts/task-manager.js write '<json-payload>'
\`\`\`
   For DONE: all acceptance done=true + non-empty evidence (task-manager enforces this).
5. Report to user with cost summary (node .agent/scripts/cost-meter.js).

## FORBIDDEN
- Marking DONE without evidence (task-manager exit 4)
- Marking DONE with unchecked acceptance items (task-manager exit 4)
- Re-implementing Gemini's work yourself
`
};

const PLANNER_PHASES = ['SCOPE', 'DECIDE', 'REVIEW'];

function generatePrompt() {
  const task = readJson(TASK_JSON);
  const mode = readJson(MODE_FILE);
  const coopActive = fs.existsSync(COOP_FLAG);

  if (!coopActive) {
    console.error('Co-op flag absent. Run: node .agent/scripts/coop-mode.js set claude-code');
    process.exit(1);
  }
  if (!mode || mode.mode !== 'ide') {
    console.warn('[!] executor-mode.json says mode=' + (mode ? mode.mode : 'unset') + '. Continuing as IDE anyway.');
  }

  const phase = task ? (task.phase || 'SCOPE') : 'SCOPE';
  if (!PLANNER_PHASES.includes(phase)) {
    console.error(`Phase=${phase} not owned by Planner. Expected SCOPE, DECIDE or REVIEW (current owner = executor/Gemini).`);
    process.exit(2);
  }

  const taskMdContent = fs.existsSync(TASK_MD) ? fs.readFileSync(TASK_MD, 'utf8') : '<no task.md yet — this is a fresh SCOPE>';
  const instructions = PHASE_INSTRUCTIONS[phase];

  const fullPrompt = `${instructions}

---

## CURRENT task.md (read-only reference)

${taskMdContent}

---

End of prompt. Begin work now.
`;

  fs.writeFileSync(PROMPT_OUT, fullPrompt);

  console.log(JSON.stringify({
    generated: true,
    phase,
    task_id: task ? task.task_id : '(new)',
    prompt_path: PROMPT_OUT,
    prompt_chars: fullPrompt.length,
    next_step: `Paste ${path.basename(PROMPT_OUT)} into the Claude panel in Antigravity. After Claude calls task-manager.js write, regen the Gemini prompt: node .agent/scripts/gen-gemini-prompt.js`
  }, null, 2));
}

generatePrompt();
