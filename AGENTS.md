# NCKH

## Stack
- Ecosystems: node, python
- Build: not configured or not verified.
- Test: not configured or not verified.
- Lint: not configured or not verified.
<!-- init-framework:v2:start -->
## Agent contract

Managed by init-framework v2, profile `strict`. Edit outside this block;
anything inside is regenerated on re-init.

The profile is the **baseline**: which documents must exist, and the default tier for
an ordinary change here (`strict`). It is not a floor and not a cap — pick the
tier below that matches what the change in front of you can actually break.

### Declaring the change

Before starting, name the current change in `docs/CHECKPOINT.md` under
`## Current objective`. The audit reads these fields and checks nothing else:

```text
- Tier: micro | standard | strict
- Spec: docs/specs/<feature>.md      (standard and strict)
- Gate: .codex-gate.json             (strict)
```

No `Tier:` line means no audit can run, and the check says so instead of passing.

### Orchestration

Keep requirements, architecture, security, and final diff accountability in the
primary agent. Use independent execution or review when available for broad or
correctness-sensitive work. Verify reports against real artifacts and command output.

### Documentation

- `docs/CHECKPOINT.md` — state: objective, verified done, unverified, next, blockers.
- `docs/DECISIONS.md` — ADRs, cumulative, never deleted.
- `docs/GOTCHAS.md` — pitfalls actually hit, with detection and status.
- `docs/specs/<feature>.md` — written before a standard or strict feature.
- `docs/technical_specs/<feature>.md` — as-built, written after the feature verifies.

### Workflow by risk, not by habit

**Micro change** (1-2 files, no state/security/schema change)
- No separate spec. Write a 4-6 line micro-spec in the checkpoint instead.
- Run the check that fits the change.
- Update the checkpoint only if work is left unfinished.

**Standard feature** (multi-file, or a change to an existing flow)
- Write `docs/specs/<feature>.md` first, with observable acceptance criteria.
- Test-first where the behavior is automatically checkable.
- Get an independent review when the diff is substantial.

**Strict change** (auth, money, PII, data migration, destructive or infra operation)
- Full spec including constraints, verification plan, and rollback/migration.
- Have the spec critiqued before the first line of code.
- Red, green, refactor.
- An objective gate must pass: a command, not a claim.
- A reviewer who did not write the change signs off before completion.

### Verification

- Test-first when the behavior is automatically checkable.
- UI change: browser/screenshot/interaction check.
- Config or docs: schema, build, or link validation.
- No test framework present: state the alternative verification explicitly. Do not
  stand up a test framework that this change does not need.
- Seeing the code is not Done. Done needs the command that was run and its result.
<!-- init-framework:v2:end -->
