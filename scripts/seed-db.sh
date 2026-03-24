#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

cd "$BACKEND_DIR"
source .venv/bin/activate

echo "Seeding database with default agents, tools, and admin user..."
python -m app.seed
