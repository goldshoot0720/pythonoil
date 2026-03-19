#!/bin/zsh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/src"
"$PYTHON_BIN" "$PROJECT_ROOT/run_oil_tracker_silent.pyw"
