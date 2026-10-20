@echo off
chcp 65001 > nul
title CIM Agent Cleaner

taskkill /f /im "02_학생용_모니터링_에이전트_전송용v3.exe" > nul 2>&1
taskkill /f /im "02_학생용*.exe" > nul 2>&1
taskkill /f /im "CIM_AGENT_PRO.exe" > nul 2>&1
taskkill /f /im "CIM_AGENT*.exe" > nul 2>&1

powershell -NoProfile -Command ^
  "Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*CIM*' -or $_.Path -like '*학생용*' -or $_.Name -like '*CIM*' } | Stop-Process -Force" > nul 2>&1

echo [OK] All CIM Agent processes terminated.
