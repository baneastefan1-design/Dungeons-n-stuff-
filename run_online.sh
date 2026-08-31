#!/usr/bin/env bash
# Start the latest game directly from GitHub on macOS or Linux.
set -euo pipefail

REPOSITORY="https://raw.githubusercontent.com/baneastefan1-design/Dungeons-n-stuff-/main"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required. Install it, then run this command again." >&2
    exit 1
fi

if [[ "$(uname)" == "Darwin" ]]; then
    export DUNGEON_STATS_FILE="$HOME/Library/Application Support/Dungeon Escape/dungeon_stats.json"
else
    export DUNGEON_STATS_FILE="${XDG_DATA_HOME:-$HOME/.local/share}/Dungeon Escape/dungeon_stats.json"
fi

curl -fsSL "$REPOSITORY/dungeon_improved.py" -o "$WORK_DIR/dungeon_improved.py"
python3 -m venv "$WORK_DIR/.venv"
"$WORK_DIR/.venv/bin/python" -m pip install --quiet --disable-pip-version-check pygame-ce
exec "$WORK_DIR/.venv/bin/python" "$WORK_DIR/dungeon_improved.py"
