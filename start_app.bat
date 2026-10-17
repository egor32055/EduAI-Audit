@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo The project Python environment was not found.
    echo Follow the setup instructions in README.md first.
    pause
    exit /b 1
)

echo Opening EduAI Audit at http://127.0.0.1:8501
".venv\Scripts\python.exe" launch_app.py
if errorlevel 1 pause
