@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo The project Python environment was not found.
    echo Follow the setup instructions in README.md first.
    pause
    exit /b 1
)

echo Starting EduAI Audit at http://127.0.0.1:8501
echo Keep this window open while using the app. Press Ctrl+C to stop it.
".venv\Scripts\python.exe" -m streamlit run app.py --server.port=8501
if errorlevel 1 pause
