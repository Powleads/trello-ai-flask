@echo off
setlocal
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.11+ and re-run.
  pause
  exit /b 1
)

REM Create venv
python -m venv .venv
if errorlevel 1 (
  echo Failed to create virtual environment.
  pause
  exit /b 1
)

REM Activate and install deps
call .venv\Scripts\activate
if exist requirements.txt (
  pip install --upgrade pip
  pip install -r requirements.txt
)

REM Fallback: editable install if pyproject exists
if exist pyproject.toml (
  pip install -e . || echo Skipping editable install.
)

REM Node deps if present
if exist package.json (
  where npm >nul 2>nul && npm install
)

REM Open in VS Code
where code >nul 2>nul
if errorlevel 1 (
  echo VS Code 'code' CLI not found. Install 'Shell Command: Install code command in PATH' from VS Code.
) else (
  code .
)
echo Done!
pause
