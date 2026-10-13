@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
echo ===================================================
echo   CIM PRO AGENT - INSTALLATION TOOL (v2.9)
echo ===================================================

set "TARGET_DIR=C:\Program Files\CIM_Agent"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo [1/3] Copying files to %TARGET_DIR%...
copy /y "%~dp002_학생용_모니터링_에이전트_전송용v2.exe" "%TARGET_DIR%\CIM_AGENT_PRO.exe" > nul 2>&1
if exist "%~dp0server_ip.txt" copy /y "%~dp0server_ip.txt" "%TARGET_DIR%" > nul 2>&1

echo [2/3] Registering Task Scheduler service...
set "TASK_NAME=CIM_Agent"
set "SCRIPT_PATH=%TARGET_DIR%\CIM_AGENT_PRO.exe"
schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /sc onstart /ru System /f > nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] CIM Agent service registered successfully!
) else (
    echo [WARNING] Failed to register Task Scheduler service. (Requires admin rights)
)

echo [3/3] Installation completed.
pause