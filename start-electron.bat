@echo off
echo ====================================
echo   Trello AI Desktop Application
echo ====================================
echo.

:: Check if Node.js is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

:: Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed!
    echo Please install Python from https://python.org/
    pause
    exit /b 1
)

echo Checking dependencies...

:: Install Node dependencies if needed
if not exist "node_modules" (
    echo Installing Electron dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install Node dependencies!
        pause
        exit /b 1
    )
)

:: Check Python dependencies
cd "google meet to group and trello ai"
python -c "import flask" 2>nul
if %errorlevel% neq 0 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install Python dependencies!
        pause
        exit /b 1
    )
)
cd ..

echo.
echo Starting Trello AI Desktop...
echo.
echo The application will open in a new window.
echo You can minimize it to the system tray.
echo.

:: Start Electron app
npm start

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start the application!
    pause
)