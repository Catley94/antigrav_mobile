#!/bin/bash
set -e

VENV_DIR=".venv"
REQUIREMENTS="requirements.txt"

# 1. Select Python Interpreter
# We prefer /usr/bin/python3 because it usually has dbus-python and gi (PyGObject) 
# installed system-wide, which are hard to compile in a pure venv without headers.
if [ -x "/usr/bin/python3" ]; then
    PYTHON_CMD="/usr/bin/python3"
else
    PYTHON_CMD="python3"
fi

echo "Using Python: $PYTHON_CMD"

# 2. Create Venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    # --system-site-packages is CRITICAL here to see the system's dbus/gi
    $PYTHON_CMD -m venv $VENV_DIR --system-site-packages
fi

# 3. Activate Venv
source "$VENV_DIR/bin/activate"

# 4. Install Dependencies
if [ -f "$REQUIREMENTS" ]; then
    echo "Installing/Updating dependencies from $REQUIREMENTS..."
    pip install -r $REQUIREMENTS --disable-pip-version-check
fi

# 5. Check Critical Libraries (dbus, gi)
# We do a quick check. If they are missing, we warn the user, but we don't try to install 
# them via pip automatically because that usually fails without dev headers.
python3 -c "import dbus" 2>/dev/null || {
    echo "⚠️  WARNING: 'dbus' module not found!"
    echo "   Since we are using --system-site-packages, please ensure you have:"
    echo "   sudo apt install python3-dbus"
    echo "   If you really want to compile it, uncomment it in requirements.txt (requires libdbus-1-dev)."
}

python3 -c "import gi" 2>/dev/null || {
    echo "⚠️  WARNING: 'gi' (PyGObject) module not found!"
    echo "   Please ensure you have:"
    echo "   sudo apt install python3-gi"
}

echo "---------------------------------------------------"
echo "Starting Bridge in Venv ($(which python3))"
echo "Topic: antigrav_sam_notifications"
echo "---------------------------------------------------"

python3 bridge.py
