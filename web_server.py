"""WebSocket adapter for the Dungeon Escape Python game rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import game


ROOT = Path(__file__).parent
app = FastAPI(title="Dungeon Escape")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


def position(value: game.Position) -> list[int]:
    return [value[0], value[1]]


def walls(values: set[game.Wall]) -> list[list[int]]:
    return [list(value) for value in values]


def serialise(state: game.GameState, statistics: game.Statistics) -> dict[str, Any]:
    """Return only rendering data; all decisions remain in game.py."""
    distance = max(abs(state.player[0] - state.dragon[0]), abs(state.player[1] - state.dragon[1]))
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
        "streak": statistics.win_streak,
        "player": position(state.player),
        "start": position(state.start),
        "treasure": position(state.treasure),
        "dragon": position(state.dragon),
        "visited": [position(value) for value in state.visited],
        "horizontal_walls": walls(state.horizontal_walls if state.status != "playing" else state.discovered_h),
        "vertical_walls": walls(state.vertical_walls if state.status != "playing" else state.discovered_v),
        "scorched": [position(value) for value in state.scorched],
        "moves": state.moves,
        "has_treasure": state.has_treasure,
        "dragon_awake": state.dragon_awake,
        "hard_mode": state.hard_mode,
        "status": state.status,
        "message": state.flash,
        "hint": hint,
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "web" / "index.html")


@app.websocket("/ws")
async def game_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    state: game.GameState | None = None
    statistics = game.Statistics()
    moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            if action == "start":
                game.configure_difficulty(statistics)
                state = game.make_game(hard_mode=message.get("difficulty") == "hard")
            elif action == "move" and state is not None:
                delta = moves.get(message.get("direction"))
                if delta is not None:
                    game.attempt_move(state, delta, statistics)
            elif action == "restart" and state is not None:
                game.configure_difficulty(statistics)
                state = game.make_game(hard_mode=state.hard_mode)
            if state is not None:
                await websocket.send_json(serialise(state, statistics))
    except WebSocketDisconnect:
        return
