"""Pathfinding algorithms used by Dungeon Escape."""

from collections.abc import Callable, Iterable
import heapq
from itertools import count


Position = tuple[int, int]


def astar_path(
    start: Position,
    goal: Position,
    neighbours: Callable[[Position], Iterable[Position]],
    grid_size: int,
) -> list[Position]:
    """Return a shortest path, preferring steps that point directly at the goal."""
    sequence = count()
    frontier = [(0, 0, 0, next(sequence), start)]
    previous: dict[Position, Position | None] = {start: None}
    cost = {start: 0}
    while frontier:
        _, _, _, _, current = heapq.heappop(frontier)
        if current == goal:
            break
        for nxt in neighbours(current):
            new_cost = cost[current] + 1
            if new_cost >= cost.get(nxt, grid_size * grid_size + 1):
                continue
            cost[nxt] = new_cost
            previous[nxt] = current
            dx = abs(nxt[0] - goal[0])
            dy = abs(nxt[1] - goal[1])
            heuristic = max(dx, dy)
            directness = dx * dx + dy * dy
            heapq.heappush(
                frontier,
                (new_cost + heuristic, heuristic, directness, next(sequence), nxt),
            )
    if goal not in previous:
        return []
    path = []
    current = goal
    while current != start:
        path.append(current)
        parent = previous[current]
        if parent is None:
            return []
        current = parent
    path.reverse()
    return path
