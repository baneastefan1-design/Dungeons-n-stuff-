"""A compact, single-file dungeon escape game built with pygame.

Find the treasure, evade the sleeping dragon, and return to the blue portal.
Controls: arrow keys/WASD or swipe. Press R to restart and Esc to quit.
"""

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


GRID_SIZE = 8
TILE_SIZE = 56
HUD_HEIGHT = 72
WIDTH = GRID_SIZE * TILE_SIZE
HEIGHT = GRID_SIZE * TILE_SIZE + HUD_HEIGHT
FPS = 60
WALL_COUNT = 12
MAX_GRID_SIZE = 16
MIN_TILE_SIZE = 42
WAKE_DISTANCE = 3
SWIPE_THRESHOLD = 28
VISION_RADIUS = 2
AUDIO_RATE = 44_100


def statistics_file() -> Path:
    """Choose a writable stats location both in development and in the app."""
    if saved_path := os.environ.get("DUNGEON_STATS_FILE"):
        return Path(saved_path)
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            data_directory = Path.home() / "Library" / "Application Support"
        elif sys.platform == "win32":
            data_directory = Path(os.environ.get("APPDATA", Path.home()))
        else:
            data_directory = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
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
    player: Position = (0, 0)
    start: Position = (0, 0)
    visited: set[Position] = field(default_factory=set)
    treasure: Position = (0, 0)
    dragon: Position = (0, 0)
    horizontal_walls: set[Wall] = field(default_factory=set)
    vertical_walls: set[Wall] = field(default_factory=set)
    discovered_h: set[Wall] = field(default_factory=set)
    discovered_v: set[Wall] = field(default_factory=set)
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
                if saved.get("best_win_moves") is not None else None
            ),
            win_streak=max(0, int(saved.get("win_streak", 0))),
            highest_win_streak=max(0, int(saved.get("highest_win_streak", saved.get("win_streak", 0)))),
        )
    except (OSError, ValueError, TypeError):
        return Statistics()


def save_statistics(statistics: Statistics) -> None:
    """Persist results without making a save failure interrupt the game."""
    try:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(statistics.__dict__, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def record_result(state: GameState, statistics: Statistics | None, status: str) -> None:
    """Record each completed run once, including moves used for treasure wins."""
    state.status = status
    if statistics is None or state.result_recorded:
        return
    state.result_recorded = True
    if status == "won":
        statistics.wins += 1
        statistics.win_streak += 1
        statistics.highest_win_streak = max(statistics.highest_win_streak, statistics.win_streak)
        statistics.total_win_moves += state.moves
        if statistics.best_win_moves is None or state.moves < statistics.best_win_moves:
            statistics.best_win_moves = state.moves
    elif status == "eaten":
        statistics.dragon_wins += 1
        statistics.win_streak = 0
    elif status == "escaped":
        statistics.escapes += 1
    save_statistics(statistics)


def configure_difficulty(statistics: Statistics) -> None:
    """Scale a win streak into a larger dungeon that still fits the display."""
    global GRID_SIZE, TILE_SIZE, WALL_COUNT, WIDTH, HEIGHT
    # Use the desktop resolution, not the active game window. The latter can
    # report the previous, smaller window and incorrectly shrink a new run.
    desktop_sizes = pygame.display.get_desktop_sizes()
    if desktop_sizes:
        desktop_width, desktop_height = desktop_sizes[0]
    else:
        display = pygame.display.Info()
        desktop_width, desktop_height = display.current_w, display.current_h
    max_width = max(1, desktop_width - 80)
    max_height = max(1, desktop_height - HUD_HEIGHT - 120)
    # The active streak controls difficulty. A dragon win clears it and
    # restores the default grid, while the all-time high remains recorded.
    requested_size = min(MAX_GRID_SIZE, 8 + statistics.win_streak)
    grid_size = requested_size
    while grid_size > 8 and min(max_width // grid_size, max_height // grid_size) < MIN_TILE_SIZE:
        grid_size -= 1
    TILE_SIZE = min(56, max_width // grid_size, max_height // grid_size)
    GRID_SIZE = grid_size
    WIDTH = GRID_SIZE * TILE_SIZE
    HEIGHT = GRID_SIZE * TILE_SIZE + HUD_HEIGHT
    # Each extra row adds walls while preserving the original light density.
    WALL_COUNT = 12 + (GRID_SIZE - 8) * 3


def make_sound(notes: list[tuple[float, float]], volume: float = 0.28) -> pygame.mixer.Sound | None:
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


def eat_player(state: GameState, statistics: Statistics | None = None) -> None:
    """End the run with matching sound and screen-shake feedback."""
    record_result(state, statistics, "eaten")
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
        if not (0 <= nxt[0] < GRID_SIZE and 0 <= nxt[1] < GRID_SIZE):
            continue
        if dx and dy:
            horizontal_first = (
                not edge_blocked(state, pos, (dx, 0))
                and not edge_blocked(state, (x + dx, y), (0, dy))
            )
            vertical_first = (
                not edge_blocked(state, pos, (0, dy))
                and not edge_blocked(state, (x, y + dy), (dx, 0))
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


def make_game() -> GameState:
    """Generate a map whose treasure is reachable from the entrance."""
    while True:
        state = GameState()
        state.visited.add(state.start)
        state.horizontal_walls = {
            (random.randrange(GRID_SIZE), random.randrange(GRID_SIZE - 1))
            for _ in range(WALL_COUNT)
        }
        state.vertical_walls = {
            (random.randrange(GRID_SIZE - 1), random.randrange(GRID_SIZE))
            for _ in range(WALL_COUNT)
        }
        candidates = [
            (x, y)
            for x in range(GRID_SIZE)
            for y in range(GRID_SIZE)
            if max(x, y) >= GRID_SIZE // 2
        ]
        state.treasure = random.choice(candidates)
        dragon_candidates = [
            p for p in candidates
            if p != state.treasure and max(abs(p[0] - state.treasure[0]), abs(p[1] - state.treasure[1])) >= 2
        ]
        state.dragon = random.choice(dragon_candidates)
        if reachable(state, state.start, state.treasure):
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


def dragon_step(state: GameState) -> None:
    choices = list(neighbours(state, state.dragon, diagonals=True))
    if not choices:
        return
    px, py = state.player
    random.shuffle(choices)
    state.dragon = min(
        choices,
        key=lambda p: (max(abs(p[0] - px), abs(p[1] - py)), (p[0] - px) ** 2 + (p[1] - py) ** 2),
    )
    state.scorched.add(state.dragon)


def attempt_move(state: GameState, delta: Position, statistics: Statistics | None = None) -> None:
    if state.status != "playing":
        return
    x, y = state.player
    dx, dy = delta
    target = (x + dx, y + dy)
    if not (0 <= target[0] < GRID_SIZE and 0 <= target[1] < GRID_SIZE):
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
    if state.player == state.dragon:
        eat_player(state, statistics)
        return
    if state.player == state.treasure and not state.has_treasure:
        state.has_treasure = True
        play_sound("treasure")
        state.flash, state.flash_color = "Treasure claimed—get back to the portal!", GOLD
        state.flash_until = pygame.time.get_ticks() + 1600
        state.treasure_open_until = pygame.time.get_ticks() + 700
    if state.player == state.start:
        if state.has_treasure:
            record_result(state, statistics, "won")
            play_sound("win")
            return
        if state.dragon_awake:
            record_result(state, statistics, "escaped")
            return

    distance = max(abs(state.player[0] - state.dragon[0]), abs(state.player[1] - state.dragon[1]))
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
            eat_player(state, statistics)


def cell_center(pos: Position) -> Position:
    return (pos[0] * TILE_SIZE + TILE_SIZE // 2, HUD_HEIGHT + pos[1] * TILE_SIZE + TILE_SIZE // 2)


def draw_discovered_walls(screen: pygame.Surface, state: GameState, reveal_all: bool = False) -> None:
    """Draw found walls, or the full dungeon layout after a run ends."""
    horizontal_walls = state.horizontal_walls if reveal_all else state.discovered_h
    vertical_walls = state.vertical_walls if reveal_all else state.discovered_v
    for wx, wy in horizontal_walls:
        py = HUD_HEIGHT + (wy + 1) * TILE_SIZE
        pygame.draw.line(screen, WALL, (wx * TILE_SIZE, py), ((wx + 1) * TILE_SIZE, py), 6)
    for wx, wy in vertical_walls:
        px = (wx + 1) * TILE_SIZE
        pygame.draw.line(screen, WALL, (px, HUD_HEIGHT + wy * TILE_SIZE), (px, HUD_HEIGHT + (wy + 1) * TILE_SIZE), 6)


def draw_game(screen: pygame.Surface, state: GameState, title_font, body_font, statistics: Statistics) -> None:
    now = pygame.time.get_ticks()
    screen.fill(BG)
    pygame.draw.rect(screen, HUD_BG, (0, 0, WIDTH, HUD_HEIGHT))
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            color = FLOOR_A if (x + y) % 2 == 0 else FLOOR_B
            pygame.draw.rect(screen, color, (x * TILE_SIZE, HUD_HEIGHT + y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            pygame.draw.rect(screen, GRID, (x * TILE_SIZE, HUD_HEIGHT + y * TILE_SIZE, TILE_SIZE, TILE_SIZE), 1)

    # The dragon leaves burned stone behind as it starts hunting.
    for scorch_x, scorch_y in state.scorched:
        scorch_rect = (scorch_x * TILE_SIZE + 2, HUD_HEIGHT + scorch_y * TILE_SIZE + 2, TILE_SIZE - 4, TILE_SIZE - 4)
        pygame.draw.rect(screen, (65, 37, 42), scorch_rect, border_radius=5)
        pygame.draw.line(screen, (120, 55, 48), (scorch_rect[0] + 10, scorch_rect[1] + 13), (scorch_rect[0] + 29, scorch_rect[1] + 30), 2)
        pygame.draw.line(screen, (120, 55, 48), (scorch_rect[0] + 35, scorch_rect[1] + 12), (scorch_rect[0] + 25, scorch_rect[1] + 37), 2)

    # Entrance portal.
    cx, cy = cell_center(state.start)
    if state.has_treasure:
        glow_radius = 23 + (now // 120) % 5
        pygame.draw.circle(screen, GOLD, (cx, cy), glow_radius, 2)
        pygame.draw.circle(screen, (157, 112, 45), (cx, cy), glow_radius + 5, 1)
    pygame.draw.circle(screen, BLUE, (cx, cy), 18, 3)
    pygame.draw.circle(screen, (43, 78, 133), (cx, cy), 11, 2)

    if not state.has_treasure:
        tx, ty = cell_center(state.treasure)
        # A wooden chest, with a bright lock and a little glint of treasure.
        pygame.draw.ellipse(screen, (18, 24, 38), (tx - 18, ty + 12, 36, 8))
        pygame.draw.rect(screen, (115, 60, 43), (tx - 16, ty - 2, 32, 17), border_radius=3)
        pygame.draw.polygon(screen, (151, 84, 50), [(tx - 16, ty - 2), (tx - 10, ty - 10), (tx + 10, ty - 10), (tx + 16, ty - 2)])
        pygame.draw.line(screen, GOLD, (tx - 11, ty - 8), (tx - 11, ty + 14), 3)
        pygame.draw.line(screen, GOLD, (tx + 11, ty - 8), (tx + 11, ty + 14), 3)
        pygame.draw.rect(screen, GOLD, (tx - 4, ty + 1, 8, 8), border_radius=2)
        pygame.draw.circle(screen, (255, 239, 164), (tx + 16, ty - 12), 2)
        pygame.draw.line(screen, (255, 239, 164), (tx + 16, ty - 17), (tx + 16, ty - 7), 1)
        pygame.draw.line(screen, (255, 239, 164), (tx + 11, ty - 12), (tx + 21, ty - 12), 1)
    elif now < state.treasure_open_until:
        # Leave a celebratory open chest in place for a moment after pickup.
        tx, ty = cell_center(state.treasure)
        pygame.draw.ellipse(screen, (18, 24, 38), (tx - 18, ty + 12, 36, 8))
        pygame.draw.rect(screen, (115, 60, 43), (tx - 16, ty + 2, 32, 13), border_radius=3)
        pygame.draw.polygon(screen, (151, 84, 50), [(tx - 16, ty + 1), (tx - 10, ty - 5), (tx + 10, ty - 5), (tx + 16, ty + 1)])
        lid_lift = 13 + (now // 80) % 3
        pygame.draw.polygon(screen, (151, 84, 50), [(tx - 16, ty - 4), (tx - 10, ty - lid_lift), (tx + 10, ty - lid_lift), (tx + 16, ty - 4)])
        pygame.draw.rect(screen, GOLD, (tx - 4, ty + 4, 8, 7), border_radius=2)
        pygame.draw.circle(screen, (255, 239, 164), (tx - 9, ty - 16), 2)
        pygame.draw.circle(screen, (255, 239, 164), (tx + 9, ty - 20), 2)
    else:
        # Keep the looted chest location readable after the animation ends.
        tx, ty = cell_center(state.treasure)
        pygame.draw.circle(screen, (30, 22, 29), (tx, ty), 15)
        pygame.draw.line(screen, RED, (tx - 8, ty - 8), (tx + 8, ty + 8), 4)
        pygame.draw.line(screen, RED, (tx + 8, ty - 8), (tx - 8, ty + 8), 4)

    for wx, wy in state.discovered_h:
        py = HUD_HEIGHT + (wy + 1) * TILE_SIZE
        pygame.draw.line(screen, WALL, (wx * TILE_SIZE, py), ((wx + 1) * TILE_SIZE, py), 6)
    for wx, wy in state.discovered_v:
        px = (wx + 1) * TILE_SIZE
        pygame.draw.line(screen, WALL, (px, HUD_HEIGHT + wy * TILE_SIZE), (px, HUD_HEIGHT + (wy + 1) * TILE_SIZE), 6)

    # Reveal the dragon after every completed run. If it was never disturbed,
    # its closed eyes and snore marks make the quiet escape clear.
    if state.dragon_awake or state.status != "playing":
        dx, dy = cell_center(state.dragon)
        # A winged dragon with horns, a tail, claws, and glowing eyes.
        if state.dragon_awake:
            glow_radius = 22 + (pygame.time.get_ticks() // 140) % 5
            pygame.draw.circle(screen, ORANGE, (dx, dy), glow_radius, 2)
        pygame.draw.ellipse(screen, (18, 24, 38), (dx - 23, dy + 14, 46, 9))
        pygame.draw.polygon(screen, (126, 42, 61), [(dx - 5, dy - 4), (dx - 23, dy - 18), (dx - 18, dy + 8), (dx - 5, dy + 12)])
        pygame.draw.polygon(screen, (126, 42, 61), [(dx + 5, dy - 4), (dx + 23, dy - 18), (dx + 18, dy + 8), (dx + 5, dy + 12)])
        pygame.draw.polygon(screen, RED, [(dx - 18, dy + 6), (dx - 28, dy + 12), (dx - 18, dy + 14), (dx - 12, dy + 11)])
        pygame.draw.ellipse(screen, RED, (dx - 15, dy - 5, 30, 22))
        pygame.draw.polygon(screen, (255, 157, 66), [(dx - 7, dy - 5), (dx, dy - 14), (dx + 7, dy - 5)])
        pygame.draw.polygon(screen, RED, [(dx - 11, dy - 7), (dx - 7, dy - 17), (dx - 2, dy - 7)])
        pygame.draw.polygon(screen, RED, [(dx + 2, dy - 7), (dx + 7, dy - 17), (dx + 11, dy - 7)])
        pygame.draw.polygon(screen, RED, [(dx - 10, dy + 1), (dx - 15, dy - 7), (dx + 15, dy - 7), (dx + 10, dy + 1)])
        if state.dragon_awake:
            pygame.draw.circle(screen, GOLD, (dx - 6, dy - 4), 3)
            pygame.draw.circle(screen, GOLD, (dx + 6, dy - 4), 3)
            pygame.draw.circle(screen, (35, 15, 24), (dx - 6, dy - 4), 1)
            pygame.draw.circle(screen, (35, 15, 24), (dx + 6, dy - 4), 1)
        else:
            pygame.draw.line(screen, (35, 15, 24), (dx - 9, dy - 4), (dx - 3, dy - 4), 2)
            pygame.draw.line(screen, (35, 15, 24), (dx + 3, dy - 4), (dx + 9, dy - 4), 2)
            for offset, size in ((0, 13), (10, 10), (18, 8)):
                snore = body_font.render("Z", True, MUTED)
                snore = pygame.transform.smoothscale(snore, (size, size))
                screen.blit(snore, (dx + 9 + offset, dy - 30 - offset))
        pygame.draw.rect(screen, (111, 37, 54), (dx - 12, dy + 13, 8, 6), border_radius=2)
        pygame.draw.rect(screen, (111, 37, 54), (dx + 4, dy + 13, 8, 6), border_radius=2)

    # Keep the space around the explorer visible, but preserve discovered walls.
    player_x, player_y = state.player
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            dragon_tile = state.dragon_awake and (x, y) == state.dragon
            hidden = (x, y) not in state.visited and max(abs(x - player_x), abs(y - player_y)) > VISION_RADIUS
            if state.status == "playing" and not dragon_tile and hidden:
                pygame.draw.rect(screen, (8, 11, 19), (x * TILE_SIZE, HUD_HEIGHT + y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    draw_discovered_walls(screen, state, reveal_all=state.status != "playing")

    # A small dungeon explorer: shadow, boots, cloak, face, and lantern.
    px, py = cell_center(state.player)
    pygame.draw.ellipse(screen, (18, 24, 38), (px - 17, py + 14, 34, 10))
    pygame.draw.rect(screen, (42, 33, 43), (px - 11, py + 11, 8, 9), border_radius=2)
    pygame.draw.rect(screen, (42, 33, 43), (px + 3, py + 11, 8, 9), border_radius=2)
    pygame.draw.polygon(screen, (44, 93, 171), [(px - 13, py + 14), (px - 11, py - 5), (px, py - 9), (px + 12, py - 5), (px + 13, py + 14)])
    pygame.draw.polygon(screen, BLUE, [(px - 10, py + 12), (px - 8, py - 4), (px, py - 7), (px + 9, py - 4), (px + 10, py + 12)])
    pygame.draw.circle(screen, (225, 174, 133), (px - 10, py - 10), 3)
    pygame.draw.circle(screen, (225, 174, 133), (px + 10, py - 10), 3)
    pygame.draw.circle(screen, (244, 196, 153), (px, py - 11), 11)
    pygame.draw.polygon(screen, (95, 54, 42), [
        (px - 10, py - 14), (px - 8, py - 22), (px + 8, py - 22),
        (px + 10, py - 14), (px + 5, py - 17), (px, py - 15), (px - 5, py - 17),
    ])
    pygame.draw.circle(screen, (28, 43, 69), (px - 4, py - 11), 2)
    pygame.draw.circle(screen, (28, 43, 69), (px + 4, py - 11), 2)
    pygame.draw.circle(screen, WHITE, (px - 4, py - 12), 1)
    pygame.draw.circle(screen, WHITE, (px + 4, py - 12), 1)
    pygame.draw.line(screen, (205, 142, 107), (px, py - 9), (px, py - 7), 1)
    pygame.draw.arc(screen, (166, 77, 82), (px - 4, py - 8, 8, 5), 0.15, 2.95, 1)
    pygame.draw.line(screen, (235, 239, 247), (px + 11, py - 2), (px + 16, py + 7), 2)
    pygame.draw.rect(screen, GOLD, (px + 13, py + 5, 7, 8), border_radius=2)
    pygame.draw.circle(screen, (255, 239, 164), (px + 16, py + 9), 2)

    if state.status == "won":
        headline, detail, color = "ESCAPED!", f"Treasure secured in {state.moves} moves · press R", GREEN
    elif state.status == "escaped":
        headline, detail, color = "SAFE FOR NOW", "You escaped through the portal · press R to try again", BLUE
    elif state.status == "eaten":
        headline, detail, color = "DEVOURED", f"The dragon wins · press R to retry", RED
    else:
        headline = f"MOVES {state.moves:03d}"
        if now < state.flash_until:
            detail, color = state.flash, state.flash_color
        elif state.dragon_awake:
            detail, color = "The dragon is hunting you!", ORANGE
        elif state.has_treasure:
            detail, color = "Return to the blue portal.", GOLD
        else:
            distance = max(abs(state.player[0] - state.dragon[0]), abs(state.player[1] - state.dragon[1]))
            detail = "The air feels warm nearby…" if distance <= WAKE_DISTANCE + 1 else "The dungeon is quiet."
            color = ORANGE if distance <= WAKE_DISTANCE + 1 else MUTED
    screen.blit(title_font.render(headline, True, WHITE), (14, 11))
    stats_text = (
        f"W {statistics.wins}  D {statistics.dragon_wins}  E {statistics.escapes}"
        f"  S {statistics.win_streak}  H {statistics.highest_win_streak}"
    )
    stats_surface = body_font.render(stats_text, True, MUTED)
    screen.blit(stats_surface, (WIDTH - stats_surface.get_width() - 14, 16))
    screen.blit(body_font.render(detail, True, color), (14, 40))

    if now < state.shake_until:
        shift = 5 if (now // 45) % 2 else -5
        screen.scroll(shift, 0)
        if shift > 0:
            screen.fill(BG, (0, 0, shift, HEIGHT))
        else:
            screen.fill(BG, (WIDTH + shift, 0, -shift, HEIGHT))


def main() -> None:
    global SOUNDS
    pygame.mixer.pre_init(AUDIO_RATE, -16, 1, 512)
    pygame.init()
    try:
        SOUNDS = create_sounds()
    except pygame.error:
        SOUNDS = {}
    statistics = load_statistics()
    configure_difficulty(statistics)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Dungeon Escape")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("consolas", 24, bold=True)
    body_font = pygame.font.SysFont("consolas", 17)
    state = make_game()
    touch_start: Position | None = None
    key_moves = {
        pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
        pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
        pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
        pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    }

    def restart_game() -> GameState:
        nonlocal screen
        configure_difficulty(statistics)
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        return make_game()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r and state.status != "playing":
                    state = restart_game()
                elif event.key in key_moves:
                    attempt_move(state, key_moves[event.key], statistics)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                touch_start = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and touch_start:
                dx, dy = event.pos[0] - touch_start[0], event.pos[1] - touch_start[1]
                if max(abs(dx), abs(dy)) >= SWIPE_THRESHOLD:
                    attempt_move(state, ((1 if dx > 0 else -1), 0) if abs(dx) > abs(dy) else (0, (1 if dy > 0 else -1)), statistics)
                elif state.status != "playing":
                    state = restart_game()
                touch_start = None

        draw_game(screen, state, title_font, body_font, statistics)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
