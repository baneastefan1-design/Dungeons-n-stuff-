"""Pygame rendering for Dungeon Escape."""

from typing import Any, Callable

import pygame

from asset_manager import ArtStyle, AssetManager


_START_ART: dict[tuple[int, int], pygame.Surface | None] = {}


def start_art(game: Any) -> pygame.Surface | None:
    """Load and crop the title art once for the current window size."""
    size = (game.WIDTH, game.HEIGHT)
    if size in _START_ART:
        return _START_ART[size]
    try:
        source = pygame.image.load(game.resource_path("assets/start_screen.png")).convert()
    except (FileNotFoundError, pygame.error):
        _START_ART[size] = None
        return None
    scale = max(game.WIDTH / source.get_width(), game.HEIGHT / source.get_height())
    scaled_size = (round(source.get_width() * scale), round(source.get_height() * scale))
    scaled = pygame.transform.smoothscale(source, scaled_size)
    crop = pygame.Rect(
        (scaled.get_width() - game.WIDTH) // 2,
        (scaled.get_height() - game.HEIGHT) // 2,
        game.WIDTH,
        game.HEIGHT,
    )
    _START_ART[size] = scaled.subsurface(crop).copy()
    return _START_ART[size]


def main_menu_button_rect(game: Any) -> pygame.Rect:
    """Return the in-game button area in the footer below the dungeon."""
    width, height = 148, 34
    top = game.HUD_HEIGHT + game.GRID_SIZE * game.TILE_SIZE + 10
    return pygame.Rect((game.WIDTH - width) // 2, top, width, height)


def mode_button_rects(game: Any) -> dict[str, pygame.Rect]:
    """Return start-menu hit areas for normal and hard mode."""
    button_width = min(170, (game.WIDTH - 42) // 2)
    gap = 14
    total_width = button_width * 2 + gap
    left = (game.WIDTH - total_width) // 2
    top = game.HEIGHT // 2 + 55
    return {
        "normal": pygame.Rect(left, top, button_width, 54),
        "hard": pygame.Rect(left + button_width + gap, top, button_width, 54),
    }


def style_button_rects(game: Any) -> dict[str, pygame.Rect]:
    """Return start-menu hit areas for the two visual themes."""
    button_width = min(142, (game.WIDTH - 42) // 2)
    gap = 14
    total_width = button_width * 2 + gap
    left = (game.WIDTH - total_width) // 2
    top = game.HEIGHT // 2 + 2
    return {
        ArtStyle.CLASSIC.value: pygame.Rect(left, top, button_width, 38),
        ArtStyle.ILLUSTRATED.value: pygame.Rect(left + button_width + gap, top, button_width, 38),
    }


def draw_start_menu(
    screen: pygame.Surface,
    title_font,
    body_font,
    statistics: Any,
    game: Any,
    art_style: ArtStyle = ArtStyle.ILLUSTRATED,
    pressed_button: str | None = None,
) -> None:
    """Draw the mode-selection screen."""
    screen.fill(game.BG)
    if artwork := start_art(game):
        screen.blit(artwork, (0, 0))
        shade = pygame.Surface((game.WIDTH, game.HEIGHT), pygame.SRCALPHA)
        shade.fill((5, 8, 16, 72))
        screen.blit(shade, (0, 0))
    center_x = game.WIDTH // 2
    title_backdrop = pygame.Surface((game.WIDTH - 32, 178), pygame.SRCALPHA)
    title_backdrop.fill((8, 11, 19, 168))
    screen.blit(title_backdrop, (16, game.HEIGHT // 2 - 132))
    title = title_font.render("DUNGEON ESCAPE", True, game.GOLD)
    screen.blit(title, (center_x - title.get_width() // 2, game.HEIGHT // 2 - 115))
    prompt = body_font.render("Choose art style and difficulty", True, game.WHITE)
    screen.blit(prompt, (center_x - prompt.get_width() // 2, game.HEIGHT // 2 - 68))

    mouse_position = pygame.mouse.get_pos()
    for style_name, rect in style_button_rects(game).items():
        selected = style_name == art_style.value
        hovered = rect.collidepoint(mouse_position)
        accent = game.GOLD if selected else game.MUTED
        fill = (18, 23, 35) if pressed_button == f"style:{style_name}" and hovered else (47, 56, 76) if hovered or selected else (27, 33, 48)
        pygame.draw.rect(screen, fill, rect, border_radius=7)
        pygame.draw.rect(screen, accent, rect, 3 if selected or hovered else 1, border_radius=7)
        label = body_font.render(style_name.upper(), True, game.WHITE if selected else game.MUTED)
        screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))

    descriptions = {
        "normal": ("NORMAL", "Learns walls", game.BLUE),
        "hard": ("HARD", "Knows all walls", game.RED),
    }
    for mode, rect in mode_button_rects(game).items():
        heading, detail, color = descriptions[mode]
        hovered = rect.collidepoint(mouse_position)
        fill = (18, 23, 35) if pressed_button == mode and hovered else (39, 47, 65) if hovered else (27, 33, 48)
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, color, rect, 3 if hovered else 2, border_radius=8)
        heading_surface = body_font.render(heading, True, color)
        detail_surface = body_font.render(detail, True, game.MUTED)
        screen.blit(heading_surface, (rect.centerx - heading_surface.get_width() // 2, rect.y + 7))
        screen.blit(detail_surface, (rect.centerx - detail_surface.get_width() // 2, rect.y + 29))

    stats = body_font.render(
        f"Wins {statistics.wins}  Escapes {statistics.escapes}  Best streak {statistics.highest_win_streak}",
        True,
        game.MUTED,
    )
    screen.blit(stats, (center_x - stats.get_width() // 2, game.HEIGHT // 2 + 138))


def draw_discovered_walls(screen: pygame.Surface, state: Any, game: Any, reveal_all: bool = False) -> None:
    """Draw found walls, or the full dungeon layout after a run ends."""
    WALL, HUD_HEIGHT, TILE_SIZE = game.WALL, game.HUD_HEIGHT, game.TILE_SIZE
    horizontal_walls = state.horizontal_walls if reveal_all else state.discovered_h
    vertical_walls = state.vertical_walls if reveal_all else state.discovered_v
    for wx, wy in horizontal_walls:
        py = HUD_HEIGHT + (wy + 1) * TILE_SIZE
        pygame.draw.line(screen, WALL, (wx * TILE_SIZE, py), ((wx + 1) * TILE_SIZE, py), 6)
    for wx, wy in vertical_walls:
        px = (wx + 1) * TILE_SIZE
        pygame.draw.line(screen, WALL, (px, HUD_HEIGHT + wy * TILE_SIZE), (px, HUD_HEIGHT + (wy + 1) * TILE_SIZE), 6)


def draw_classic_game(
    screen: pygame.Surface,
    state: Any,
    title_font,
    body_font,
    statistics: Any,
    game: Any,
    cell_center: Callable[[tuple[int, int]], tuple[int, int]],
    phantom_state: Any | None = None,
    pressed_button: str | None = None,
    debug: bool = False,
) -> None:
    GRID_SIZE, TILE_SIZE = game.GRID_SIZE, game.TILE_SIZE
    HUD_HEIGHT, WIDTH, HEIGHT = game.HUD_HEIGHT, game.WIDTH, game.HEIGHT
    VISION_RADIUS, WAKE_DISTANCE = game.VISION_RADIUS, game.WAKE_DISTANCE
    BG, FLOOR_A, FLOOR_B, GRID, HUD_BG = game.BG, game.FLOOR_A, game.FLOOR_B, game.GRID, game.HUD_BG
    WHITE, MUTED, BLUE, GOLD, RED = game.WHITE, game.MUTED, game.BLUE, game.GOLD, game.RED
    ORANGE, GREEN, WALL = game.ORANGE, game.GREEN, game.WALL
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
    if debug or state.dragon_awake or state.status != "playing":
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

    if debug and phantom_state is not None and phantom_state.dragon_awake:
        ghost_x, ghost_y = cell_center(phantom_state.dragon)
        ghost = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        center = TILE_SIZE // 2
        ghost_color = (129, 220, 255, 145) if phantom_state.hard_mode else (190, 145, 255, 145)
        pygame.draw.polygon(
            ghost,
            ghost_color,
            [(center - 4, center), (center - 22, center - 15), (center - 16, center + 10)],
        )
        pygame.draw.polygon(
            ghost,
            ghost_color,
            [(center + 4, center), (center + 22, center - 15), (center + 16, center + 10)],
        )
        pygame.draw.ellipse(ghost, ghost_color, (center - 14, center - 9, 28, 24))
        pygame.draw.circle(ghost, (255, 255, 255, 190), (center - 5, center - 2), 2)
        pygame.draw.circle(ghost, (255, 255, 255, 190), (center + 5, center - 2), 2)
        mode_label = "H" if phantom_state.hard_mode else "N"
        label = body_font.render(mode_label, True, ghost_color[:3])
        ghost.blit(label, (center - label.get_width() // 2, center + 8))
        screen.blit(ghost, (ghost_x - center, ghost_y - center))

    # Keep the space around the explorer visible, but preserve discovered walls.
    player_x, player_y = state.player
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            dragon_tile = state.dragon_awake and (x, y) == state.dragon
            hidden = (x, y) not in state.visited and max(abs(x - player_x), abs(y - player_y)) > VISION_RADIUS
            if not debug and state.status == "playing" and not dragon_tile and hidden:
                pygame.draw.rect(screen, (8, 11, 19), (x * TILE_SIZE, HUD_HEIGHT + y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    draw_discovered_walls(screen, state, game, reveal_all=debug or state.status != "playing")

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

    footer_top = HUD_HEIGHT + GRID_SIZE * TILE_SIZE
    pygame.draw.rect(screen, HUD_BG, (0, footer_top, WIDTH, game.MENU_HEIGHT))
    menu_button = main_menu_button_rect(game)
    menu_hovered = menu_button.collidepoint(pygame.mouse.get_pos())
    menu_fill = (18, 23, 35) if pressed_button == "main_menu" and menu_hovered else (47, 56, 76) if menu_hovered else (31, 38, 55)
    pygame.draw.rect(screen, menu_fill, menu_button, border_radius=7)
    pygame.draw.rect(screen, WHITE if menu_hovered else MUTED, menu_button, 3 if menu_hovered else 2, border_radius=7)
    menu_label = body_font.render("MAIN MENU", True, WHITE)
    screen.blit(
        menu_label,
        (menu_button.centerx - menu_label.get_width() // 2, menu_button.centery - menu_label.get_height() // 2),
    )

    if now < state.shake_until:
        shift = 5 if (now // 45) % 2 else -5
        screen.scroll(shift, 0)
        if shift > 0:
            screen.fill(BG, (0, 0, shift, HEIGHT))
        else:
            screen.fill(BG, (WIDTH + shift, 0, -shift, HEIGHT))


def draw_illustrated_game(
    screen: pygame.Surface,
    state: Any,
    title_font,
    body_font,
    statistics: Any,
    game: Any,
    cell_center: Callable[[tuple[int, int]], tuple[int, int]],
    assets: AssetManager,
    phantom_state: Any | None = None,
    pressed_button: str | None = None,
    debug: bool = False,
) -> None:
    """Draw illustrated assets when present, using Classic for missing pieces."""
    draw_classic_game(
        screen,
        state,
        title_font,
        body_font,
        statistics,
        game,
        cell_center,
        phantom_state=phantom_state,
        pressed_button=pressed_button,
        debug=debug,
    )

    tile_size = game.TILE_SIZE
    grid_bottom = game.HUD_HEIGHT + game.GRID_SIZE * tile_size
    player_x, player_y = state.player

    def tile_hidden(position: tuple[int, int]) -> bool:
        """Return whether fog should completely conceal a cell's contents."""
        x, y = position
        outside_vision = max(abs(x - player_x), abs(y - player_y)) > game.VISION_RADIUS
        return not debug and state.status == "playing" and position not in state.visited and outside_vision

    def blit_at_cell(image: pygame.Surface | None, position: tuple[int, int]) -> None:
        if image is None:
            return
        center_x, center_y = cell_center(position)
        screen.blit(image, (center_x - image.get_width() // 2, center_y - image.get_height() // 2))

    floor_size = (tile_size, tile_size)
    floors = (
        assets.get(ArtStyle.ILLUSTRATED, "tiles/floor_1", floor_size),
        assets.get(ArtStyle.ILLUSTRATED, "tiles/floor_2", floor_size),
    )
    if all(floors):
        for y in range(game.GRID_SIZE):
            for x in range(game.GRID_SIZE):
                screen.blit(floors[(x + y) % 2], (x * tile_size, game.HUD_HEIGHT + y * tile_size))

    scorch = assets.get(ArtStyle.ILLUSTRATED, "scorch", floor_size, fit=True, trim=True)
    for position in state.scorched:
        blit_at_cell(scorch, position)

    portal = assets.get(ArtStyle.ILLUSTRATED, "portal", floor_size, fit=True, trim=True)
    blit_at_cell(portal, state.start)

    if not tile_hidden(state.treasure):
        if not state.has_treasure or pygame.time.get_ticks() < state.treasure_open_until:
            treasure = assets.get(ArtStyle.ILLUSTRATED, "treasure_open", floor_size, fit=True, trim=True)
            blit_at_cell(treasure, state.treasure)
        else:
            treasure_x, treasure_y = cell_center(state.treasure)
            pygame.draw.line(screen, game.RED, (treasure_x - 8, treasure_y - 8), (treasure_x + 8, treasure_y + 8), 4)
            pygame.draw.line(screen, game.RED, (treasure_x + 8, treasure_y - 8), (treasure_x - 8, treasure_y + 8), 4)

    if debug or state.dragon_awake or state.status != "playing":
        dragon_name = "dragon/awake" if state.dragon_awake else "dragon/sleeping"
        dragon = assets.get(ArtStyle.ILLUSTRATED, dragon_name, floor_size, fit=True, trim=True)
        blit_at_cell(dragon, state.dragon)

    if debug and phantom_state is not None and phantom_state.dragon_awake:
        phantom = assets.get(ArtStyle.ILLUSTRATED, "dragon/phantom", floor_size, fit=True, trim=True)
        blit_at_cell(phantom, phantom_state.dragon)

    fog = assets.get(ArtStyle.ILLUSTRATED, "fog", floor_size)
    for y in range(game.GRID_SIZE):
        for x in range(game.GRID_SIZE):
            dragon_tile = state.dragon_awake and (x, y) == state.dragon
            if not dragon_tile and tile_hidden((x, y)):
                if fog is not None:
                    screen.blit(fog, (x * tile_size, game.HUD_HEIGHT + y * tile_size))
                else:
                    pygame.draw.rect(screen, (8, 11, 19), (x * tile_size, game.HUD_HEIGHT + y * tile_size, tile_size, tile_size))

    horizontal_walls = state.horizontal_walls if debug or state.status != "playing" else state.discovered_h
    vertical_walls = state.vertical_walls if debug or state.status != "playing" else state.discovered_v
    wall_thickness = 14
    wall_offset = wall_thickness // 2
    horizontal = assets.get(ArtStyle.ILLUSTRATED, "tiles/wall_horizontal", (tile_size, wall_thickness), trim=True)
    vertical = assets.get(ArtStyle.ILLUSTRATED, "tiles/wall_vertical", (wall_thickness, tile_size), trim=True)
    for wall_x, wall_y in horizontal_walls:
        if horizontal is not None:
            screen.blit(horizontal, (wall_x * tile_size, game.HUD_HEIGHT + (wall_y + 1) * tile_size - wall_offset))
    for wall_x, wall_y in vertical_walls:
        if vertical is not None:
            screen.blit(vertical, ((wall_x + 1) * tile_size - wall_offset, game.HUD_HEIGHT + wall_y * tile_size))

    hero_name = "hero/walk" if state.moves % 2 else "hero/idle"
    hero = assets.get(ArtStyle.ILLUSTRATED, hero_name, floor_size, fit=True, trim=True)
    blit_at_cell(hero, state.player)

    # Keep the footer visually separate from the illustrated dungeon.
    pygame.draw.line(screen, game.GRID, (0, grid_bottom), (game.WIDTH, grid_bottom), 1)


def draw_game(
    screen: pygame.Surface,
    state: Any,
    title_font,
    body_font,
    statistics: Any,
    game: Any,
    cell_center: Callable[[tuple[int, int]], tuple[int, int]],
    assets: AssetManager,
    art_style: ArtStyle = ArtStyle.ILLUSTRATED,
    phantom_state: Any | None = None,
    pressed_button: str | None = None,
    debug: bool = False,
) -> None:
    """Dispatch rendering to the selected visual theme."""
    if art_style is ArtStyle.ILLUSTRATED:
        draw_illustrated_game(
            screen,
            state,
            title_font,
            body_font,
            statistics,
            game,
            cell_center,
            assets,
            phantom_state=phantom_state,
            pressed_button=pressed_button,
            debug=debug,
        )
        return
    draw_classic_game(
        screen,
        state,
        title_font,
        body_font,
        statistics,
        game,
        cell_center,
        phantom_state=phantom_state,
        pressed_button=pressed_button,
        debug=debug,
    )
