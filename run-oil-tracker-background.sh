#!/bin/zsh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif [[ -x "/opt/homebrew/bin/python3" ]]; then
  PYTHON_BIN="/opt/homebrew/bin/python3"
elif [[ -x "/usr/local/bin/python3" ]]; then
  PYTHON_BIN="/usr/local/bin/python3"
elif [[ -x "/usr/bin/python3" ]]; then
  PYTHON_BIN="/usr/bin/python3"
else
  PYTHON_BIN="$(command -v python3)"
fi

cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/src"
"$PYTHON_BIN" "$PROJECT_ROOT/run_oil_tracker_silent.pyw"
