@echo off
echo ========================================================
echo   Running ReconOS AI Automated Test Suite (Pytest)
echo ========================================================
echo.

cd /d "%~dp0backend"
set PYTHONPATH=%~dp0backend

"%~dp0.venv\Scripts\python.exe" -m pytest tests -v
echo.
pause
