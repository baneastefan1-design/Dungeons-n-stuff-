#!/usr/bin/env bash
# Run this on Linux to produce dist/DungeonEscape, a standalone executable.
set -euo pipefail

python3 -m pip install --user pyinstaller pygame-ce
python3 -m PyInstaller --noconfirm --clean --onefile --windowed \
  --name DungeonEscape dungeon_improved.py
