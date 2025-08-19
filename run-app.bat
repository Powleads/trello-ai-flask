@echo off
echo ====================================
echo   Starting Trello AI Desktop
echo ====================================
echo.

:: Start Flask in a new window
echo Starting Flask server...
start "Flask Server" /min cmd /c "cd /d \"google meet to group and trello ai\" && python web_app.py"

:: Wait for Flask to start
echo Waiting for Flask server to initialize...
timeout /t 5 /nobreak > nul

:: Start Electron
echo Starting Electron application...
npm start

pause