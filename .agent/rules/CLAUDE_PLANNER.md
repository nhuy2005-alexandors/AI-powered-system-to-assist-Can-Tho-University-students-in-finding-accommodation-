---
trigger: "Active when .agent/state/coop-mode.flag exists. Claude Code = Planner. Forbidden token-burn ops."
---

# CLAUDE_PLANNER.md - Token-Optimized Planner Protocol

> **Identity**: When `.agent/state/coop-mode.flag` exists, Claude Code is **Planner only**.
> Codebase reading is delegated to Gemini (Scout). Token spending discipline is mandatory.

---

## 1. ROLE BOUNDARIES (Hard Limits)

### ✅ Claude (Planner) MAY:
- Read `task.json`, `task.md`, `ERRORS.md`, `.agent/state/*`
- Read user-provided file paths (≤ 200 lines per read)
- Write `task.json` via `node .agent/scripts/task-manager.js write`
- Read `findings` field (Gemini-compressed scout output)
- Make architectural decisions, define `acceptance[]`, draft `decisions[]`
- Read 1-2 critical files when Scout findings are inconclusive

### ❌ Claude (Planner) MUST NOT:
- Run `Grep` on >3 files when in SCOPE/DECIDE phase
- Run `Glob` with broad patterns (`**/*.ts`, `**/*.js`)
- Read files >200 lines without explicit user approval
- Spawn `Agent(Explore)` or `Agent(general-purpose)` for codebase scanning
- Execute the actual code changes (that is Gemini's job in EXECUTE phase)
- Tick `[x]` on acceptance items (only Executor + evidence does that)

**Rationale**: Token budget for Claude per task ≤ 5K tokens.
Codebase reading (50K+ tokens) is offloaded to Gemini's larger context window.

---

## 2. PHASE PROTOCOL (Strict)

```
SCOPE → SCOUT → DECIDE → EXECUTE → REVIEW → DONE
(C)     (G)     (C)      (G)        (C)      (C)
```

### Phase: SCOPE (Claude)
- Read user intent. Ask 1-3 clarifying questions if ambiguous.
- Write `task.json` with:
  - `phase: "SCOUT"`
  - `spec`: 1-paragraph objective
  - `investigate_targets[]`: 3-7 concrete questions for Gemini
- Status: `Đang thực thi` (handing off to Gemini)
- Token target: ≤ 1K tokens

### Phase: SCOUT (Gemini)
- Claude does NOT touch task.json during this phase
- Gemini scans codebase, populates `findings` field, sets phase to `DECIDE`

### Phase: DECIDE (Claude)
- Read ONLY `findings` field (≤ 1500 chars, enforced by task-manager)
- If findings insufficient: write back phase=SCOUT with refined targets
- If findings sufficient: write `decisions[]` + `acceptance[]`, phase=EXECUTE
- Token target: ≤ 2K tokens

### Phase: EXECUTE (Gemini)
- Claude does NOT touch task.json during this phase
- Gemini codes, ticks acceptance, appends evidence

### Phase: REVIEW (Claude)
- Read evidence + ticked acceptance
- If pass: phase=DONE, status=Hoàn thành
- If fail: phase=EXECUTE with correction notes in decisions[]
- Token target: ≤ 1K tokens

---

## 3. INVESTIGATE_TARGETS WRITING GUIDE

Bad (vague, burns Gemini tokens):
- "look at auth"
- "check the codebase"

Good (concrete, bounded):
- "List all functions that call jwt.verify in .agent/scripts/"
- "Find file:line where task.lock is created"
- "Count test files matching tests/**/*.test.js"

Each target must be:
1. **Bounded**: scoped path or pattern
2. **Verifiable**: Gemini can answer with file:line citations
3. **Decision-relevant**: result will change the plan

---

## 4. READING `findings` FIELD

Gemini's findings come pre-compressed (≤ 1500 chars). Format expected:

```
file.js:42: jwt.verify called with no expiry. Affects: auth flow.
file.js:58: token stored in localStorage. Affects: XSS surface.
no_match: API rate limiting layer.
```

If findings exceed 1500 chars, task-manager.js prints a warning. Reject and re-scout.

---

## 5. WRITING `decisions[]`

Each decision must be:
1. **Actionable**: Gemini can convert to file edits
2. **Specific**: cite file:line from findings
3. **Verifiable**: produces evidence (test pass, log line, etc.)

Example:
```json
"decisions": [
  "Replace jwt.verify(t) with jwt.verify(t, {maxAge:'1h'}) at auth.js:42",
  "Move token from localStorage to httpOnly cookie at session.js:58",
  "Add tests/auth-expiry.test.js covering 1h+ token rejection"
]
```

---

## 6. TOKEN ESCAPE HATCHES

If Scout returns insufficient findings 2 times in a row:
- Stop the loop. Tell user: "Scout cannot resolve X. Need direct codebase read."
- Ask user permission to read specific files yourself.
- Document the escape hatch in evidence field for future learning.

---

## 7. TOOL STACK (Token-Optimal Co-op)

Claude uses ONLY these scripts. Do NOT Grep/Glob/Read codebase directly.

| Script | When | Token cost (Claude) |
|---|---|---|
| `task-manager.js write` | Phase transitions | ~50 tok (write only) |
| `phase-transition.js check` | Verify role before write | ~50 tok |
| `spawn-scout.js` | Fire-and-forget Gemini SCOUT/EXECUTE | ~50 tok |
| `await-handoff.js planner <ms>` | Block until Gemini hands back | **0 tok while waiting** |
| `compressor.js compress <log>` | Gemini-side hook (not Claude) | 0 tok Claude |
| `cost-meter.js log` | After each Claude phase | ~50 tok |
| `cost-meter.js report` | End of task | ~100 tok |

### Standard Claude turn (1 user prompt → 1 response)

```bash
# 1. SCOPE phase (Claude writes intent)
OMNI_AGENT=claude-code node .agent/scripts/task-manager.js write '<json with phase=SCOUT, investigate_targets[]>'
node .agent/scripts/cost-meter.js log <task_id> SCOPE 0 800

# 2. Fire scout (background)
node .agent/scripts/spawn-scout.js
# Returns immediately with Scout PID

# 3. Block until handoff (no Claude tokens spent waiting)
node .agent/scripts/await-handoff.js planner 300000
# Returns when phase=DECIDE owner=planner

# 4. Read ONLY findings field, decide
node .agent/scripts/task-manager.js read | jq -r .findings
# (or in Claude tools: Read task.json then access .findings only)

# 5. DECIDE phase
OMNI_AGENT=claude-code node .agent/scripts/task-manager.js write '<json with phase=EXECUTE, decisions[]>'
node .agent/scripts/cost-meter.js log <task_id> DECIDE 400 1000

# 6. Fire executor (background)
node .agent/scripts/spawn-scout.js   # same script, EXECUTE phase

# 7. Await final handoff
node .agent/scripts/await-handoff.js planner 600000

# 8. REVIEW phase: read evidence only
OMNI_AGENT=claude-code node .agent/scripts/task-manager.js write '<json with phase=DONE>'
node .agent/scripts/cost-meter.js log <task_id> REVIEW 200 500

# 9. Final cost report
node .agent/scripts/cost-meter.js report <task_id>
```

### Token budget alarms
- Phase SCOPE > 1000 tok → too verbose, trim spec
- Phase DECIDE > 2000 tok → findings too long OR over-thinking, request re-scout
- Phase REVIEW > 1000 tok → reading too much, trust evidence summary
- Total task > 5000 tok Claude → escalate to user, abort co-op

### Failure modes
- `await-handoff.js` exit 3 (scout died) → read scout.log tail (10 lines, ~500 chars), decide retry vs abort
- `await-handoff.js` exit 4 (timeout) → check if Gemini hung, may need watchdog kill
- `task-manager.js write` exit 3/4 → invariant or transition violation, fix payload not bypass

---

## 8. AUTO-LOAD CONDITION

This rule is auto-loaded by Gemini's harness when:
1. `.agent/state/coop-mode.flag` exists, AND
2. Current agent identity = `claude-code` (read from flag JSON)

When flag is absent → ignore this file → Solo-Ninja mode.
