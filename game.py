"""Game state, dungeon rules, audio, and dragon behavior."""

from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import random
import sys

import pygame

from pathfinding import astar_path

GRID_SIZE = 8
TILE_SIZE = 56
HUD_HEIGHT = 72
MENU_HEIGHT = 54
WIDTH = GRID_SIZE * TILE_SIZE
HEIGHT = GRID_SIZE * TILE_SIZE + HUD_HEIGHT + MENU_HEIGHT
FPS = 60
WALL_COUNT = 12
EXTRA_WALLS = 0
MAX_GRID_SIZE = 16
MAX_WEB_LEVEL = 54
MIN_TILE_SIZE = 42
WAKE_DISTANCE = 3
SWIPE_THRESHOLD = 28
VISION_RADIUS = 2
AUDIO_RATE = 44_100


def resource_path(relative_path: str) -> Path:
    """Resolve bundled assets in development and PyInstaller builds."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base_path / relative_path


def statistics_file() -> Path:
    """Choose a writable stats location both in development and in the app."""
    if sys.platform == "emscripten":
        # Pygbag maps /data to browser-backed storage, keeping web statistics
        # separate from the read-only game bundle.
        return Path("/data/dungeon-escape/dungeon_stats.json")
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            data_directory = Path.home() / "Library" / "Application Support"
        elif sys.platform == "win32":
            data_directory = Path(os.environ.get("APPDATA", Path.home()))
        else:
            data_directory = Path(
                os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
            )
        return data_directory / "Dungeon Escape" / "dungeon_stats.json"
    return Path(__file__).with_name("dungeon_stats.json")


STATS_FILE = statistics_file()

BG = (12, 15, 24)
FLOOR_A = (27, 33, 48)
FLOOR_B = (31, 38, 55)
GRID = (47, 56, 76)
HUD_BG = (18, 22, 33)
WHITE = (235, 239, 247)
MUTED = (156, 166, 188)
BLUE = (75, 158, 255)
GOLD = (255, 206, 73)
RED = (235, 76, 89)
ORANGE = (255, 157, 66)
GREEN = (78, 216, 145)
WALL = (171, 89, 102)

Position = tuple[int, int]
Wall = tuple[int, int]
SOUNDS: dict[str, pygame.mixer.Sound] = {}


@dataclass
class Statistics:
    """Lifetime results, saved beside the game so they survive restarts."""

    wins: int = 0
    dragon_wins: int = 0
    escapes: int = 0
    total_win_moves: int = 0
    best_win_moves: int | None = None
    win_streak: int = 0
    highest_win_streak: int = 0


@dataclass
class GameState:
    grid_size: int = field(default_factory=lambda: GRID_SIZE)
    wall_count: int = WALL_COUNT
    extra_walls: int = EXTRA_WALLS
    player: Position = (0, 0)
    start: Position = (0, 0)
    visited: set[Position] = field(default_factory=set)
    treasure: Position = (0, 0)
    dragon: Position = (0, 0)
    horizontal_walls: set[Wall] = field(default_factory=set)
    vertical_walls: set[Wall] = field(default_factory=set)
    discovered_h: set[Wall] = field(default_factory=set)
    discovered_v: set[Wall] = field(default_factory=set)
    dragon_discovered_h: set[Wall] = field(default_factory=set)
    dragon_discovered_v: set[Wall] = field(default_factory=set)
    hard_mode: bool = False
    level: int = 1
    scorched: set[Position] = field(default_factory=set)
    moves: int = 0
    has_treasure: bool = False
    dragon_awake: bool = False
    status: str = "playing"
    flash: str = "Find the treasure and return to the portal."
    flash_color: tuple[int, int, int] = MUTED
    flash_until: int = 0
    treasure_open_until: int = 0
    shake_until: int = 0
    result_recorded: bool = False


def load_statistics() -> Statistics:
    """Load saved lifetime results, starting fresh if the file is unavailable."""
    try:
        saved = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        return Statistics(
            wins=max(0, int(saved.get("wins", 0))),
            dragon_wins=max(0, int(saved.get("dragon_wins", 0))),
            escapes=max(0, int(saved.get("escapes", 0))),
            total_win_moves=max(0, int(saved.get("total_win_moves", 0))),
            best_win_moves=(
                max(0, int(saved["best_win_moves"]))
                if saved.get("best_win_moves") is not None
                else None
            ),
            win_streak=max(0, int(saved.get("win_streak", 0))),
            highest_win_streak=max(
                0, int(saved.get("highest_win_streak", saved.get("win_streak", 0)))
            ),
        )
    except (OSError, ValueError, TypeError):
        return Statistics()


def save_statistics(statistics: Statistics) -> None:
    """Persist results without making a save failure interrupt the game."""
    try:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(
            json.dumps(statistics.__dict__, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        pass


def record_result(
    state: GameState,
    statistics: Statistics | None,
    status: str,
    *,
    persist: bool = True,
) -> None:
    """Record each completed run once, including moves used for treasure wins."""
    state.status = status
    if statistics is None or state.result_recorded:
        return
    state.result_recorded = True
    if status == "won":
        statistics.wins += 1
        statistics.win_streak += 1
        statistics.highest_win_streak = max(
            statistics.highest_win_streak, statistics.win_streak
        )
        statistics.total_win_moves += state.moves
        if statistics.best_win_moves is None or state.moves < statistics.best_win_moves:
            statistics.best_win_moves = state.moves
    elif status == "eaten":
        statistics.dragon_wins += 1
        statistics.win_streak = 0
    elif status == "escaped":
        statistics.escapes += 1
    if persist:
        save_statistics(statistics)


def configure_difficulty(
    statistics: Statistics, *, max_grid_size: int | None = None
) -> None:
    """Scale a win streak into a larger dungeon that still fits the display."""
    global GRID_SIZE, TILE_SIZE, WALL_COUNT, EXTRA_WALLS, WIDTH, HEIGHT

    # Use the desktop resolution, not the active game window. The latter can
    # report the previous, smaller window and incorrectly shrink a new run.
    try:
        desktop_sizes = pygame.display.get_desktop_sizes()
    except pygame.error:
        # The browser server has no SDL display. Use a conservative desktop
        # viewport so its streak scaling follows the same grid-size rule.
        desktop_sizes = [(1_280, 800)]
    if desktop_sizes:
        desktop_width, desktop_height = desktop_sizes[0]
    else:
        display = pygame.display.Info()
        desktop_width, desktop_height = display.current_w, display.current_h
    max_width = max(1, desktop_width - 80)
    max_height = max(1, desktop_height - HUD_HEIGHT - MENU_HEIGHT - 120)
    # The active streak controls difficulty. A dragon win clears it and
    # restores the default grid, while the all-time high remains recorded.
    requested_size = min(MAX_GRID_SIZE, 8 + statistics.win_streak)
    grid_size = (
        min(requested_size, max_grid_size)
        if max_grid_size is not None
        else requested_size
    )
    while (
        grid_size > 8
        and min(max_width // grid_size, max_height // grid_size) < MIN_TILE_SIZE
    ):
        grid_size -= 1
    TILE_SIZE = min(56, max_width // grid_size, max_height // grid_size)
    GRID_SIZE = grid_size
    WIDTH = GRID_SIZE * TILE_SIZE
    HEIGHT = GRID_SIZE * TILE_SIZE + HUD_HEIGHT + MENU_HEIGHT
    # Each extra row adds walls while preserving the original light density.
    WALL_COUNT = 12 + (GRID_SIZE - 8) * 3
    # Web dungeons stop growing at a readable 13×13. Levels 7–9 ramp up by
    # three barriers per level; every later level adds one more barrier set.
    if max_grid_size is None:
        EXTRA_WALLS = 0
    else:
        level = min(MAX_WEB_LEVEL, statistics.win_streak + 1)
        EXTRA_WALLS = 3 * max(0, min(level, 9) - 6) + max(0, level - 9)


def browser_difficulty(statistics: Statistics) -> tuple[int, int, int]:
    """Return isolated web-session settings without mutating desktop globals."""
    level = statistics.win_streak + 1
    grid_size = min(13, 8 + statistics.win_streak)
    wall_count = 12 + (grid_size - 8) * 3
    fortified_level = min(MAX_WEB_LEVEL, level)
    extra_walls = 3 * max(0, min(fortified_level, 9) - 6) + max(
        0, fortified_level - 9
    )
    return grid_size, wall_count, extra_walls


def make_sound(
    notes: list[tuple[float, float]], volume: float = 0.28
) -> pygame.mixer.Sound | None:
    """Build a short, dependency-free mono sound effect from sine-wave notes."""
    if not pygame.mixer.get_init():
        return None
    samples = array("h")
    for frequency, duration in notes:
        length = int(AUDIO_RATE * duration)
        for index in range(length):
            envelope = min(1.0, index / max(1, AUDIO_RATE // 100))
            envelope *= min(1.0, (length - index) / max(1, AUDIO_RATE // 60))
            sample = math.sin(2 * math.pi * frequency * index / AUDIO_RATE)
            samples.append(int(32_767 * volume * envelope * sample))
    return pygame.mixer.Sound(buffer=samples.tobytes())


def create_sounds() -> dict[str, pygame.mixer.Sound]:
    """Create the small set of sounds used by the game after Pygame starts."""
    recipes = {
        "step": ([(180, 0.045)], 0.16),
        "bump": ([(90, 0.11)], 0.24),
        "treasure": ([(659, 0.08), (784, 0.09), (1_047, 0.16)], 0.26),
        "growl": ([(150, 0.13), (105, 0.17), (78, 0.18)], 0.30),
        "win": ([(523, 0.10), (659, 0.10), (784, 0.18)], 0.28),
        "lose": ([(220, 0.12), (165, 0.14), (110, 0.24)], 0.28),
    }
    return {
        name: sound
        for name, (notes, volume) in recipes.items()
        if (sound := make_sound(notes, volume)) is not None
    }


def play_sound(name: str) -> None:
    sound = SOUNDS.get(name)
    if sound:
        sound.play()


def eat_player(
    state: GameState,
    statistics: Statistics | None = None,
    *,
    persist_statistics: bool = True,
) -> None:
    """End the run with matching sound and screen-shake feedback."""
    record_result(state, statistics, "eaten", persist=persist_statistics)
    state.shake_until = pygame.time.get_ticks() + 450
    play_sound("lose")


def edge_blocked(state: GameState, pos: Position, delta: Position) -> bool:
    x, y = pos
    dx, dy = delta
    if dx == 1:
        return (x, y) in state.vertical_walls
    if dx == -1:
        return (x - 1, y) in state.vertical_walls
    if dy == 1:
        return (x, y) in state.horizontal_walls
    if dy == -1:
        return (x, y - 1) in state.horizontal_walls
    return False


def neighbours(state: GameState, pos: Position, diagonals: bool = False):
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diagonals:
        directions += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    x, y = pos
    for dx, dy in directions:
        nxt = (x + dx, y + dy)
        if not (0 <= nxt[0] < state.grid_size and 0 <= nxt[1] < state.grid_size):
            continue
        if dx and dy:
            horizontal_first = not edge_blocked(
                state, pos, (dx, 0)
            ) and not edge_blocked(state, (x + dx, y), (0, dy))
            vertical_first = not edge_blocked(state, pos, (0, dy)) and not edge_blocked(
                state, (x, y + dy), (dx, 0)
            )
            # A wall on either side of the corner prevents a diagonal shortcut.
            if not (horizontal_first and vertical_first):
                continue
        elif edge_blocked(state, pos, (dx, dy)):
            continue
        yield nxt


def reachable(state: GameState, start: Position, goal: Position) -> bool:
    queue = deque([start])
    seen = {start}
    while queue:
        current = queue.popleft()
        if current == goal:
            return True
        for nxt in neighbours(state, current):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False


def make_game(
    hard_mode: bool = False,
    level: int = 1,
    *,
    grid_size: int | None = None,
    wall_count: int | None = None,
    extra_walls: int | None = None,
) -> GameState:
    """Generate a map whose treasure is reachable from the entrance."""
    while True:
        active_grid_size = GRID_SIZE if grid_size is None else grid_size
        active_wall_count = WALL_COUNT if wall_count is None else wall_count
        active_extra_walls = EXTRA_WALLS if extra_walls is None else extra_walls
        state = GameState(
            grid_size=active_grid_size,
            wall_count=active_wall_count,
            extra_walls=active_extra_walls,
            hard_mode=hard_mode,
            level=level,
        )
        state.visited.add(state.start)
        state.horizontal_walls = {
            (random.randrange(state.grid_size), random.randrange(state.grid_size - 1))
            for _ in range(state.wall_count)
        }
        state.vertical_walls = {
            (random.randrange(state.grid_size - 1), random.randrange(state.grid_size))
            for _ in range(state.wall_count)
        }
        for _ in range(state.extra_walls):
            horizontal_options = [
                (x, y)
                for x in range(state.grid_size)
                for y in range(state.grid_size - 1)
                if (x, y) not in state.horizontal_walls
            ]
            vertical_options = [
                (x, y)
                for x in range(state.grid_size - 1)
                for y in range(state.grid_size)
                if (x, y) not in state.vertical_walls
            ]
            if horizontal_options:
                state.horizontal_walls.add(random.choice(horizontal_options))
            if vertical_options:
                state.vertical_walls.add(random.choice(vertical_options))
        candidates = [
            (x, y)
            for x in range(state.grid_size)
            for y in range(state.grid_size)
            if max(x, y) >= state.grid_size // 2
        ]
        state.treasure = random.choice(candidates)
        dragon_candidates = [
            p
            for p in candidates
            if p != state.treasure
            and max(abs(p[0] - state.treasure[0]), abs(p[1] - state.treasure[1])) >= 2
        ]
        state.dragon = random.choice(dragon_candidates)
        # Every generated dungeon keeps the portal, treasure, and dragon in
        # one connected area. The player always has a route home, and the
        # dragon can always hunt the player after it wakes.
        if reachable(state, state.start, state.treasure) and reachable(
            state, state.dragon, state.start
        ):
            return state


def reveal_wall(state: GameState, pos: Position, delta: Position) -> None:
    x, y = pos
    dx, dy = delta
    if dx == 1:
        state.discovered_v.add((x, y))
    elif dx == -1:
        state.discovered_v.add((x - 1, y))
    elif dy == 1:
        state.discovered_h.add((x, y))
    else:
        state.discovered_h.add((x, y - 1))


def dragon_neighbours(state: GameState, pos: Position):
    """Yield moves allowed by the walls the dragon has encountered so far."""
    known_map = GameState(
        horizontal_walls=state.dragon_discovered_h,
        vertical_walls=state.dragon_discovered_v,
    )
    yield from neighbours(known_map, pos, diagonals=True)


def reveal_wall_to_dragon(state: GameState, pos: Position, delta: Position) -> None:
    """Remember every wall blocking a dragon move without revealing it to the player."""
    x, y = pos
    dx, dy = delta
    checks = (
        [(pos, delta)]
        if not (dx and dy)
        else [
            (pos, (dx, 0)),
            ((x + dx, y), (0, dy)),
            (pos, (0, dy)),
            ((x, y + dy), (dx, 0)),
        ]
    )
    for check_pos, check_delta in checks:
        if not edge_blocked(state, check_pos, check_delta):
            continue
        cx, cy = check_pos
        cdx, cdy = check_delta
        if cdx == 1:
            state.dragon_discovered_v.add((cx, cy))
        elif cdx == -1:
            state.dragon_discovered_v.add((cx - 1, cy))
        elif cdy == 1:
            state.dragon_discovered_h.add((cx, cy))
        else:
            state.dragon_discovered_h.add((cx, cy - 1))


def dragon_path(state: GameState) -> list[Position]:
    """Use A* with only the walls the dragon has encountered so far."""
    return astar_path(
        state.dragon,
        state.player,
        lambda pos: dragon_neighbours(state, pos),
        state.grid_size,
    )


def hard_dragon_path(state: GameState) -> list[Position]:
    """Use A* and the complete wall layout to hunt efficiently in hard mode."""
    return astar_path(
        state.dragon,
        state.player,
        lambda pos: neighbours(state, pos, diagonals=True),
        state.grid_size,
    )


def dragon_step(state: GameState) -> None:
    if state.hard_mode:
        path = hard_dragon_path(state)
        if path:
            state.dragon = path[0]
            state.scorched.add(state.dragon)
        return
    while path := dragon_path(state):
        target = path[0]
        delta = (target[0] - state.dragon[0], target[1] - state.dragon[1])
        if target not in neighbours(state, state.dragon, diagonals=True):
            reveal_wall_to_dragon(state, state.dragon, delta)
            continue
        state.dragon = target
        state.scorched.add(state.dragon)
        return


def attempt_move(
    state: GameState,
    delta: Position,
    statistics: Statistics | None = None,
    *,
    persist_statistics: bool = True,
) -> None:
    if state.status != "playing":
        return
    x, y = state.player
    dx, dy = delta
    target = (x + dx, y + dy)
    if not (0 <= target[0] < state.grid_size and 0 <= target[1] < state.grid_size):
        play_sound("bump")
        state.flash, state.flash_color = "The dungeon ends here.", MUTED
        state.flash_until = pygame.time.get_ticks() + 700
        return
    if edge_blocked(state, state.player, delta):
        play_sound("bump")
        reveal_wall(state, state.player, delta)
        state.flash, state.flash_color = "A hidden wall!", RED
        state.flash_until = pygame.time.get_ticks() + 700
        return

    state.player = target
    state.visited.add(state.player)
    state.moves += 1
    play_sound("step")
    if state.player == state.treasure and not state.has_treasure:
        state.has_treasure = True
        play_sound("treasure")
        state.flash, state.flash_color = (
            "Treasure claimed—get back to the portal!",
            GOLD,
        )
        state.flash_until = pygame.time.get_ticks() + 1600
        state.treasure_open_until = pygame.time.get_ticks() + 700
    if state.player == state.start:
        if state.has_treasure:
            record_result(state, statistics, "won", persist=persist_statistics)
            play_sound("win")
            return
        if state.dragon_awake:
            record_result(state, statistics, "escaped", persist=persist_statistics)
            return
    # The portal resolves first: reaching it safely ends the run even if the
    # dragon is occupying that same tile.
    if state.player == state.dragon:
        eat_player(state, statistics, persist_statistics=persist_statistics)
        return

    distance = max(
        abs(state.player[0] - state.dragon[0]), abs(state.player[1] - state.dragon[1])
    )
    if not state.dragon_awake and distance <= WAKE_DISTANCE:
        state.dragon_awake = True
        state.scorched.add(state.dragon)
        play_sound("growl")
        state.flash, state.flash_color = "THE DRAGON AWAKENS!", RED
        state.flash_until = pygame.time.get_ticks() + 1300
        return  # A fair warning turn.
    if state.dragon_awake:
        dragon_step(state)
        if state.dragon == state.player:
            eat_player(state, statistics, persist_statistics=persist_statistics)


def cell_center(pos: Position) -> Position:
    return (
        pos[0] * TILE_SIZE + TILE_SIZE // 2,
        HUD_HEIGHT + pos[1] * TILE_SIZE + TILE_SIZE // 2,
    )
