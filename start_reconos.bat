@echo off
echo ========================================================
echo   Launching ReconOS AI - Financial Operations Platform
echo ========================================================
echo.

cd /d "%~dp0backend"
set PYTHONPATH=%~dp0backend

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in .venv.
    pause
    exit /b 1
)

echo Starting ReconOS AI server on http://localhost:8000 ...
echo - Backend API & Docs: http://localhost:8000/docs
echo - Enterprise UI Dashboard: http://localhost:8000/
echo.
echo Demo Credentials:
echo Email: admin@harareretail.co.zw
echo Password: SuperSecret123!
echo.

start http://localhost:8000/
"%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
