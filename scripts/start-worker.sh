#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
    echo "Backend venv not found. Run start-backend.sh first."
    exit 1
fi

source .venv/bin/activate

echo "Starting Agentic Builder Worker..."
python -m app.workers.task_worker
