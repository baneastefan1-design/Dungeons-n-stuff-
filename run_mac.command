#!/bin/bash
# Double-click this file in Finder to launch Dungeon Escape on macOS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$SCRIPT_DIR/dist/Dungeon Escape.app"

if [[ -d "$APP_PATH" ]]; then
    open "$APP_PATH"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    cd "$SCRIPT_DIR"
    exec .venv/bin/python dungeon_improved.py
else
    osascript -e 'display alert "Dungeon Escape cannot start" message "Download or build the macOS app first, or create the local .venv environment."'
fi
