"""Launch Dungeon Escape.

Find the treasure, evade the sleeping dragon, and return to the blue portal.
Controls: arrow keys/WASD or swipe. Press R to restart and Esc to quit.
"""

import argparse
import asyncio
from copy import deepcopy

import pygame

import game
from asset_manager import ArtStyle, AssetManager
from rendering import (
    draw_game,
    draw_start_menu,
    main_menu_button_rect,
    mode_button_rects,
    style_button_rects,
)


def set_window_icon() -> None:
    """Use the bundled Dungeon Escape artwork for development windows."""
    try:
        icon = pygame.image.load(
            str(game.resource_path("assets/dungeon_escape_icon.png"))
        )
        pygame.display.set_icon(icon)
    except pygame.error:
        # The game remains playable if an optional image asset is unavailable.
        pass


def make_phantom(state: game.GameState) -> game.GameState:
    """Create the opposite-mode dragon used for debug comparisons."""
    phantom = deepcopy(state)
    phantom.hard_mode = not state.hard_mode
    phantom.dragon_discovered_h.clear()
    phantom.dragon_discovered_v.clear()
    return phantom


def advance_phantom(phantom: game.GameState, player: game.Position) -> None:
    """Advance a comparison dragon after the real player successfully moves."""
    phantom.player = player
    distance = max(
        abs(phantom.player[0] - phantom.dragon[0]),
        abs(phantom.player[1] - phantom.dragon[1]),
    )
    if not phantom.dragon_awake and distance <= game.WAKE_DISTANCE:
        phantom.dragon_awake = True
        phantom.scorched.add(phantom.dragon)
        return
    if phantom.dragon_awake:
        game.dragon_step(phantom)


async def main(debug: bool = False) -> None:
    pygame.mixer.pre_init(game.AUDIO_RATE, -16, 1, 512)
    pygame.init()
    try:
        game.SOUNDS = game.create_sounds()
    except pygame.error:
        game.SOUNDS = {}

    statistics = game.load_statistics()
    game.configure_difficulty(statistics)
    set_window_icon()
    screen = pygame.display.set_mode((game.WIDTH, game.HEIGHT))
    pygame.display.set_caption("Dungeon Escape")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("consolas", 24, bold=True)
    body_font = pygame.font.SysFont("consolas", 17)
    assets = AssetManager(game.resource_path)
    state: game.GameState | None = None
    phantom: game.GameState | None = None
    hard_mode = False
    art_style = ArtStyle.ILLUSTRATED
    touch_start: game.Position | None = None
    pressed_button: str | None = None
    key_moves = {
        pygame.K_LEFT: (-1, 0),
        pygame.K_a: (-1, 0),
        pygame.K_RIGHT: (1, 0),
        pygame.K_d: (1, 0),
        pygame.K_UP: (0, -1),
        pygame.K_w: (0, -1),
        pygame.K_DOWN: (0, 1),
        pygame.K_s: (0, 1),
    }

    def start_game(selected_hard_mode: bool) -> game.GameState:
        nonlocal screen, hard_mode
        hard_mode = selected_hard_mode
        game.configure_difficulty(statistics)
        screen = pygame.display.set_mode((game.WIDTH, game.HEIGHT))
        pygame.display.set_caption(
            "Dungeon Escape — Hard" if hard_mode else "Dungeon Escape"
        )
        return game.make_game(hard_mode=hard_mode)

    def move_player(delta: game.Position) -> None:
        if state is None:
            return
        previous_player = state.player
        game.attempt_move(state, delta, statistics)
        if phantom is not None and state.player != previous_player:
            advance_phantom(phantom, state.player)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif (
                    event.key == pygame.K_r
                    and state is not None
                    and state.status != "playing"
                ):
                    state = start_game(hard_mode)
                    phantom = make_phantom(state) if debug else None
                elif state is not None and event.key in key_moves:
                    move_player(key_moves[event.key])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state is None:
                    pressed_button = next(
                        (
                            f"style:{style}"
                            for style, rect in style_button_rects(game).items()
                            if rect.collidepoint(event.pos)
                        ),
                        None,
                    )
                    if pressed_button is None:
                        pressed_button = next(
                            (
                                mode
                                for mode, rect in mode_button_rects(game).items()
                                if rect.collidepoint(event.pos)
                            ),
                            None,
                        )
                elif main_menu_button_rect(game).collidepoint(event.pos):
                    pressed_button = "main_menu"
                else:
                    touch_start = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if (
                    state is None
                    and pressed_button is not None
                    and pressed_button.startswith("style:")
                ):
                    style_name = pressed_button.removeprefix("style:")
                    button = style_button_rects(game).get(style_name)
                    if button is not None and button.collidepoint(event.pos):
                        art_style = ArtStyle(style_name)
                elif state is None and pressed_button in mode_button_rects(game):
                    button = mode_button_rects(game)[pressed_button]
                    if button.collidepoint(event.pos):
                        state = start_game(selected_hard_mode=pressed_button == "hard")
                        phantom = make_phantom(state) if debug else None
                elif pressed_button == "main_menu" and main_menu_button_rect(
                    game
                ).collidepoint(event.pos):
                    state = None
                    phantom = None
                    hard_mode = False
                    art_style = ArtStyle.ILLUSTRATED
                    pygame.display.set_caption("Dungeon Escape")
                elif touch_start is not None and state is not None:
                    dx = event.pos[0] - touch_start[0]
                    dy = event.pos[1] - touch_start[1]
                    if max(abs(dx), abs(dy)) >= game.SWIPE_THRESHOLD:
                        delta = (
                            ((1 if dx > 0 else -1), 0)
                            if abs(dx) > abs(dy)
                            else (0, (1 if dy > 0 else -1))
                        )
                        move_player(delta)
                    elif state.status != "playing":
                        state = start_game(hard_mode)
                        phantom = make_phantom(state) if debug else None
                touch_start = None
                pressed_button = None

        if state is None:
            draw_start_menu(
                screen,
                title_font,
                body_font,
                statistics,
                game,
                art_style=art_style,
                pressed_button=pressed_button,
            )
        else:
            draw_game(
                screen,
                state,
                title_font,
                body_font,
                statistics,
                game=game,
                cell_center=game.cell_center,
                assets=assets,
                art_style=art_style,
                phantom_state=phantom,
                pressed_button=pressed_button,
                debug=debug,
            )
        pygame.display.flip()
        clock.tick(game.FPS)
        # Browser builds must yield to the WebAssembly event loop each frame.
        await asyncio.sleep(0)

    pygame.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="show the full dungeon while playing",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(main(debug=arguments.debug))
