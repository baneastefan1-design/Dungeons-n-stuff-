"""Treasure wake-up rules shared by the desktop and browser games."""

from backend import game


def open_dungeon(level: int = 1) -> game.GameState:
    return game.GameState(
        grid_size=8,
        player=(2, 0),
        start=(0, 0),
        treasure=(3, 0),
        dragon=(7, 7),
        level=level,
        wake_distance=game.TREASURE_WAKE_DISTANCE,
        treasure_wake_enabled=True,
    )


def test_level_one_treasure_does_not_start_a_wake_countdown() -> None:
    state = open_dungeon()

    game.attempt_move(state, (1, 0), persist_statistics=False)

    assert state.has_treasure
    assert state.treasure_wake_moves_remaining is None
    assert not state.dragon_awake


def test_treasure_countdown_wakes_dragon_after_its_dynamic_move_budget() -> None:
    state = open_dungeon(level=6)
    game.attempt_move(state, (1, 0), persist_statistics=False)

    game.attempt_move(state, (-1, 0), persist_statistics=False)

    assert state.treasure_wake_moves_remaining == 1
    assert not state.dragon_awake

    game.attempt_move(state, (-1, 0), persist_statistics=False)

    assert state.dragon_awake
    assert state.treasure_wake_moves_remaining is None


def test_dynamic_timer_has_a_one_move_minimum() -> None:
    state = open_dungeon(level=2)

    assert game.treasure_wake_moves(state) == 1

    game.attempt_move(state, (1, 0), persist_statistics=False)

    assert state.treasure_wake_moves_remaining == 2


def test_dynamic_timer_gives_more_time_when_the_dragon_is_nearby() -> None:
    state = game.GameState(
        grid_size=13,
        player=(12, 0),
        start=(0, 0),
        dragon=(12, 2),
        level=2,
    )

    assert game.treasure_wake_moves(state) == 8


def test_dynamic_timer_has_a_twelve_move_maximum() -> None:
    state = game.GameState(
        grid_size=30,
        player=(29, 0),
        start=(0, 0),
        dragon=(29, 1),
        level=2,
    )

    assert game.treasure_wake_moves(state) == 12


def test_countdown_can_be_disabled_for_a_game_mode() -> None:
    state = open_dungeon()
    state.treasure_wake_enabled = False

    game.attempt_move(state, (1, 0), persist_statistics=False)

    assert state.treasure_wake_moves_remaining is None


def test_heart_keeps_the_three_tile_wake_boundary() -> None:
    state = game.GameState(
        player=(0, 0), start=(0, 0), heart=(1, 0), dragon=(4, 0),
        wake_distance=game.TREASURE_WAKE_DISTANCE,
    )

    game.attempt_move(state, (1, 0), persist_statistics=False)

    assert state.has_heart
    assert state.dragon_awake
