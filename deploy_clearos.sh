#!/usr/bin/env bash
# ==============================================================================
# Notes Library - Automated Deployment Script for ClearOS 7 (CentOS 7 / RHEL 7)
# Target Environment: ClearOS 7 with Python 3.8.17 & MariaDB / MySQL
# ==============================================================================

set -e

echo "------------------------------------------------------------------------"
echo "  Deploying Notes Library on ClearOS 7 (Python 3.8.17)"
echo "------------------------------------------------------------------------"

# 1. Locate Python 3.8 executable
PYTHON_BIN=""
if command -v python3.8 &>/dev/null; then
    PYTHON_BIN="python3.8"
elif command -v python3 &>/dev/null && python3 -c "import sys; exit(0 if sys.version_info[:2]==(3,8) else 1)" &>/dev/null; then
    PYTHON_BIN="python3"
elif [ -f "/usr/local/bin/python3.8" ]; then
    PYTHON_BIN="/usr/local/bin/python3.8"
elif [ -f "/opt/rh/rh-python38/root/usr/bin/python3.8" ]; then
    PYTHON_BIN="/opt/rh/rh-python38/root/usr/bin/python3.8"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3.8.17 not found in PATH."
    echo "Please ensure Python 3.8 is installed on your ClearOS 7 system."
    exit 1
fi

echo "[INFO] Using Python: $($PYTHON_BIN --version) at $(which $PYTHON_BIN 2>/dev/null || echo $PYTHON_BIN)"

# 2. Check / Start MariaDB
echo "[INFO] Checking MariaDB service..."
if systemctl is-active --quiet mariadb; then
    echo "[INFO] MariaDB is already running."
elif systemctl is-active --quiet mysqld; then
    echo "[INFO] MySQL is already running."
else
    echo "[INFO] Starting MariaDB service..."
    systemctl start mariadb || systemctl start mysqld || echo "[WARN] Could not automatically start MariaDB. Please ensure it is running."
fi

# 3. Create/recreate Python virtual environment
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

if [ ! -d "venv" ]; then
    echo "[INFO] Creating isolated Python 3.8 virtual environment..."
    $PYTHON_BIN -m venv venv
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# 4. Upgrade pip inside venv and install dependencies
echo "[INFO] Upgrading pip inside virtual environment..."
pip install --upgrade "pip<24.1" "setuptools<69.0.0"

echo "[INFO] Installing production dependencies from requirements.txt..."
pip install -r requirements.txt

# 5. Run Database Migration & Table Verification
echo "[INFO] Initializing database tables & default superuser..."
export DB_USER="${DB_USER:-root}"
export DB_PASSWORD="${DB_PASSWORD:-MySQL@123}"
export DB_NAME="${DB_NAME:-notes_library}"
export DB_PORT="${DB_PORT:-3306}"
export DB_HOST="${DB_HOST:-localhost}"
python db_setup.py

# 6. Verify roster loading
echo "[INFO] Verifying student roster loading from cslist.json..."
python -c "import app; print(f'[SUCCESS] Verified {len(app.STUDENT_ROSTER)} students loaded into memory.')"

# 7. Systemd Service Deployment (Instructions)
echo "------------------------------------------------------------------------"
echo "[SUCCESS] Notes Library is ready for production on ClearOS 7!"
echo "------------------------------------------------------------------------"
echo "To run interactively in production with Gunicorn:"
echo "    source venv/bin/activate"
echo "    gunicorn -w 4 -b 0.0.0.0:3000 wsgi:app"
echo ""
echo "To install as a permanent systemd background service:"
echo "    cp noteslib.service /etc/systemd/system/"
echo "    # Edit /etc/systemd/system/noteslib.service with your directory path & DB password"
echo "    systemctl daemon-reload"
echo "    systemctl enable noteslib"
echo "    systemctl start noteslib"
echo "    systemctl status noteslib"
echo "------------------------------------------------------------------------"
