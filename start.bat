@echo off
cd /d "%~dp0backend"
call venv\Scripts\activate
start "" cmd /c "timeout /t 3 >nul & start http://localhost:8000"
uvicorn main:app --reload
