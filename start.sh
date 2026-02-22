#!/bin/bash
# Start the dashboard with gunicorn
# Usage: ./start.sh

cd "$(dirname "$0")"

export PYTHONPATH="$PWD/scripts/visualization:$PYTHONPATH"

exec gunicorn \
    --chdir scripts/visualization \
    dashboard_app:server \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
