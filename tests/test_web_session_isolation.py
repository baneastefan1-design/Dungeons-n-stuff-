from backend import game


def test_state_grid_size_isolated_from_other_dungeons(monkeypatch):
    small_dungeon = game.GameState(grid_size=8, player=(7, 4))
    large_dungeon = game.GameState(grid_size=13, player=(7, 4))
    monkeypatch.setattr(game, "GRID_SIZE", 4)

    assert (8, 4) not in set(game.neighbours(small_dungeon, small_dungeon.player))
    assert (8, 4) in set(game.neighbours(large_dungeon, large_dungeon.player))


def test_browser_dungeon_settings_do_not_mutate_desktop_globals(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    monkeypatch.setattr(game, "WALL_COUNT", 12)
    monkeypatch.setattr(game, "EXTRA_WALLS", 0)

    small = game.browser_difficulty(game.Statistics(win_streak=0))
    large = game.browser_difficulty(game.Statistics(win_streak=10))

    assert small == (8, 12, 0)
    assert large[0] == 13
    assert large[2] == 11
    assert (game.GRID_SIZE, game.WALL_COUNT, game.EXTRA_WALLS) == (8, 12, 0)
