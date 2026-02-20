@echo off
setlocal
cd /d "%~dp0"

:: 1. Verify Python
py --version >nul 2>&1
if %errorlevel% == 0 (set PY=py) else (set PY=python)

:: 2. Setup/Activate Environment
if not exist "venv" (
    %PY% -m venv venv
)
call venv\Scripts\activate

:: 3. Install Requirements (Only if needed)
pip install -r requirements.txt --quiet

:: 4. Launch Application
echo [INFO] Starting Matchbox ERP...
start "" http://127.0.0.1:5000
python "Payroll/Payroll/app.py"
pause