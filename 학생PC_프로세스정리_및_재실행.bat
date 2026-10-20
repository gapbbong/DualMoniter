@echo off
chcp 65001 > nul
title CIM Agent Cleaner & Restart

echo ============================================================
echo   학생 PC 모니터링 에이전트 프로세스 정리 및 재실행 도구
echo ============================================================
echo.

echo [1/3] 중복 실행된 기존 에이전트 프로세스 강제 종료 중...
taskkill /f /im "02_학생용_모니터링_에이전트_전송용v3.exe" > nul 2>&1
taskkill /f /im "02_학생용*.exe" > nul 2>&1
taskkill /f /im "CIM_AGENT_PRO.exe" > nul 2>&1
taskkill /f /im "CIM_AGENT*.exe" > nul 2>&1

:: 파워쉘로 숨은 프로세스까지 완전 정리
powershell -NoProfile -Command ^
  "Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*CIM*' -or $_.Path -like '*학생용*' -or $_.Name -like '*CIM*' } | Stop-Process -Force" > nul 2>&1

timeout /t 2 /nobreak > nul

echo [2/3] 최신 에이전트 1개만 깔끔하게 재실행...
set "EXE_LAUNCHED=0"

if exist "%~dp002_학생용_모니터링_에이전트_전송용v3.exe" (
    start "" "%~dp002_학생용_모니터링_에이전트_전송용v3.exe"
    set "EXE_LAUNCHED=1"
) else if exist "C:\CIM_Agent\CIM_AGENT_PRO.exe" (
    start "" "C:\CIM_Agent\CIM_AGENT_PRO.exe"
    set "EXE_LAUNCHED=1"
)

if "!EXE_LAUNCHED!"=="0" (
    for %%f in ("%~dp0*.exe") do (
        start "" "%%~ff"
        goto :done
    )
)

:done
echo.
echo ============================================================
echo   [완료] 기존 프로세스 정리 후 단일 에이전트가 실행되었습니다!
echo ============================================================
timeout /t 2 > nul
