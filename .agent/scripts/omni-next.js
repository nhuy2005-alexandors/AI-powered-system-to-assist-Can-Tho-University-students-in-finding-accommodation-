const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const WORKSPACE_DIR = process.cwd();
const TASK_JSON = path.join(WORKSPACE_DIR, 'task.json');
const STATE_DIR = path.join(WORKSPACE_DIR, '.agent', 'state');
const COOP_FLAG = path.join(STATE_DIR, 'coop-mode.flag');
const CLAUDE_PROMPT = path.join(STATE_DIR, 'claude-paste-prompt.md');
const GEMINI_PROMPT = path.join(STATE_DIR, 'gemini-paste-prompt.md');

const PHASE_OWNER = {
  SCOPE: 'planner', SCOUT: 'executor', DECIDE: 'planner',
  EXECUTE: 'executor', REVIEW: 'planner', DONE: 'planner'
};

function readJson(p) {
  if (!fs.existsSync(p)) return null;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

function copyToClipboard(text) {
  try {
    if (process.platform === 'win32') {
      execSync('clip', { input: text });
    } else if (process.platform === 'darwin') {
      execSync('pbcopy', { input: text });
    } else {
      execSync('xclip -selection clipboard', { input: text });
    }
    return true;
  } catch {
    return false;
  }
}

if (!fs.existsSync(COOP_FLAG)) {
  console.error('Co-op flag absent. Run: node .agent/scripts/coop-mode.js set claude-code');
  process.exit(1);
}

const task = readJson(TASK_JSON);
const phase = task ? (task.phase || 'SCOPE') : 'SCOPE';

if (phase === 'DONE') {
  console.log('Task DONE. Nothing to paste. Start a new task: paste SCOPE into Panel-Claude (run with fresh/empty task.json).');
  process.exit(0);
}

const owner = PHASE_OWNER[phase];
const isPlanner = owner === 'planner';
const genScript = isPlanner ? 'gen-claude-prompt.js' : 'gen-gemini-prompt.js';
const promptFile = isPlanner ? CLAUDE_PROMPT : GEMINI_PROMPT;
const panel = isPlanner ? 'Panel-Claude (model Claude)' : 'Panel-Gemini (Gemini 3.1 Pro)';

try {
  execSync(`node .agent/scripts/${genScript}`, { cwd: WORKSPACE_DIR, stdio: 'pipe' });
} catch (e) {
  console.error(`gen failed: ${e.stderr ? e.stderr.toString() : e.message}`);
  process.exit(2);
}

const promptText = fs.existsSync(promptFile) ? fs.readFileSync(promptFile, 'utf8') : null;
if (!promptText) {
  console.error(`Prompt file not generated: ${promptFile}`);
  process.exit(3);
}

const copied = copyToClipboard(promptText);

console.log('========================================');
console.log(`  PHASE: ${phase}  (owner: ${owner})`);
console.log(`  PASTE INTO: ${panel}`);
console.log(`  Clipboard: ${copied ? 'COPIED — just Ctrl+V' : 'FAILED — open ' + path.basename(promptFile) + ' and copy manually'}`);
console.log(`  Prompt chars: ${promptText.length}`);
console.log('========================================');
console.log(`After that panel writes task.json, run this command again for the next phase.`);
