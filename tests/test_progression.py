from backend import game


def test_browser_progression_fortifies_after_the_13_by_13_cap(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "TILE_SIZE", 56)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 0)

    game.configure_difficulty(game.Statistics(win_streak=7), max_grid_size=13)

    assert game.GRID_SIZE == 13
    assert game.EXTRA_WALLS == 4


def test_browser_fortification_keeps_growing_after_level_nine(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "TILE_SIZE", 56)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 0)

    game.configure_difficulty(game.Statistics(win_streak=9), max_grid_size=13)

    assert game.GRID_SIZE == 13
    assert game.EXTRA_WALLS == 7


def test_browser_fortification_caps_at_the_load_tested_level(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "TILE_SIZE", 56)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 0)

    game.configure_difficulty(game.Statistics(win_streak=53), max_grid_size=13)
    safe_extra_walls = game.EXTRA_WALLS
    game.configure_difficulty(game.Statistics(win_streak=99), max_grid_size=13)

    assert safe_extra_walls == 10
    assert game.EXTRA_WALLS == safe_extra_walls


def test_fortified_dungeon_keeps_dragon_and_treasure_reachable(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 18)

    state = game.make_game()

    assert game.reachable(state, state.start, state.treasure)
    assert game.reachable(state, state.dragon, state.start)


def test_desktop_progression_uses_the_shared_fortification_curve(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "TILE_SIZE", 56)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 0)

    game.configure_difficulty(game.Statistics(win_streak=7))

    assert game.EXTRA_WALLS == 4
