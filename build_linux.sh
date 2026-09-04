#!/usr/bin/env bash
# Run this on Linux to produce dist/DungeonEscape, a standalone executable.
set -euo pipefail

python3 -m pip install --user pyinstaller pygame-ce
python3 -m PyInstaller --noconfirm --clean --onefile --windowed \
  --add-data "assets/start_screen.png:assets" \
  --add-data "assets/illustrated:assets/illustrated" \
  --add-data "assets/dungeon_escape_icon.png:assets" \
  --name DungeonEscape dungeon_improved.py
