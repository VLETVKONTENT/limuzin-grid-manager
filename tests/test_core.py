from __future__ import annotations

import pytest

from limuzin_grid_manager.core.crs import infer_gk_zone
from limuzin_grid_manager.core.geometry import normalize_bounds, rect_corners_ck42, round_bounds, snake_index
from limuzin_grid_manager.core.models import Bounds, RoundingMode, SmallNumberingDirection, SmallNumberingMode, StartCorner
from limuzin_grid_manager.core.numbering import small_number_index


def test_infer_gk_zone() -> None:
    assert infer_gk_zone(6_650_000) == 6


def test_round_bounds_in_out_none() -> None:
    bounds = Bounds(x_top=5_660_950, x_bottom=5_650_050, y_left=6_650_050, y_right=6_669_950)

    assert round_bounds(bounds, 1000, RoundingMode.IN) == Bounds(
        x_top=5_660_000,
        x_bottom=5_651_000,
        y_left=6_651_000,
        y_right=6_669_000,
    )
    assert round_bounds(bounds, 1000, RoundingMode.OUT) == Bounds(
        x_top=5_661_000,
        x_bottom=5_650_000,
        y_left=6_650_000,
        y_right=6_670_000,
    )
    assert round_bounds(bounds, 1000, RoundingMode.NONE) == bounds


def test_round_bounds_raises_when_area_disappears() -> None:
    with pytest.raises(ValueError):
        round_bounds(Bounds(1050, 1010, 2010, 2050), 100, RoundingMode.IN)


def test_snake_index() -> None:
    assert [snake_index(0, col, 4) for col in range(4)] == [0, 1, 2, 3]
    assert [snake_index(1, col, 4) for col in range(4)] == [7, 6, 5, 4]


def test_rect_corners_order() -> None:
    assert rect_corners_ck42(1000, 2000, 100, 100) == [
        (1000, 2000),
        (900, 2000),
        (900, 2100),
        (1000, 2100),
        (1000, 2000),
    ]


def test_normalize_bounds() -> None:
    assert normalize_bounds(100, 400, 900, 200) == Bounds(
        x_top=900,
        x_bottom=100,
        y_left=200,
        y_right=400,
    )


def test_small_numbering_default_matches_old_snake() -> None:
    values = [small_number_index(1, col, 2, 4, "snake", "by_rows", "NW") for col in range(4)]
    assert values == [7, 6, 5, 4]


def test_small_numbering_row_linear_from_each_corner() -> None:
    assert small_number_index(0, 0, 2, 3, SmallNumberingMode.LINEAR, SmallNumberingDirection.BY_ROWS, StartCorner.NW) == 0
    assert small_number_index(0, 2, 2, 3, SmallNumberingMode.LINEAR, SmallNumberingDirection.BY_ROWS, StartCorner.NE) == 0
    assert small_number_index(1, 0, 2, 3, SmallNumberingMode.LINEAR, SmallNumberingDirection.BY_ROWS, StartCorner.SW) == 0
    assert small_number_index(1, 2, 2, 3, SmallNumberingMode.LINEAR, SmallNumberingDirection.BY_ROWS, StartCorner.SE) == 0


def test_small_numbering_column_snake() -> None:
    values = [small_number_index(row, 1, 3, 2, "snake", "by_columns", "NW") for row in range(3)]
    assert values == [5, 4, 3]


def test_small_numbering_has_no_duplicates_for_10x10_modes() -> None:
    for mode in SmallNumberingMode:
        for direction in SmallNumberingDirection:
            for corner in StartCorner:
                values = {
                    small_number_index(row, col, 10, 10, mode, direction, corner)
                    for row in range(10)
                    for col in range(10)
                }
                assert values == set(range(100))
