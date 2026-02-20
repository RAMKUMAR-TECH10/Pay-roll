#!/bin/bash

# 1. Get the directory where the script is located
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$BASE_DIR"

echo "[INFO] Checking for Python3 and Venv..."

# 2. Check for Python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed."
    echo "Please run: sudo apt update && sudo apt install python3 python3-venv"
    exit 1
fi

# 3. Handle Virtual Environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating fresh virtual environment..."
    python3 -m venv venv
fi

# 4. Activate and Sync
source venv/bin/activate
echo "[INFO] Installing/Updating requirements..."
pip install -r requirements.txt --quiet

# 5. Launch Browser (Handles different Linux distros)
echo "[INFO] Opening Matchbox ERP..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:5000
elif command -v gnome-open &> /dev/null; then
    gnome-open http://127.0.0.1:5000
fi

# 6. Start the Server (Using your triple-nested path)
echo "[INFO] Starting Flask Server..."
python3 "Payroll/Payroll/app.py"