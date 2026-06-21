@echo off
setlocal enabledelayedexpansion

echo === TimeTracker Windows Agent Setup ===

:: 1. Get server URL
set /p SERVER_URL="Server URL (e.g. http://yourserver.com:8000): "
if "!SERVER_URL!"=="" set SERVER_URL=http://localhost:8000

:: 2. Get credentials
set /p EMAIL="Your email: "
set /p PASSWORD="Your password: "

:: 3. Login
echo Authenticating...
set RESPONSE_FILE=%TEMP%\tt_login.json
curl -s -X POST "!SERVER_URL!/auth/login" ^
  -H "Content-Type: application/json" ^
  -d "{\"email\": \"!EMAIL!\", \"password\": \"!PASSWORD!\"}" ^
  -o "!RESPONSE_FILE!"

for /f "delims=" %%i in ('python -c "import json,sys; d=json.load(open(r'!RESPONSE_FILE!')); print(d['member']['id'])"') do set MEMBER_ID=%%i
for /f "delims=" %%i in ('python -c "import json,sys; d=json.load(open(r'!RESPONSE_FILE!')); print(d['member']['name'])"') do set MEMBER_NAME=%%i

if "!MEMBER_ID!"=="" (
  echo Login failed. Check credentials and server URL.
  pause & exit /b 1
)
echo Logged in as: !MEMBER_NAME! (ID: !MEMBER_ID!)

:: 4. Setup directories
set AGENT_DIR=%APPDATA%\TimeTracker
mkdir "!AGENT_DIR!" 2>nul
mkdir "!AGENT_DIR!\agent" 2>nul

:: 5. Install dependencies
echo Installing Python packages...
pip install requests pygetwindow pywin32 psutil keyboard uiautomation --quiet

:: 6. Copy agent files
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
xcopy /E /I /Q "!PROJECT_ROOT!\agent" "!AGENT_DIR!\agent" >nul

:: 7. Save config
python -c "
import sys
sys.path.insert(0, r'!AGENT_DIR!')
from agent.common.local_db import init_db, set_config
init_db()
set_config('member_id', '!MEMBER_ID!')
set_config('server_url', '!SERVER_URL!')
print('Config saved.')
"

:: 8. Create Task Scheduler entry
schtasks /create /tn "TimeTrackerAgent" ^
  /tr "python \"!AGENT_DIR!\agent\windows\agent.py\"" ^
  /sc ONLOGON /ru "%USERNAME%" /f ^
  /rl HIGHEST >nul 2>&1

:: Set environment variables for the task
schtasks /change /tn "TimeTrackerAgent" ^
  /tr "cmd /c set TRACKER_SERVER_URL=!SERVER_URL! && set TRACKER_MEMBER_ID=!MEMBER_ID! && set PYTHONPATH=!AGENT_DIR! && python \"!AGENT_DIR!\agent\windows\agent.py\"" >nul 2>&1

:: 9. Start now
echo Starting agent...
start /B pythonw "!AGENT_DIR!\agent\windows\agent.py"

echo.
echo [SUCCESS] TimeTracker agent installed!
echo    Logs: !AGENT_DIR!\agent.log
echo    Pause tracking: Ctrl+Shift+P (30 min)
echo    Dashboard: !SERVER_URL!
echo.
pause
