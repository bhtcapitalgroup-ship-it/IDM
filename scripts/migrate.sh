#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

cd "$BACKEND_DIR"
source .venv/bin/activate

echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."
