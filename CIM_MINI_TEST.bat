@echo off
chcp 65001 > nul
echo =========================================
echo   CIM PRO FORCED PAUSE TEST (v2.5)
echo =========================================
echo.

echo [1] STARTING TEST... PRESS ANY KEY.
pause

echo.
echo [2] RUNNING DIAGNOSTICS...
python -c "import FINAL_AGENT_PRO; FINAL_AGENT_PRO.run_full_diagnostics()"
pause