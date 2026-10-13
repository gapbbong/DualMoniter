@echo off
chcp 65001 > nul
set "TASK_NAME=CIM_Agent"
set "SCRIPT_PATH=%~dp0FINAL_AGENT_START.bat"

echo ========================================
echo   CIM PRO 에이전트 서비스 등록 도구
echo ========================================

:: Register task in Task Scheduler to run at startup
schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /sc onstart /ru System /f
if %errorlevel% equ 0 (
    echo [OK] CIM Agent service registered successfully!
) else (
    echo [ERROR] Failed to register service. Please run as Administrator.
)
pause