from __future__ import annotations

from limuzin_grid_manager.core.models import SmallNumberingDirection, SmallNumberingMode, StartCorner


def small_number_index(
    row: int,
    col: int,
    rows: int,
    cols: int,
    mode: SmallNumberingMode | str,
    direction: SmallNumberingDirection | str,
    start_corner: StartCorner | str,
) -> int:
    mode = SmallNumberingMode(mode)
    direction = SmallNumberingDirection(direction)
    start_corner = StartCorner(start_corner)

    if rows <= 0 or cols <= 0:
        raise ValueError("Размер сетки должен быть положительным.")
    if row < 0 or row >= rows or col < 0 or col >= cols:
        raise ValueError("Ячейка находится за пределами сетки.")

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
) -> int:
    return small_number_index(row, col, rows, cols, mode, direction, start_corner) + 1


def _starts_from_north(start_corner: StartCorner) -> bool:
    return start_corner in (StartCorner.NW, StartCorner.NE)


def _starts_from_west(start_corner: StartCorner) -> bool:
    return start_corner in (StartCorner.NW, StartCorner.SW)
