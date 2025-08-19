@echo off
echo ====================================
echo   🚀 Trello AI Web Application  
echo ====================================
echo.

:: Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python is not installed!
    echo Please install Python from https://python.org/
    pause
    exit /b 1
)

echo ✅ Python found

:: Navigate to app directory
cd "google meet to group and trello ai"

:: Check if .env exists
if not exist ".env" (
    echo ⚠️  WARNING: .env file not found!
    echo Please copy .env.example to .env and configure your API keys
    echo.
    if exist "../.env.example" (
        echo Copying .env.example to .env...
        copy "..\env.example" ".env" >nul
        echo ✅ .env file created. Please edit it with your API keys.
    )
    echo.
    pause
)

:: Install dependencies if needed
echo 📦 Checking dependencies...
pip show flask >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo ✅ Dependencies ready
echo.
echo 🌐 Starting Flask server...
echo.
echo Open your browser to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

:: Start the Flask application
python web_app.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Failed to start the application!
    echo Check the error messages above for details.
    pause
)

echo.
echo 👋 Application stopped
pause