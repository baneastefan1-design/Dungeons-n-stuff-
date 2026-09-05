#!/usr/bin/env bash
# Run this on macOS to produce dist/Dungeon Escape.app.
set -euo pipefail

python3 -m pip install pyinstaller pygame-ce
python3 -m PyInstaller --noconfirm --clean --windowed --paths . \
  --icon frontend/assets/dungeon_escape_icon.icns \
  --add-data "frontend/assets:frontend/assets" \
  --name "Dungeon Escape" backend/dungeon_improved.py
