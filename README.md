# Dungeon Escape

A compact Pygame dungeon crawler. Find the treasure, avoid the dragon, and return to the blue portal—or retreat through it once the dragon wakes.

## Run the Game

The project uses a local virtual environment and `pygame-ce`.

```bash
source .venv/bin/activate
python dungeon_improved.py
```

Or run it directly:

```bash
.venv/bin/python dungeon_improved.py
```

## Standalone macOS App

Open `dist/Dungeon Escape.app` to play without installing Python or Pygame. Its lifetime statistics are stored in `~/Library/Application Support/Dungeon Escape/dungeon_stats.json`.

You can also double-click `run_mac.command` in Finder. It opens the packaged app when present, or runs the local development version when `.venv` exists.

### Linux

Run `bash build_linux.sh` on a Linux machine to create `dist/DungeonEscape`, a standalone executable. Its statistics are saved in `~/.local/share/Dungeon Escape/dungeon_stats.json` (or `$XDG_DATA_HOME` when set). It must be built on Linux because native application bundles cannot be cross-compiled from macOS.

### Windows

Run `build_windows.bat` on a Windows machine to create `dist\DungeonEscape.exe`, a standalone game executable. Its statistics are saved in `%APPDATA%\Dungeon Escape\dungeon_stats.json`. It must be built on Windows because `.exe` files cannot be cross-compiled from macOS.

If you need to recreate the environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install pygame-ce
```

## Controls

| Action | Control |
| --- | --- |
| Move | Arrow keys or `W` `A` `S` `D` |
| Move on touch devices | Swipe |
| Restart after a completed run | `R` |
| Quit | `Esc` |

## How to Play

- Start at the blue portal in the top-left corner.
- Explore the random 8×8 dungeon to find the treasure chest.
- Return to the portal with the treasure to win.
- Once the dragon wakes, you may return to the portal without the treasure for a safe retreat.

## Dungeon Rules

- Walls are hidden until you try to walk into them. The treasure always has a reachable route from the portal.
- Tiles you enter stay lit; unexplored distant tiles remain under fog.
- The dragon wakes when you enter its danger radius. It is visible through fog when awake and leaves scorched tiles behind.
- The dragon obeys walls. It can move diagonally only across a fully clear corner.
- Collecting the chest plays an opening animation, marks its location with an X, and makes the portal glow gold.
- The game plays generated sound effects for movement, walls, treasure, the dragon, wins, and losses.
- When a run ends, the entire map and every wall are revealed.
- Lifetime wins, dragon wins, retreats, total winning moves, best winning move count, and highest streak are saved in `dungeon_stats.json` beside the game. The HUD shows `W`, `D`, `E`, `S`, and `H` for wins, dragon wins, escapes, current streak, and highest streak.
- Each consecutive treasure win adds one row and column to the next dungeon and adds three walls. A safe retreat preserves the current streak and difficulty; a dragon win resets the next game to the default 8×8 dungeon while retaining the all-time highest streak. The grid is capped at 16×16 and is reduced as needed to stay within the current display.

## Development Check

```bash
.venv/bin/python -m py_compile dungeon_improved.py
```
