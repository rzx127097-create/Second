"""Deterministic grid topology helpers."""

from __future__ import annotations

from collections import deque
from typing import Iterable

Cell = tuple[int, int]
Edge = tuple[Cell, Cell]


def four_connected_edges(cells: Iterable[Cell]) -> list[Edge]:
    """Return each horizontal/vertical grid edge exactly once in stable order."""

    occupied = {tuple(cell) for cell in cells}
    edges: set[Edge] = set()
    for row, col in occupied:
        for neighbour in ((row, col + 1), (row + 1, col)):
            if neighbour in occupied:
                edges.add(((row, col), neighbour) if (row, col) < neighbour else (neighbour, (row, col)))
    return sorted(edges)


def connected_components(cells: Iterable[Cell]) -> list[set[Cell]]:
    """Return four-connected components sorted by their smallest cell."""

    remaining = {tuple(cell) for cell in cells}
    components: list[set[Cell]] = []
    while remaining:
        start = min(remaining)
        component = {start}
        remaining.remove(start)
        queue = deque([start])
        while queue:
            row, col = queue.popleft()
            for neighbour in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    component.add(neighbour)
                    queue.append(neighbour)
        components.append(component)
    return components

