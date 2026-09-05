# Dungeon Escape

A compact Pygame dungeon crawler. Find the treasure, avoid the dragon, and return to the blue portal—or retreat through it once the dragon wakes.

The code is split by responsibility:

- `dungeon_improved.py` handles the CLI and Pygame event loop.
- `game.py` contains game state, rules, map generation, and movement.
- `pathfinding.py` contains the reusable A* implementation.
- `rendering.py` draws the game without changing its state.
- `asset_manager.py` selects visual themes and lazily loads optional artwork.
- `assets/start_screen.png` provides the illustrated mode-selection backdrop.
- `assets/illustrated/` contains the small-screen gameplay theme: hero, dragons, portal, open treasure, floors, walls, scorch, and fog.

## One-Line Install and Run

These commands install the game for the current user, create a reusable launcher, and start it. They require internet access and Python 3; the first run also downloads Pygame.

macOS or Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/baneastefan1-design/Dungeons-n-stuff-/main/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/baneastefan1-design/Dungeons-n-stuff-/main/install.ps1 | iex
```

### macOS

Open `dist/Dungeon Escape.app` to play without installing Python or Pygame. Its lifetime statistics are stored in `~/Library/Application Support/Dungeon Escape/dungeon_stats.json`.

Run `bash build_macos.sh` on a Mac to build the app bundle. The bundle and development window use the included Dungeon Escape icon.

You can also double-click `run_mac.command` in Finder. It opens the packaged app when present, or runs the local development version when `.venv` exists.


### Linux

Run `bash build_linux.sh` on a Linux machine to create `dist/DungeonEscape`, a standalone executable. Its statistics are saved in `~/.local/share/Dungeon Escape/dungeon_stats.json` (or `$XDG_DATA_HOME` when set). It must be built on Linux because native application bundles cannot be cross-compiled from macOS.

### Windows

Run `build_windows.bat` on a Windows machine to create `dist\DungeonEscape.exe`, a standalone game executable. Its statistics are saved in `%APPDATA%\Dungeon Escape\dungeon_stats.json`. It must be built on Windows because `.exe` files cannot be cross-compiled from macOS.

### Browser / Docker (2.0)

Build and host the illustrated browser edition with Docker:

```bash
docker compose up --build
```

Open `http://localhost:8080` on a computer or phone on the same network (replace `localhost` with the host computer's LAN address for a phone). The browser draws the included illustrated artwork in an HTML Canvas, while a Python WebSocket service runs the existing `game.py` maze, movement, wall-discovery, treasure, and dragon rules. It supports keyboard controls, touch buttons, and swipes.

Browser players enter an explorer name before a run. Completed results are saved by the Python server in a persistent Docker SQLite volume and can be viewed with the **Rankings** button. Use a unique name if multiple people share the server.

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

To reveal the full map, including all walls and the sleeping dragon, while testing dragon movement, run:

```bash
.venv/bin/python dungeon_improved.py -d
```

Choose **Normal** or **Hard** from the start screen. Hard mode gives the dragon full knowledge of the walls while Normal mode makes it discover walls through collisions. Both use A* pathfinding.

Debug mode is available only through the `-d` console option. It overlays a translucent phantom dragon running the opposite difficulty, marked `H` for hard or `N` for normal, so their routes can be compared on the same map.

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
- The illustrated art style is selected by default; Classic remains available from the start screen.
- Explore the random 8×8 dungeon to find the treasure chest.
- Return to the portal with the treasure to win.
- Once the dragon wakes, you may return to the portal without the treasure for a safe retreat.

## Dungeon Rules

- Walls are hidden until you try to walk into them. The treasure always has a reachable route from the portal.
- Tiles you enter stay lit; unexplored distant tiles remain under fog.
- The dragon wakes when you enter its danger radius. It is visible through fog when awake and leaves scorched tiles behind.
- The dragon uses A* pathfinding, discovers walls by bumping into them, remembers them while chasing, and immediately reroutes without losing its move. It can move diagonally only across a fully clear corner.
- Collecting the chest plays an opening animation, marks its location with an X, and makes the portal glow gold.
- The game plays generated sound effects for movement, walls, treasure, the dragon, wins, and losses.
- When a run ends, the entire map and every wall are revealed.
- Lifetime wins, dragon wins, retreats, total winning moves, best winning move count, and highest streak are saved in `dungeon_stats.json` beside the game. The HUD shows `W`, `D`, `E`, `S`, and `H` for wins, dragon wins, escapes, current streak, and highest streak.
- Each consecutive treasure win adds one row and column to the next dungeon and adds three walls. A safe retreat preserves the current streak and difficulty; a dragon win resets the next game to the default 8×8 dungeon while retaining the all-time highest streak. The grid is capped at 16×16 and is reduced as needed to stay within the current display.

## Development Check

```bash
.venv/bin/python -m py_compile dungeon_improved.py game.py pathfinding.py rendering.py asset_manager.py
```
