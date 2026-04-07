from __future__ import annotations

from functools import lru_cache

from limuzin_grid_manager.core.models import (
    SmallNumberingDirection,
    SmallNumberingMode,
    SpiralDirection,
    StartCorner,
)


def small_number_index(
    row: int,
    col: int,
    rows: int,
    cols: int,
    mode: SmallNumberingMode | str,
    direction: SmallNumberingDirection | str,
    start_corner: StartCorner | str,
    spiral_direction: SpiralDirection | str = SpiralDirection.CLOCKWISE,
) -> int:
    mode = SmallNumberingMode(mode)
    direction = SmallNumberingDirection(direction)
    start_corner = StartCorner(start_corner)
    spiral_direction = SpiralDirection(spiral_direction)

    if rows <= 0 or cols <= 0:
        raise ValueError("Размер сетки должен быть положительным.")
    if row < 0 or row >= rows or col < 0 or col >= cols:
        raise ValueError("Ячейка находится за пределами сетки.")

    if _is_spiral_mode(mode):
        return _spiral_number_index(row, col, rows, cols, mode, start_corner, spiral_direction)

    row_pos = row if _starts_from_north(start_corner) else rows - 1 - row
    col_pos = col if _starts_from_west(start_corner) else cols - 1 - col

    if direction == SmallNumberingDirection.BY_ROWS:
        if mode == SmallNumberingMode.SNAKE and row_pos % 2 == 1:
            col_pos = cols - 1 - col_pos
        return row_pos * cols + col_pos

    if mode == SmallNumberingMode.SNAKE and col_pos % 2 == 1:
        row_pos = rows - 1 - row_pos
    return col_pos * rows + row_pos


def small_number(
    row: int,
    col: int,
    rows: int,
    cols: int,
    mode: SmallNumberingMode | str,
    direction: SmallNumberingDirection | str,
    start_corner: StartCorner | str,
    spiral_direction: SpiralDirection | str = SpiralDirection.CLOCKWISE,
) -> int:
    return small_number_index(row, col, rows, cols, mode, direction, start_corner, spiral_direction) + 1


def _starts_from_north(start_corner: StartCorner) -> bool:
    return start_corner in (StartCorner.NW, StartCorner.NE)


def _starts_from_west(start_corner: StartCorner) -> bool:
    return start_corner in (StartCorner.NW, StartCorner.SW)


def _is_spiral_mode(mode: SmallNumberingMode) -> bool:
    return mode in (SmallNumberingMode.SPIRAL_CENTER_OUT, SmallNumberingMode.SPIRAL_EDGE_IN)


def _spiral_number_index(
    row: int,
    col: int,
    rows: int,
    cols: int,
    mode: SmallNumberingMode,
    center_anchor: StartCorner,
    spiral_direction: SpiralDirection,
) -> int:
    indexes = _spiral_indexes(rows, cols, mode, center_anchor, spiral_direction)
    return indexes[row * cols + col]


@lru_cache(maxsize=64)
def _spiral_indexes(
    rows: int,
    cols: int,
    mode: SmallNumberingMode,
    center_anchor: StartCorner,
    spiral_direction: SpiralDirection,
) -> tuple[int, ...]:
    center_out_direction = spiral_direction
    if mode == SmallNumberingMode.SPIRAL_EDGE_IN:
        # Reversing an outward spiral flips its turn direction, so build the opposite first.
        center_out_direction = _opposite_spiral_direction(spiral_direction)

    path = _spiral_center_out_path(rows, cols, center_anchor, center_out_direction)
    if mode == SmallNumberingMode.SPIRAL_EDGE_IN:
        path = tuple(reversed(path))

    indexes = [0] * (rows * cols)
    for index, (path_row, path_col) in enumerate(path):
        indexes[path_row * cols + path_col] = index
    return tuple(indexes)


def _spiral_center_out_path(
    rows: int,
    cols: int,
    center_anchor: StartCorner,
    spiral_direction: SpiralDirection,
) -> tuple[tuple[int, int], ...]:
    row = _center_row(rows, center_anchor)
    col = _center_col(cols, center_anchor)
    path = [(row, col)]
    total = rows * cols
    directions = _spiral_directions(center_anchor, spiral_direction)

    direction_index = 0
    step_size = 1
    while len(path) < total:
        for _ in range(2):
            delta_row, delta_col = directions[direction_index % 4]
            for _ in range(step_size):
                row += delta_row
                col += delta_col
                if 0 <= row < rows and 0 <= col < cols:
                    path.append((row, col))
                    if len(path) == total:
                        return tuple(path)
            direction_index += 1
        step_size += 1

    return tuple(path)


def _center_row(rows: int, center_anchor: StartCorner) -> int:
    if rows % 2 == 1:
        return rows // 2
    if _starts_from_north(center_anchor):
        return rows // 2 - 1
    return rows // 2


def _center_col(cols: int, center_anchor: StartCorner) -> int:
    if cols % 2 == 1:
        return cols // 2
    if _starts_from_west(center_anchor):
        return cols // 2 - 1
    return cols // 2


def _spiral_directions(
    center_anchor: StartCorner,
    spiral_direction: SpiralDirection,
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
    clockwise = {
        StartCorner.NW: ((0, 1), (1, 0), (0, -1), (-1, 0)),
        StartCorner.NE: ((1, 0), (0, -1), (-1, 0), (0, 1)),
        StartCorner.SE: ((0, -1), (-1, 0), (0, 1), (1, 0)),
        StartCorner.SW: ((-1, 0), (0, 1), (1, 0), (0, -1)),
    }
    counterclockwise = {
        StartCorner.NW: ((1, 0), (0, 1), (-1, 0), (0, -1)),
        StartCorner.NE: ((0, -1), (1, 0), (0, 1), (-1, 0)),
        StartCorner.SE: ((-1, 0), (0, -1), (1, 0), (0, 1)),
        StartCorner.SW: ((0, 1), (-1, 0), (0, -1), (1, 0)),
    }
    if spiral_direction == SpiralDirection.CLOCKWISE:
        return clockwise[center_anchor]
    return counterclockwise[center_anchor]


def _opposite_spiral_direction(spiral_direction: SpiralDirection) -> SpiralDirection:
    if spiral_direction == SpiralDirection.CLOCKWISE:
        return SpiralDirection.COUNTERCLOCKWISE
    return SpiralDirection.CLOCKWISE
