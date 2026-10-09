#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  echo "Project virtual environment was not found: $PROJECT_ROOT/.venv"
  exit 1
fi

source "$PROJECT_ROOT/.venv/bin/activate"

cd "$PROJECT_ROOT/app"

python access_review_worker.py &
WORKER_PID=$!

cleanup() {
  kill "$WORKER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

flask --app app run --host 127.0.0.1 --port 5000
