#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

if [ ! -f ".venv/.deps_installed" ] || [ "requirements.txt" -nt ".venv/.deps_installed" ]; then
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  touch .venv/.deps_installed
fi

python ilmeteo_gioiosa.py
