@echo off
if not "%1"=="min" (
    start "" /min cmd /c ""%~f0" min"
    exit /b
)
chcp 65001 > nul
setlocal
cd /d "%~dp0"
title CIM PRO SERVER (Port 8888)

python 시스템_관리_서버.py
pause
