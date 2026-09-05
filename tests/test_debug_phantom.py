from backend import dungeon_improved as app
from backend import game


def test_phantom_uses_the_opposite_difficulty():
    normal = game.GameState(hard_mode=False)
    hard = game.GameState(hard_mode=True)

    assert app.make_phantom(normal).hard_mode is True
    assert app.make_phantom(hard).hard_mode is False


def test_advancing_phantom_does_not_move_real_dragon(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 8)
    real = game.GameState(player=(4, 1), dragon=(5, 5))
    phantom = app.make_phantom(real)
    phantom.dragon_awake = True

    app.advance_phantom(phantom, real.player)

    assert phantom.dragon == (4, 4)
    assert real.dragon == (5, 5)
