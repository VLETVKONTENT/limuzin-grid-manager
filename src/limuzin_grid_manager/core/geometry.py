from __future__ import annotations

from limuzin_grid_manager.core.models import Bounds, RoundingMode


def normalize_bounds(x_nw: int, y_nw: int, x_se: int, y_se: int) -> Bounds:
    return Bounds(
        x_top=max(x_nw, x_se),
        x_bottom=min(x_nw, x_se),
        y_left=min(y_nw, y_se),
        y_right=max(y_nw, y_se),
    )


def round_bounds(bounds: Bounds, step: int, mode: RoundingMode | str) -> Bounds:
    mode = RoundingMode(mode)
    if mode == RoundingMode.NONE:
        return bounds

    def floor_to(value: int, grid_step: int) -> int:
        return (value // grid_step) * grid_step

    def ceil_to(value: int, grid_step: int) -> int:
        return ((value + grid_step - 1) // grid_step) * grid_step

    if mode == RoundingMode.IN:
        rounded = Bounds(
            x_top=floor_to(bounds.x_top, step),
            x_bottom=ceil_to(bounds.x_bottom, step),
            y_left=ceil_to(bounds.y_left, step),
            y_right=floor_to(bounds.y_right, step),
        )
    else:
        rounded = Bounds(
            x_top=ceil_to(bounds.x_top, step),
            x_bottom=floor_to(bounds.x_bottom, step),
            y_left=floor_to(bounds.y_left, step),
            y_right=ceil_to(bounds.y_right, step),
        )

    if rounded.x_top <= rounded.x_bottom or rounded.y_right <= rounded.y_left:
        raise ValueError("После округления границы стали некорректными: площадь <= 0.")
    return rounded


def count_grid(bounds: Bounds, step: int) -> tuple[int, int]:
    return bounds.height_m() // step, bounds.width_m() // step


def rect_corners_ck42(x_top: int, y_left: int, step_x: int, step_y: int) -> list[tuple[int, int]]:
    x_bottom = x_top - step_x
    y_right = y_left + step_y
    return [
        (x_top, y_left),
        (x_bottom, y_left),
        (x_bottom, y_right),
        (x_top, y_right),
        (x_top, y_left),
    ]


def snake_index(row: int, col: int, cols: int) -> int:
    if row % 2 == 0:
        return row * cols + col
    return row * cols + (cols - 1 - col)
