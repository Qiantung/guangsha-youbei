#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -f .venv/bin/python ]; then
  python3 -m venv .venv
fi
if [ ! -f .venv/dependencies-ready ]; then
  .venv/bin/python -m pip install -r requirements.txt
  touch .venv/dependencies-ready
fi
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
