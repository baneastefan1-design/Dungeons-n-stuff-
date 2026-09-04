@echo off
REM Run this on Windows to create dist\DungeonEscape.exe.
py -m pip install --user pyinstaller pygame-ce
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --windowed --icon "assets\dungeon_escape_icon.ico" --add-data "assets\start_screen.png;assets" --add-data "assets\illustrated;assets\illustrated" --add-data "assets\dungeon_escape_icon.png;assets" --name DungeonEscape dungeon_improved.py
