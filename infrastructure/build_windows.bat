@echo off
REM Run this on Windows to create dist\DungeonEscape.exe.
py -m pip install --user pyinstaller pygame-ce
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --windowed --paths . --icon "frontend\assets\dungeon_escape_icon.ico" --add-data "frontend\assets;frontend\assets" --name DungeonEscape backend\dungeon_improved.py
