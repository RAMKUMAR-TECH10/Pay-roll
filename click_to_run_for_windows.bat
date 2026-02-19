@echo off
title Matchbox ERP - Automated Launcher
setlocal

:: 1. Use the 'py' launcher to find Python (more reliable than 'python')
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found. 
    echo Please install Python from python.org and ensure "Add to PATH" is checked.
    pause
    exit /b
)

:: 2. Setup/Activate Local Virtual Environment
if not exist venv (
    echo [INFO] No local environment found. Starting one-time setup...
    :: Use 'py -m' instead of 'python -m'
    py -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
    
    echo [INFO] Activating environment...
    call venv\Scripts\activate
    
    echo [INFO] Installing required libraries...
    python -m pip install -r requirements.txt
) else (
    echo [INFO] Environment detected. Activating...
    call venv\Scripts\activate
)

:: 3. Run the Application
echo [INFO] Opening Matchbox ERP in your browser...
start "" http://127.0.0.1:5000

echo [INFO] Launching Server...
cd Payroll
:: Now that venv is active, 'python' will refer to the local venv python
python app.py
pause