@echo off
cd /d "%~dp0"
title CIM PRO SERVER (Port 8888)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0select_room.ps1"
python server.py
pause
