import game


def test_dragon_bump_does_not_consume_its_move(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 4)
    state = game.GameState(player=(2, 1), dragon=(0, 1))
    state.vertical_walls.add((0, 1))

    game.dragon_step(state)

    assert state.dragon != (0, 1)
    assert (0, 1) in state.dragon_discovered_v
    assert (0, 1) not in state.discovered_v


def test_dragon_moves_only_one_tile_after_rerouting(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 4)
    state = game.GameState(player=(2, 1), dragon=(0, 1))
    state.vertical_walls.add((0, 1))

    game.dragon_step(state)

    assert state.dragon in {(0, 0), (0, 2), (1, 0), (1, 2)}


def test_dragon_path_does_not_use_known_wall(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 4)
    state = game.GameState(player=(2, 1), dragon=(0, 1))
    state.vertical_walls.add((0, 1))
    state.dragon_discovered_v.add((0, 1))

    path = game.dragon_path(state)

    assert path
    assert path[0] != (1, 1)


def test_normal_dragon_astar_prefers_the_more_direct_shortest_step(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    state = game.GameState(player=(4, 1), dragon=(5, 5))

    game.dragon_step(state)

    assert state.dragon == (4, 4)


def test_hard_dragon_uses_real_walls_without_bumping(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 4)
    state = game.GameState(player=(2, 1), dragon=(0, 1), hard_mode=True)
    state.vertical_walls.add((0, 1))

    game.dragon_step(state)

    assert state.dragon != (0, 1)
    assert state.dragon != (1, 1)
    assert not state.dragon_discovered_v


def test_hard_dragon_prefers_the_more_direct_shortest_step(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    state = game.GameState(player=(4, 1), dragon=(5, 5), hard_mode=True)

    game.dragon_step(state)

    assert state.dragon == (4, 4)
