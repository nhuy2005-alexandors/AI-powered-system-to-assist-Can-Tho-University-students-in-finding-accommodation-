@echo off
setlocal enabledelayedexpansion
cd /d "D:\Dev\Workspaces\NCKH"
title Omni Co-op Launcher - NCKH

echo ==========================================
echo   OMNI CO-OP LAUNCHER
echo ==========================================
echo.
echo Workspace: %CD%
echo.

REM --- activate co-op if not active ---
node .agent/scripts/coop-mode.js status | findstr /C:"\"active\":true" >nul 2>&1
if errorlevel 1 (
  echo [+] Activating co-op mode...
  node .agent/scripts/coop-mode.js set claude-code
) else (
  echo [ok] Co-op already active.
)

echo.
echo NEXT: Open Antigravity workspace, create 2 chat panels:
echo   - Panel-Claude  (model = Claude)
echo   - Panel-Gemini  (model = Gemini 3.1 Pro)
echo.
pause

:LOOP
cls
echo ==========================================
echo   OMNI CO-OP -- PHASE LOOP
echo ==========================================
echo.
node .agent/scripts/omni-next.js
set NEXT_EXIT=%ERRORLEVEL%
echo.
echo ------------------------------------------
echo   [Ctrl+V] into the panel shown above.
echo   Wait for panel to finish (it will run task-manager.js write).
echo ------------------------------------------
echo.
choice /C NRQ /N /M "  [N]ext phase   [R]eset (new task)   [Q]uit: "
if errorlevel 3 goto END
if errorlevel 2 goto RESET
goto LOOP

:RESET
echo.
echo [!] Deleting task.json + task.md for new task...
if exist task.json del task.json
if exist task.md del task.md
echo Ready. Next N will gen SCOPE prompt for Panel-Claude.
pause
goto LOOP

:END
echo.
choice /C YN /N /M "Clear co-op mode on exit? [Y/N]: "
if errorlevel 2 goto SKIP_CLEAR
node .agent/scripts/coop-mode.js clear
:SKIP_CLEAR
echo.
echo Bye.
timeout /t 2 >nul
endlocal
