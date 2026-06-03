#!/bin/sh
# Helper script to restart the irrigazione_dashboard_v2 addon services
# Usage: run this inside the add-on container as root (or from the host path)

set -eu

ROOT_DIR="/addons/local/irrigazione_dashboard_v2"
if [ ! -d "$ROOT_DIR" ]; then
    # fallback locations used by some setups
    if [ -d "/share/addons/local/irrigazione_dashboard_v2" ]; then
        ROOT_DIR="/share/addons/local/irrigazione_dashboard_v2"
    elif [ -d "/data/addons/local/irrigazione_dashboard_v2" ]; then
        ROOT_DIR="/data/addons/local/irrigazione_dashboard_v2"
    fi
fi

echo "Using addon root: $ROOT_DIR"

RUN_SH="$ROOT_DIR/run.sh"
if [ ! -f "$RUN_SH" ]; then
    echo "ERROR: run.sh not found at $RUN_SH" >&2
    exit 2
fi

echo "Stopping running servers (if any)..."
# attempt graceful stop
pkill -f entities_server.py || true
pkill -f server.py || true
sleep 1

echo "Starting servers via run.sh (background)..."
cd "$ROOT_DIR"
nohup sh ./run.sh > /tmp/irrigazione.log 2>&1 &
sleep 1
echo "Launched run.sh, tailing last 200 lines of /tmp/irrigazione.log"
tail -n 200 /tmp/irrigazione.log || true

echo "If Supervisor is managing the addon, prefer to restart it from Supervisor UI instead of running this script."
