#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -d ".venv" ] && {
  ! ./.venv/bin/python -c 'import sys' >/dev/null 2>&1 ||
  ! ./.venv/bin/pip --version >/dev/null 2>&1
}; then
  echo "Recreating invalid virtual environment..."
  rm -rf .venv
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
fi

./.venv/bin/pip install -r requirements.txt

exec ./.venv/bin/uvicorn app.main:app --reload --reload-dir app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"