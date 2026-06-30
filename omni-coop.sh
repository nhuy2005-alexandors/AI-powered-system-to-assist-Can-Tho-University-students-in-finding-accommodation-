#!/usr/bin/env bash
# omni-coop.sh - Limb-side wrapper for Co-op scripts (bash/POSIX).
# Calls Brain scripts but uses LIMB cwd via process.cwd().

set -e

BRAIN_ROOT="D:/Dev/Workspaces/Omni_Assistant"
SCRIPTS="$BRAIN_ROOT/.agent/scripts"
ACTION="${1:-help}"
shift || true

case "$ACTION" in
  set)         node "$SCRIPTS/coop-mode.js" set claude-code ;;
  clear)      node "$SCRIPTS/coop-mode.js" clear ;;
  status)     node "$SCRIPTS/coop-mode.js" status; node "$SCRIPTS/phase-transition.js" check ;;
  scope)      OMNI_AGENT=claude-code node "$SCRIPTS/task-manager.js" write "$@" ;;
  gen-prompt) node "$SCRIPTS/gen-gemini-prompt.js" ;;
  await)      node "$SCRIPTS/await-handoff.js" planner "${1:-600000}" ;;
  phase)      node "$SCRIPTS/phase-transition.js" check ;;
  cost-report) node "$SCRIPTS/cost-meter.js" report "$@" ;;
  verify)     node "$SCRIPTS/verify-links.js" ;;
  *)
    echo "Usage: omni-coop {set|clear|status|scope|gen-prompt|await|phase|cost-report|verify}"
    exit 1 ;;
esac
