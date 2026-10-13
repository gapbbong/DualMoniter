@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Checking Python Libraries...
python -m pip install requests mss pillow websocket-client websockets --quiet

echo ========================================
echo   CIM PRO SYSTEM STARTING...
echo ========================================
python FINAL_AGENT_PRO.py
pause