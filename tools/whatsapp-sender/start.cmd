@echo off
setlocal EnableExtensions
title Project Finder - WhatsApp sender
cd /d "%~dp0"

set "MODE=--send"
if /i "%~1"=="check" set "MODE=--check"

echo.
echo  ============================================================
echo   Project Finder  -  WhatsApp sender
echo  ============================================================
echo.

rem --- 1. Node.js ------------------------------------------------------
where node >nul 2>nul
if errorlevel 1 goto :no_node

rem --- 2. the key file -------------------------------------------------
if not exist "config.json" goto :no_config

rem --- 3. the WhatsApp library -----------------------------------------
if not exist "node_modules\whatsapp-web.js" (
  echo  First run: installing the WhatsApp library. This takes a minute.
  call npm install
  if errorlevel 1 goto :npm_failed
)

rem --- 4. the VPN ------------------------------------------------------
rem  The live site answers 451 to an Iranian address, so the sender has to
rem  leave through the VPN. Doing it here means it works even when the VPN
rem  client does not set the proxy variables for the whole machine.
set "VPORT="
for /f "usebackq delims=" %%p in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; foreach($x in 10808,10809,1080,7890,8086){ $t=New-Object Net.Sockets.TcpClient; if($t.ConnectAsync('127.0.0.1',$x).Wait(400)){ $t.Close(); $x; break }; $t.Close() }"`) do set "VPORT=%%p"
if defined VPORT (
  set "HTTP_PROXY=http://127.0.0.1:%VPORT%"
  set "HTTPS_PROXY=http://127.0.0.1:%VPORT%"
  set "NO_PROXY=localhost,127.0.0.1,::1"
  echo  VPN proxy found on 127.0.0.1:%VPORT% - using it.
) else (
  echo  No VPN proxy is running. If the check below says 451, start V2Ray
  echo  and run this again.
)
echo.

rem --- 5. does the server answer? --------------------------------------
echo  Checking the server (this never claims or sends anything)...
echo.
call node sender.js --check
if errorlevel 1 goto :check_failed

if /i "%MODE%"=="--check" goto :end

rem --- 6. the panel, then sending --------------------------------------
start "" "https://nimabuilds.pythonanywhere.com/admin"

echo.
echo  Sending. Keep this window open - closing it stops the queue.
echo  Nothing goes out while Autopilot is off in the panel.
echo.
node sender.js --send
goto :end

:no_node
echo  Node.js is not installed, or not on PATH.
echo  Install the LTS version from https://nodejs.org and run this again.
goto :end

:no_config
echo  config.json is missing from this folder.
echo.
echo  In the admin panel open  Project Finder - Autopilot - Sender setup,
echo  press "Download config.json", and drop the file in this folder.
goto :end

:npm_failed
echo.
echo  npm install failed. Check your internet connection, then run again.
goto :end

:check_failed
echo.
echo  The server check failed - the message above says why.
echo    451  = the VPN is not running. Start it and run this again.
echo    401  = the agent key changed. Download config.json again.
echo    peek = the live site is running an older build. Deploy, then retry.
goto :end

:end
echo.
echo  Sender stopped. You can close this window.
echo.
pause
