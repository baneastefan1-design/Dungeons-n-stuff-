from backend import game


def test_dragon_capture_spends_a_heart_and_keeps_the_level() -> None:
    statistics = game.Statistics(win_streak=4, hearts=2)
    state = game.GameState()

    game.eat_player(state, statistics, persist_statistics=False)

    assert state.status == "escaped"
    assert state.life_spent
    assert statistics.hearts == 1
    assert statistics.win_streak == 4
    assert statistics.escapes == 1


def test_true_defeat_refills_hearts_for_level_one() -> None:
    statistics = game.Statistics(win_streak=4, hearts=0)
    state = game.GameState()

    game.eat_player(state, statistics, persist_statistics=False)

    assert state.status == "eaten"
    assert statistics.hearts == 3
    assert statistics.win_streak == 0
    assert statistics.dragon_wins == 1


def test_heart_is_banked_only_after_returning_to_the_portal() -> None:
    statistics = game.Statistics(hearts=1)
    state = game.GameState(
        player=(1, 0),
        start=(0, 0),
        treasure=(4, 4),
        dragon=(7, 7),
        dragon_awake=True,
        has_heart=True,
    )

    game.attempt_move(state, (-1, 0), statistics, persist_statistics=False)

    assert state.status == "escaped"
    assert state.heart_banked
    assert statistics.hearts == 2


def test_spawned_heart_sits_on_the_dragon_wake_boundary(monkeypatch) -> None:
    monkeypatch.setattr(game.random, "random", lambda: 0.0)

    state = game.make_game(hearts=2)

    assert state.heart is not None
    assert max(
        abs(state.heart[0] - state.dragon[0]),
        abs(state.heart[1] - state.dragon[1]),
    ) == game.WAKE_DISTANCE
