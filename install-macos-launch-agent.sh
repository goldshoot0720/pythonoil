#!/bin/zsh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/com.goldshoot0720.pythonoil.plist"
TEMPLATE_PATH="$PROJECT_ROOT/macos/com.goldshoot0720.pythonoil.plist.template"

mkdir -p "$LAUNCH_AGENTS_DIR"
mkdir -p "$PROJECT_ROOT/data"

python3 - "$TEMPLATE_PATH" "$PLIST_PATH" "$PROJECT_ROOT" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
plist_path = Path(sys.argv[2])
project_root = sys.argv[3]
working_directory = str(Path.home())
venv_python = f"{project_root}/.venv/bin/python"

if Path(venv_python).exists():
    python_bin = venv_python
elif Path("/opt/homebrew/bin/python3").exists():
    python_bin = "/opt/homebrew/bin/python3"
elif Path("/usr/local/bin/python3").exists():
    python_bin = "/usr/local/bin/python3"
else:
    python_bin = "/usr/bin/python3"

command = (
    f'export PYTHONPATH="{project_root}/src" && '
    f'"{python_bin}" "{project_root}/run_oil_tracker_silent.pyw"'
)

content = template_path.read_text(encoding="utf-8")
content = content.replace("__PROJECT_ROOT__", project_root)
content = content.replace("__WORKING_DIRECTORY__", working_directory)
content = content.replace("__COMMAND__", command)
plist_path.write_text(content, encoding="utf-8")
PY

chmod 644 "$PLIST_PATH"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/com.goldshoot0720.pythonoil"
launchctl kickstart -k "gui/$(id -u)/com.goldshoot0720.pythonoil"

echo "Installed launch agent:"
echo "  $PLIST_PATH"
echo
echo "Schedule:"
echo "  - Runs every day at 13:00"
echo "  - Runs once at each login via RunAtLoad"
echo
echo "Logs:"
echo "  - $PROJECT_ROOT/data/oil_tracker.log"
echo "  - $PROJECT_ROOT/data/launchd.stdout.log"
echo "  - $PROJECT_ROOT/data/launchd.stderr.log"
