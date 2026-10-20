@echo off
if not "%1"=="min" (
    start "" /min cmd /c ""%~f0" min"
    exit /b
)
chcp 65001 > nul
setlocal
cd /d "%~dp0"
title CIM PRO SERVER (Port 8888)

echo [1/3] Checking libraries...
python -m pip install "uvicorn[standard]" fastapi pyautogui requests websocket-client pillow python-multipart mss websockets openpyxl --quiet

echo [2/3] Checking firewall (Port 8888)...
powershell -Command "if (!(Get-NetFirewallRule -DisplayName 'CIM_PRO_SERVER' -ErrorAction SilentlyContinue)) { New-NetFirewallRule -DisplayName 'CIM_PRO_SERVER' -Direction Inbound -LocalPort 8888 -Protocol TCP -Action Allow }" >nul 2>&1
powershell -Command "if (!(Get-NetFirewallRule -DisplayName 'CIM_PRO_DISCOVERY' -ErrorAction SilentlyContinue)) { New-NetFirewallRule -DisplayName 'CIM_PRO_DISCOVERY' -Direction Inbound -LocalPort 8889 -Protocol UDP -Action Allow }" >nul 2>&1

:: Get active local IP address dynamically using PowerShell (pipeless for CMD safety)
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "$r = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue; if ($r) { $int = Get-NetIPInterface -InterfaceIndex $r[0].InterfaceIndex -ErrorAction SilentlyContinue; if ($int) { $ips = Get-NetIPAddress -InterfaceIndex $int[0].InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue; if ($ips) { $ips[0].IPAddress; exit } } }; $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue; foreach ($ip in $ips) { if (-not $ip.IPAddress.StartsWith('127.') -and -not $ip.IPAddress.StartsWith('169.254.')) { $ip.IPAddress; exit } }"') do set "SERVER_IP=%%i"

if "%SERVER_IP%"=="" set "SERVER_IP=localhost"

echo [3/3] CIM PRO SERVER READY!
echo ========================================
echo   URL: http://%SERVER_IP%:8888
echo   (Use this IP to connect from other PCs)
echo ========================================
echo.

:: 서버가 포트 8888에서 실제로 응답을 시작한 뒤에 브라우저를 여는 백그라운드 대기 작업
start "" powershell -NoProfile -WindowStyle Hidden -Command "for ($i=0; $i -lt 30; $i++) { try { (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1', 8888); Start-Process 'http://localhost:8888'; break } catch { Start-Sleep -Seconds 1 } }"

python 시스템_관리_서버.py
pause