from backend import game
from backend.rendering import main_menu_button_rect, mode_button_rects, style_button_rects


def test_mode_buttons_are_separate_and_inside_window():
    buttons = mode_button_rects(game)

    assert set(buttons) == {"normal", "hard"}
    assert not buttons["normal"].colliderect(buttons["hard"])
    for button in buttons.values():
        assert 0 <= button.left < button.right <= game.WIDTH
        assert 0 <= button.top < button.bottom <= game.HEIGHT


def test_main_menu_button_sits_below_dungeon():
    button = main_menu_button_rect(game)
    dungeon_bottom = game.HUD_HEIGHT + game.GRID_SIZE * game.TILE_SIZE

    assert button.top >= dungeon_bottom
    assert button.bottom <= game.HEIGHT


def test_style_buttons_are_separate_and_inside_window():
    buttons = style_button_rects(game)

    assert set(buttons) == {"classic", "illustrated"}
    assert not buttons["classic"].colliderect(buttons["illustrated"])
    for button in buttons.values():
        assert 0 <= button.left < button.right <= game.WIDTH
        assert 0 <= button.top < button.bottom <= game.HEIGHT
