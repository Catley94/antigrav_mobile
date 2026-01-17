#!/bin/bash
# Script to start the local Ntfy server

echo "Starting Local Ntfy Server..."
echo "Listening on: http://192.168.1.159:8080"
echo "Topic URL:    http://192.168.1.159:8080/antigrav_sam_notifications"

# Ensure cache directory exists
mkdir -p cache

# Start ntfy with our local config
# Exempt localhost from rate limiting to avoid issues during development
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ntfy serve \
    --config "$SCRIPT_DIR/server.yml" \
    --visitor-request-limit-exempt-hosts "127.0.0.1,localhost,::1"
