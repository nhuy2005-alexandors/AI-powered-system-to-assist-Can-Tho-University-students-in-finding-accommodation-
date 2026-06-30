const fs = require('fs');
const path = require('path');

const WORKSPACE_DIR = process.cwd();
const TASK_JSON = path.join(WORKSPACE_DIR, 'task.json');
const TASK_MD = path.join(WORKSPACE_DIR, 'task.md');
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const MODE_FILE = path.join(STATE_DIR, 'executor-mode.json');
const PROMPT_OUT = path.join(STATE_DIR, 'gemini-paste-prompt.md');
const COOP_FLAG = path.join(STATE_DIR, 'coop-mode.flag');

function readJson(p) {
  if (!fs.existsSync(p)) return null;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

const PHASE_INSTRUCTIONS = {
  SCOUT: `# YOUR JOB: SCOUT phase
Read task.md. For each item in 'Investigate Targets', scan codebase and produce ONE compressed fact per line.

## COMPRESSION MANDATE (mandatory)
- TOTAL output (findings field) <= 1500 chars
- Each line format: \`path/to/file.ext:LINE: <fact>. <impact>.\`
- NO filler words: drop "I looked at", "Looking at", "basically", "actually"
- NO code blocks > 5 lines
- If no match: \`no_match: <original query>\`
- ONE fact per line (split multi-fact files into multi-line)

## WORKFLOW
1. Read full task.md (already pasted below)
2. For each investigate_target: grep/scan codebase, extract file:line facts
3. Compose 'findings' string (<= 1500 chars)
4. Call this exact command in terminal (Antigravity has terminal access):
\`\`\`bash
cd "${WORKSPACE_DIR.replace(/\\/g, '/')}"
OMNI_AGENT=gemini node .agent/scripts/task-manager.js write '<your-json-payload>'
\`\`\`
   The JSON must preserve all original fields (task_id, spec, investigate_targets, acceptance) AND add:
   - "findings": "<your compressed string>"
   - "phase": "DECIDE"
   - "status": "Chờ review"

5. After write succeeds: STOP. Do NOT proceed to EXECUTE.

## FORBIDDEN
- Editing source code (this is SCOUT, not EXECUTE)
- Skipping the task-manager.js write (Claude won't see findings otherwise)
- Verbose explanations to user (they're not the audience; Claude is)
`,
  EXECUTE: `# YOUR JOB: EXECUTE phase
Read task.md. The 'Decisions' section has Claude's plan. Implement it.

## WORKFLOW
1. Read 'Decisions' section in task.md (already pasted below)
2. Apply each decision as a code change (edit files, run tests, etc.)
3. After all decisions applied:
   - Verify with terminal commands (npm test, lint, etc.)
   - Capture evidence (test output, file paths, log snippets) <= 800 chars
4. Call this exact command in terminal:
\`\`\`bash
cd "${WORKSPACE_DIR.replace(/\\/g, '/')}"
OMNI_AGENT=gemini node .agent/scripts/task-manager.js write '<json-payload>'
\`\`\`
   Payload must include:
   - All original fields preserved
   - "acceptance": [{"desc": "...", "done": true}, ...]  // tick every item you completed
   - "evidence": "<<= 800 char proof: test output, file changes, log lines>"
   - "phase": "REVIEW"
   - "status": "Chờ review"

5. After write: STOP. Claude does final REVIEW.

## FORBIDDEN
- Adding features beyond decisions[]
- Skipping evidence (Claude rejects empty evidence)
- Marking acceptance done without actual verification
- Re-doing investigate_targets (that was SCOUT)
`
};

function generatePrompt() {
  const task = readJson(TASK_JSON);
  const mode = readJson(MODE_FILE);
  const coopActive = fs.existsSync(COOP_FLAG);

  if (!task) {
    console.error('No task.json. Planner must write one first.');
    process.exit(1);
  }
  if (!coopActive) {
    console.error('Co-op flag absent. Run: node .agent/scripts/coop-mode.js set claude-code');
    process.exit(1);
  }
  if (!mode || mode.mode !== 'ide') {
    console.warn('[!] executor-mode.json says mode=' + (mode ? mode.mode : 'unset') + '. Continuing as IDE anyway.');
  }

  const phase = task.phase || 'SCOPE';
  if (phase !== 'SCOUT' && phase !== 'EXECUTE') {
    console.error(`Phase=${phase} not actionable by Gemini. Expected SCOUT or EXECUTE.`);
    process.exit(2);
  }

  const taskMdContent = fs.existsSync(TASK_MD) ? fs.readFileSync(TASK_MD, 'utf8') : '<task.md missing>';
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
    task_id: task.task_id,
    prompt_path: PROMPT_OUT,
    prompt_chars: fullPrompt.length,
    next_step: `Open Antigravity in workspace, paste content of ${path.basename(PROMPT_OUT)} to Gemini chat. After Gemini calls task-manager.js write, run: node .agent/scripts/await-handoff.js planner`
  }, null, 2));
}

generatePrompt();
