@echo off
REM omni-coop.cmd - Limb-side wrapper for Co-op scripts
REM Calls Brain scripts but uses LIMB cwd via process.cwd().
REM
REM Usage:
REM   omni-coop set                     # activate co-op (planner=claude-code)
REM   omni-coop clear                   # deactivate
REM   omni-coop status                  # show flag + phase
REM   omni-coop scope <json>            # write task.json (Claude SCOPE)
REM   omni-coop gen-prompt              # generate gemini paste-prompt
REM   omni-coop await [timeout_ms]      # block until phase owner=planner
REM   omni-coop phase                   # show current phase + role
REM   omni-coop cost-report             # show token spend for current task
REM   omni-coop verify                  # verify limb is healthy

setlocal enabledelayedexpansion

set "BRAIN_ROOT=D:\Dev\Workspaces\Omni_Assistant"
set "SCRIPTS=%BRAIN_ROOT%\.agent\scripts"
set "ACTION=%~1"
shift

if "%ACTION%"=="set" (
  node "%SCRIPTS%\coop-mode.js" set claude-code
  goto :end
)
if "%ACTION%"=="clear" (
  node "%SCRIPTS%\coop-mode.js" clear
  goto :end
)
if "%ACTION%"=="status" (
  node "%SCRIPTS%\coop-mode.js" status
  echo.
  node "%SCRIPTS%\phase-transition.js" check
  goto :end
)
if "%ACTION%"=="scope" (
  set "OMNI_AGENT=claude-code"
  node "%SCRIPTS%\task-manager.js" write %1 %2 %3 %4 %5 %6 %7 %8 %9
  goto :end
)
if "%ACTION%"=="gen-prompt" (
  node "%SCRIPTS%\gen-gemini-prompt.js"
  goto :end
)
if "%ACTION%"=="await" (
  set "TIMEOUT=%~1"
  if "!TIMEOUT!"=="" set "TIMEOUT=600000"
  node "%SCRIPTS%\await-handoff.js" planner !TIMEOUT!
  goto :end
)
if "%ACTION%"=="phase" (
  node "%SCRIPTS%\phase-transition.js" check
  goto :end
)
if "%ACTION%"=="cost-report" (
  node "%SCRIPTS%\cost-meter.js" report %1
  goto :end
)
if "%ACTION%"=="verify" (
  node "%SCRIPTS%\verify-links.js"
  goto :end
)

echo Unknown action: %ACTION%
echo.
echo Usage:
echo   omni-coop set ^| clear ^| status
echo   omni-coop scope ^<json-payload^>
echo   omni-coop gen-prompt
echo   omni-coop await [timeout_ms]
echo   omni-coop phase
echo   omni-coop cost-report [task_id]
echo   omni-coop verify

:end
endlocal
