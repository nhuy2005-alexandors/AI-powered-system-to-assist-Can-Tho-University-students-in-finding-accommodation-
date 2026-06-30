---
trigger: "Active when .agent/state/executor-mode.json has mode='ide'"
---

# IDE_MODE.md - Co-op via Antigravity (Dual-Panel)

> **Architecture**: Both agents live in ONE Antigravity workspace as two separate chat panels. Panel-Claude (via API extension) = Planner. Panel-Gemini (3.1 Pro, free Google Pro) = Executor. Hand-off via `task.json` mutations only. Operator pastes the per-phase prompt into whichever panel owns the current phase.

> **Cost note**: Claude in Antigravity bills to the Anthropic API (NOT free). It stays cheap (~3K tok/task) because it only does SCOPE/DECIDE/REVIEW. Gemini is free on Google Pro quota and absorbs the token-heavy SCOUT (codebase reads) + EXECUTE (code writing).

---

## When to use IDE mode

- Have Google AI Pro subscription with Gemini 3.1 Pro access in Antigravity
- Don't want to pay API token billing for CLI
- Sitting at desk with both IDEs open
- Tasks where 3.1 Pro reasoning matters (refactor, design, deep analysis)

## When NOT to use IDE mode

- Headless / scheduled / `/loop` tasks → use CLI mode (Flash 2.5 free)
- Trivial SCOUT tasks → CLI Flash 2.5 is enough and free
- Sếp not at desk → no one to paste prompt

---

## Operator Cheat Sheet (dual-panel, 4 pastes per task)

### Setup once per session
```bash
# Activate co-op + dual-panel IDE mode
node .agent/scripts/coop-mode.js set claude-code
# executor-mode.json already says mode=ide, topology=dual-panel
```
Open Antigravity in `Omni_Assistant` workspace. Open TWO agent chat panels:
- **Panel-Claude** → model = Claude (API extension). This is your Planner.
- **Panel-Gemini** → model = Gemini 3.1 Pro. This is your Executor.

### Per task — the 5-step / 4-paste loop

Phase owners: `SCOPE(C) → SCOUT(G) → DECIDE(C) → EXECUTE(G) → REVIEW(C) → DONE(C)`

**① SCOPE → paste to Panel-Claude**
```bash
node .agent/scripts/gen-claude-prompt.js   # writes claude-paste-prompt.md (SCOPE)
```
Paste `claude-paste-prompt.md` + your goal into Panel-Claude. Claude writes `task.json` (phase=SCOUT) via its terminal.

**② SCOUT → paste to Panel-Gemini**
```bash
node .agent/scripts/gen-gemini-prompt.js   # writes gemini-paste-prompt.md (SCOUT)
```
Paste `gemini-paste-prompt.md` into Panel-Gemini. Gemini scans codebase, writes `findings` (phase=DECIDE) via terminal. FREE.

**③ DECIDE → paste to Panel-Claude**
```bash
node .agent/scripts/gen-claude-prompt.js   # now emits DECIDE prompt
```
Paste into Panel-Claude. Claude reads ONLY findings, writes `decisions[]` (phase=EXECUTE).

**④ EXECUTE → paste to Panel-Gemini**
```bash
node .agent/scripts/gen-gemini-prompt.js   # now emits EXECUTE prompt
```
Paste into Panel-Gemini. Gemini implements decisions, writes `evidence` + ticks acceptance (phase=REVIEW). FREE.

**⑤ REVIEW → paste to Panel-Claude**
```bash
node .agent/scripts/gen-claude-prompt.js   # now emits REVIEW prompt
```
Paste into Panel-Claude. Claude verifies evidence, sets phase=DONE (or sends back to EXECUTE/SCOUT). Reports cost via `cost-meter.js`.

> Each `gen-*-prompt.js` reads the current `task.json` phase and emits the right instruction automatically. If you paste into the wrong panel, the phase guard in `task-manager.js` rejects the illegal write (exit 3) — no corruption.

> **No `await-handoff.js` needed** in dual-panel: the operator is the interrupt. `await-handoff.js` stays for headless CLI mode only.

---

## Token economy (IDE mode)

Per task with 1 SCOUT + 1 EXECUTE round:

| Phase | Claude tok (API) | Gemini tok | Operator action |
|---|---|---|
| SCOPE | ~800 | 0 | paste 1 → Panel-Claude |
| (gen gemini prompt) | 0 | 0 | none |
| SCOUT | 0 | ~30K (Pro 3.1) | paste 2 → Panel-Gemini |
| DECIDE | ~1500 | 0 | paste 3 → Panel-Claude |
| (gen gemini prompt) | 0 | 0 | none |
| EXECUTE | 0 | ~10K (Pro 3.1) | paste 4 → Panel-Gemini |
| REVIEW | ~700 | 0 | paste 5 → Panel-Claude |
| **Total Claude** | **~3K (billed)** | — | 4 pastes |

Compare (per task):
- Claude solo (no co-op): ~70K Claude API tok billed
- Dual-panel co-op: ~3K Claude API tok billed + ~40K Gemini tok @ $0 (Google Pro quota)

**~95% cut in Claude API spend.** Claude only reasons over compressed findings/evidence; Gemini eats the codebase for free.

---

## Failure modes + recovery

| Symptom | Cause | Fix |
|---|---|---|
| Pasted prompt, panel says "phase not owned" / exit 2 | Wrong gen script for current phase, or pasted into wrong panel | Run the matching gen script (claude for SCOPE/DECIDE/REVIEW, gemini for SCOUT/EXECUTE); paste into the owning panel |
| `task-manager.js` exit 3 illegal transition | Agent tried to skip a phase (e.g. SCOUT→DONE) | Re-paste correct phase prompt; phase guard protected task.json — no corruption |
| `task-manager.js` exit 4 invariant | findings > 1500 chars, missing decisions[], or DONE without evidence | Re-paste with "respect Compression Mandate / fill required fields" addendum |
| Gemini edits files in SCOUT phase | Pasted EXECUTE prompt during SCOUT, or Gemini ignored "FORBIDDEN: Editing source code" | `git restore`; re-do SCOUT |
| Antigravity terminal can't find node | PATH misconfig | `cd` then `node` with absolute path |

---

## Switching modes mid-session

```bash
# Switch to CLI (Flash 2.5 free, headless)
node -e "const fs=require('fs'),p='.agent/state/executor-mode.json';const m=JSON.parse(fs.readFileSync(p));m.mode='cli';fs.writeFileSync(p,JSON.stringify(m,null,2))"

# Switch back to IDE (Pro 3.1)
node -e "const fs=require('fs'),p='.agent/state/executor-mode.json';const m=JSON.parse(fs.readFileSync(p));m.mode='ide';fs.writeFileSync(p,JSON.stringify(m,null,2))"
```

`await-handoff.js` reads mode dynamically — no restart needed.

---

## Why this design

1. **Stigmergy preserved**: Claude and Gemini still communicate ONLY via `task.json` mutations. No direct chat. No socket. Operator paste = manual interrupt to wake Gemini.
2. **Phase guards still active**: `task-manager.js` rejects illegal transitions even when Gemini is the writer.
3. **Compression Mandate enforced**: Both Compressor (CLI mode) and prompt instructions (IDE mode) cap findings at 1500 chars.
4. **Claude stays cheap**: Same token economy as CLI mode (~3K/task) regardless of executor.
5. **Pro 3.1 unlocks**: Use the bigger reasoning where it matters (codebase scan, refactor) without paying API tokens.
