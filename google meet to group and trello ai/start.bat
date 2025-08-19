@echo off
echo 🚀 Meeting Automation Tool
echo.

if "%1"=="" (
    echo Quick commands:
    echo   start setup       - Setup everything
    echo   start test        - Test all integrations  
    echo   start sample      - Process sample transcript
    echo   start process FILE - Process your file
    echo.
    echo Example: start process my_transcript.txt
    goto end
)

if "%1"=="setup" (
    echo 🔧 Setting up...
    python setup.py
    goto end
)

if "%1"=="test" (
    echo 🧪 Testing integrations...
    python quick_test.py
    goto end
)

if "%1"=="sample" (
    echo 📝 Processing sample...
    python run.py sample
    goto end
)

if "%1"=="process" (
    if "%2"=="" (
        echo ❌ Please provide a file path
        echo Example: start process my_transcript.txt
        goto end
    )
    echo 📝 Processing %2...
    python run.py process "%2"
    goto end
)

echo ❌ Unknown command: %1

:end
pause