"""WebSocket adapter for the Dungeon Escape Python game rules."""

from __future__ import annotations

from datetime import date
from copy import deepcopy
from pathlib import Path
import sqlite3
from typing import Any
from uuid import UUID

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import game

ROOT = Path(__file__).parent
DATABASE = ROOT / "data" / "dungeon_escape.sqlite3"
app = FastAPI(title="Dungeon Escape")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


def database() -> sqlite3.Connection:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_database() -> None:
    with database() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS players (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                wins INTEGER NOT NULL DEFAULT 0,
                dragon_wins INTEGER NOT NULL DEFAULT 0,
                escapes INTEGER NOT NULL DEFAULT 0,
                total_win_moves INTEGER NOT NULL DEFAULT 0,
                best_win_moves INTEGER,
                win_streak INTEGER NOT NULL DEFAULT 0,
                highest_win_streak INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS client_profiles (
                client_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                change_day TEXT NOT NULL,
                change_count INTEGER NOT NULL DEFAULT 0
            )
            """)


def player_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned if 1 <= len(cleaned) <= 24 else None


def client_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return str(UUID(value))
    except ValueError:
        return None


def allow_username(username: str, client_id: str) -> bool:
    """Allow the initial name and at most two later name changes per day."""
    today = date.today().isoformat()
    with database() as connection:
        profile = connection.execute(
            "SELECT username, change_day, change_count FROM client_profiles WHERE client_id = ?",
            (client_id,),
        ).fetchone()
        if profile is None:
            connection.execute(
                "INSERT INTO client_profiles (client_id, username, change_day) VALUES (?, ?, ?)",
                (client_id, username, today),
            )
            return True
        if profile["username"].casefold() == username.casefold():
            return True
        changes = profile["change_count"] if profile["change_day"] == today else 0
        if changes >= 2:
            return False
        connection.execute(
            "UPDATE client_profiles SET username = ?, change_day = ?, change_count = ? WHERE client_id = ?",
            (username, today, changes + 1, client_id),
        )
        return True


def load_player(username: str) -> game.Statistics:
    with database() as connection:
        row = connection.execute(
            "SELECT * FROM players WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        return game.Statistics()
    return game.Statistics(
        **{field: row[field] for field in game.Statistics.__dataclass_fields__}
    )


def save_player(username: str, statistics: game.Statistics) -> None:
    values = statistics.__dict__
    with database() as connection:
        connection.execute(
            """
            INSERT INTO players (username, wins, dragon_wins, escapes, total_win_moves, best_win_moves, win_streak, highest_win_streak)
            VALUES (:username, :wins, :dragon_wins, :escapes, :total_win_moves, :best_win_moves, :win_streak, :highest_win_streak)
            ON CONFLICT(username) DO UPDATE SET
                wins = excluded.wins, dragon_wins = excluded.dragon_wins, escapes = excluded.escapes,
                total_win_moves = excluded.total_win_moves, best_win_moves = excluded.best_win_moves,
                win_streak = excluded.win_streak, highest_win_streak = excluded.highest_win_streak,
                updated_at = CURRENT_TIMESTAMP
            """,
            {"username": username, **values},
        )


initialise_database()


def position(value: game.Position) -> list[int]:
    return [value[0], value[1]]


def walls(values: set[game.Wall]) -> list[list[int]]:
    return [list(value) for value in values]


def serialise(
    state: game.GameState,
    statistics: game.Statistics,
    *,
    debug: bool = False,
    phantom: game.GameState | None = None,
) -> dict[str, Any]:
    """Return only rendering data; all decisions remain in game.py."""
    distance = max(
        abs(state.player[0] - state.dragon[0]), abs(state.player[1] - state.dragon[1])
    )
    if state.status == "eaten":
        hint = "DEVOURED · The dragon wins."
    elif state.status == "won":
        hint = "ESCAPED · Treasure secured."
    elif state.status == "escaped":
        hint = "ESCAPED · You reached the portal safely."
    elif state.dragon_awake:
        hint = "The dragon is hunting you!"
    elif distance <= game.WAKE_DISTANCE + 1:
        hint = "The air feels warm nearby…"
    else:
        hint = "The dungeon is quiet."
    return {
        "grid_size": game.GRID_SIZE,
        "level": state.level,
        "next_level": statistics.win_streak + 1,
        "fortification_level": max(0, state.level - 6),
        "forced_hard": state.level >= 10,
        "streak": statistics.win_streak,
        "player": position(state.player),
        "start": position(state.start),
        "treasure": position(state.treasure),
        "dragon": position(state.dragon),
        "visited": [position(value) for value in state.visited],
        "horizontal_walls": walls(
            state.horizontal_walls
            if debug or state.status != "playing"
            else state.discovered_h
        ),
        "vertical_walls": walls(
            state.vertical_walls
            if debug or state.status != "playing"
            else state.discovered_v
        ),
        "scorched": [position(value) for value in state.scorched],
        "moves": state.moves,
        "has_treasure": state.has_treasure,
        "dragon_awake": state.dragon_awake,
        "hard_mode": state.hard_mode,
        "status": state.status,
        "message": state.flash,
        "hint": hint,
        "debug": debug,
        "phantom": (
            {"position": position(phantom.dragon), "hard_mode": phantom.hard_mode}
            if phantom is not None and phantom.dragon_awake
            else None
        ),
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(
        ROOT / "web" / "index.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/debug")
async def debug_index() -> FileResponse:
    """Serve the debug client; debug-only controls are enabled by its URL."""
    return FileResponse(
        ROOT / "web" / "index.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/api/leaderboard")
async def leaderboard() -> JSONResponse:
    with database() as connection:
        rows = connection.execute("""
            SELECT username, wins, dragon_wins, escapes, best_win_moves, highest_win_streak
            FROM players
            ORDER BY wins DESC, highest_win_streak DESC, best_win_moves IS NULL, best_win_moves ASC, username COLLATE NOCASE
            LIMIT 50
            """).fetchall()
    return JSONResponse({"players": [dict(row) for row in rows]})


@app.websocket("/ws")
async def game_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    debug_mode = websocket.query_params.get("debug") == "1"
    state: game.GameState | None = None
    phantom: game.GameState | None = None
    statistics = game.Statistics()
    username: str | None = None
    moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "start":
                selected_name = player_name(message.get("username"))
                client_id = client_identifier(message.get("client_id"))
                if selected_name is None or (not debug_mode and client_id is None):
                    await websocket.send_json(
                        {"error": "Enter a username between 1 and 24 characters."}
                    )
                    continue
                if not debug_mode and not allow_username(selected_name, client_id):
                    await websocket.send_json(
                        {"error": "You can change username only twice per day."}
                    )
                    continue
                if debug_mode:
                    requested_level = message.get("level", 1)
                    if not isinstance(requested_level, int) or isinstance(
                        requested_level, bool
                    ):
                        requested_level = 1
                    requested_level = max(1, min(99, requested_level))
                    statistics = game.Statistics(
                        win_streak=requested_level - 1,
                        highest_win_streak=requested_level - 1,
                    )
                    username = selected_name
                elif selected_name != username:
                    username = selected_name
                    statistics = load_player(username)
                game.configure_difficulty(statistics, max_grid_size=13)
                state = game.make_game(
                    hard_mode=message.get("difficulty") == "hard"
                    or statistics.win_streak >= 9,
                    level=statistics.win_streak + 1,
                )
                phantom = make_phantom(state) if debug_mode else None
            elif action == "move" and state is not None:
                delta = moves.get(message.get("direction"))
                if delta is not None:
                    previous_player = state.player
                    game.attempt_move(
                        state, delta, statistics, persist_statistics=not debug_mode
                    )
                    if phantom is not None and state.player != previous_player:
                        advance_phantom(phantom, state.player)
                    if (
                        not debug_mode
                        and state.status != "playing"
                        and username is not None
                    ):
                        save_player(username, statistics)
            elif action == "restart" and state is not None:
                game.configure_difficulty(statistics, max_grid_size=13)
                state = game.make_game(
                    hard_mode=state.hard_mode, level=statistics.win_streak + 1
                )
                phantom = make_phantom(state) if debug_mode else None
            if state is not None:
                await websocket.send_json(
                    serialise(state, statistics, debug=debug_mode, phantom=phantom)
                )
    except WebSocketDisconnect:
        return


def make_phantom(state: game.GameState) -> game.GameState:
    """Create the opposite dragon mode for browser debug comparisons."""
    phantom = deepcopy(state)
    phantom.hard_mode = not state.hard_mode
    phantom.dragon_discovered_h.clear()
    phantom.dragon_discovered_v.clear()
    return phantom


def advance_phantom(phantom: game.GameState, player: game.Position) -> None:
    """Advance the debug comparison dragon without touching the real state."""
    phantom.player = player
    distance = max(
        abs(player[0] - phantom.dragon[0]), abs(player[1] - phantom.dragon[1])
    )
    if not phantom.dragon_awake and distance <= game.WAKE_DISTANCE:
        phantom.dragon_awake = True
        phantom.scorched.add(phantom.dragon)
    elif phantom.dragon_awake:
        game.dragon_step(phantom)
