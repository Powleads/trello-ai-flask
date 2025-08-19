@echo off
echo Starting TRELLO AI Application...
echo.
cd /d "C:\Users\james\Desktop\TRELLO AI\google meet to group and trello ai"
echo Current directory: %CD%
echo.
echo Starting web application on http://localhost:5000/
echo Press Ctrl+C to stop the server
echo.
python web_app.py
pause