import game


def test_portal_wins_when_dragon_is_already_on_the_portal(monkeypatch):
    monkeypatch.setattr(game, "GRID_SIZE", 4)
    state = game.GameState(
        player=(1, 0),
        start=(0, 0),
        dragon=(0, 0),
        has_treasure=True,
    )

    game.attempt_move(state, (-1, 0))

    assert state.status == "won"
