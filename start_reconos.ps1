Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Launching ReconOS AI - Financial Operations Platform" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "backend")
$env:PYTHONPATH = (Join-Path $ScriptDir "backend")

$PythonExe = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Error "Python virtual environment not found in .venv."
    exit 1
}

Write-Host "Starting ReconOS AI unified server on http://localhost:8000 ..." -ForegroundColor Green
Write-Host "- Backend API & Swagger Docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "- Enterprise UI Dashboard: http://localhost:8000/" -ForegroundColor Yellow
Write-Host ""
Write-Host "Demo Credentials:" -ForegroundColor Cyan
Write-Host "Email: admin@harareretail.co.zw" -ForegroundColor White
Write-Host "Password: SuperSecret123!" -ForegroundColor White
Write-Host ""

Start-Process "http://localhost:8000/"
& $PythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
