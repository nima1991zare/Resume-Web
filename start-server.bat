@echo off
title Nima Website Server
cd /d "%~dp0"

rem already running? just open the browser
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8123/api/content | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    echo Server is already running.
    start "" "http://127.0.0.1:8123/"
    exit /b 0
)

echo Starting Nima website server on http://127.0.0.1:8123 ...
echo (Keep this window open. Close it to stop the website.)
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start "" http://127.0.0.1:8123/"
python -m uvicorn app.main:app --port 8123
pause
