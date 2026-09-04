#!/usr/bin/env bash
# Run this on macOS to produce dist/Dungeon Escape.app.
set -euo pipefail

python3 -m pip install pyinstaller pygame-ce
python3 -m PyInstaller --noconfirm --clean --windowed \
  --icon assets/dungeon_escape_icon.icns \
  --add-data "assets/start_screen.png:assets" \
  --add-data "assets/illustrated:assets/illustrated" \
  --add-data "assets/dungeon_escape_icon.png:assets" \
  --name "Dungeon Escape" dungeon_improved.py
