# Run the Payroll application using the virtual environment
$VENV_PATH = "$PSScriptRoot\.venv\Scripts\python.exe"
$APP_PATH = "$PSScriptRoot\app.py"

if (Test-Path $VENV_PATH) {
    Write-Host "Starting Payroll Application..." -ForegroundColor Cyan
    & $VENV_PATH $APP_PATH
} else {
    Write-Host "Error: Virtual environment not found at $VENV_PATH" -ForegroundColor Red
    Write-Host "Please ensure you have run the setup correctly." -ForegroundColor Yellow
}
