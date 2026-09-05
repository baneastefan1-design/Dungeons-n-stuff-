import game


def test_browser_progression_fortifies_after_the_13_by_13_cap(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "TILE_SIZE", 56)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 0)

    game.configure_difficulty(game.Statistics(win_streak=7), max_grid_size=13)

    assert game.GRID_SIZE == 13
    assert game.EXTRA_WALLS == 6


def test_browser_fortification_keeps_growing_after_level_nine(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "TILE_SIZE", 56)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 0)

    game.configure_difficulty(game.Statistics(win_streak=9), max_grid_size=13)

    assert game.GRID_SIZE == 13
    assert game.EXTRA_WALLS == 10


def test_fortified_dungeon_keeps_dragon_and_treasure_reachable(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 18)

    state = game.make_game()

    assert game.reachable(state, state.start, state.treasure)
    assert game.reachable(state, state.dragon, state.start)


def test_desktop_progression_has_no_browser_fortification(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "TILE_SIZE", 56)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 0)

    game.configure_difficulty(game.Statistics(win_streak=0))

    assert game.EXTRA_WALLS == 0
