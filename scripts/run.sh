#!/usr/bin/env bash
# Launch Queue Sniper from project root (Linux Mint / Ubuntu)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  echo "Run setup first: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
exec "$ROOT/.venv/bin/python3" "$ROOT/main.py"
