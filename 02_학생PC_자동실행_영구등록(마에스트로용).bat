@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title CIM PRO - 학생용 에이전트 자동실행 설치

echo ============================================================
echo   CIM PRO 학생용 모니터링 에이전트 자동실행 등록 도구
echo ============================================================
echo.

set "TARGET_DIR=C:\CIM_Agent"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo [1/3] 에이전트 파일 복사 중...
copy /y "%~dp002_학생용_모니터링_에이전트_전송용v3.exe" "%TARGET_DIR%\CIM_AGENT_PRO.exe" > nul 2>&1
if exist "%~dp0server_ip.txt" copy /y "%~dp0server_ip.txt" "%TARGET_DIR%\" > nul 2>&1

echo [2/3] 윈도우 시작프로그램(자동 실행) 등록 중...
:: 모든 사용자 시작프로그램 폴더에 바로가기 등록 (관리자 권한 호환)
powershell -NoProfile -Command ^
  "$s = (New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('CommonStartup') + '\CIM_Agent.lnk');" ^
  "$s.TargetPath = '%TARGET_DIR%\CIM_AGENT_PRO.exe';" ^
  "$s.WorkingDirectory = '%TARGET_DIR%';" ^
  "$s.WindowStyle = 7;" ^
  "$s.Save();" > nul 2>&1

:: 현재 사용자 시작프로그램 폴더에도 등록 (이중 보장)
powershell -NoProfile -Command ^
  "$s = (New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup') + '\CIM_Agent.lnk');" ^
  "$s.TargetPath = '%TARGET_DIR%\CIM_AGENT_PRO.exe';" ^
  "$s.WorkingDirectory = '%TARGET_DIR%';" ^
  "$s.WindowStyle = 7;" ^
  "$s.Save();" > nul 2>&1

echo [3/3] 에이전트 백그라운드 실행...
taskkill /f /im CIM_AGENT_PRO.exe > nul 2>&1
taskkill /f /im "02_학생용_모니터링_에이전트_전송용v3.exe" > nul 2>&1
start "" "%TARGET_DIR%\CIM_AGENT_PRO.exe"

echo.
echo ============================================================
echo   [완료] 학생 PC 에이전트가 자동 실행되도록 설정되었습니다!
echo   이제 마에스트로에서 '보호 실행(순간복구 잠금)'을 진행하세요.
echo ============================================================
timeout /t 3 > nul
