#!/bin/bash
echo "Starting Antigravity Notification Bridge..."

# Check if requests is installed
python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required 'requests' library..."
    # Try apt first if on Debian/Ubuntu for system-wide, else pip
    if command -v apt-get &> /dev/null; then
         # This might need sudo, which is interactive. Better to try pip user install first.
         pip3 install requests --break-system-packages 2>/dev/null || pip3 install requests --user
    else
         pip3 install requests --user
    fi
fi

echo "Topic: antigrav_sam_notifications"
python3 bridge.py
