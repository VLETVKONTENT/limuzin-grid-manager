from __future__ import annotations

import pytest

from limuzin_grid_manager.core.crs import infer_gk_zone
from limuzin_grid_manager.core.geometry import normalize_bounds, rect_corners_ck42, round_bounds, snake_index
from limuzin_grid_manager.core.models import (
    Bounds,
    ExportMode,
    GridOptions,
    RoundingMode,
    SmallNumberingDirection,
    SmallNumberingMode,
    SpiralDirection,
    StartCorner,
)
from limuzin_grid_manager.core.numbering import small_number_index
from limuzin_grid_manager.core.stats import calculate_grid_stats, estimate_export_placemarks, estimate_export_size_bytes


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


def test_spiral_center_out_10x10_default_anchor_clockwise() -> None:
    assert small_number_index(
        4,
        4,
        10,
        10,
        SmallNumberingMode.SPIRAL_CENTER_OUT,
        SmallNumberingDirection.BY_ROWS,
        StartCorner.NW,
        SpiralDirection.CLOCKWISE,
    ) == 0
    assert small_number_index(4, 5, 10, 10, "spiral_center_out", "by_rows", "NW", "clockwise") == 1
    assert small_number_index(5, 5, 10, 10, "spiral_center_out", "by_rows", "NW", "clockwise") == 2
    assert small_number_index(5, 4, 10, 10, "spiral_center_out", "by_rows", "NW", "clockwise") == 3


def test_spiral_center_out_10x10_default_anchor_counterclockwise() -> None:
    assert small_number_index(4, 4, 10, 10, "spiral_center_out", "by_rows", "NW", "counterclockwise") == 0
    assert small_number_index(5, 4, 10, 10, "spiral_center_out", "by_rows", "NW", "counterclockwise") == 1
    assert small_number_index(5, 5, 10, 10, "spiral_center_out", "by_rows", "NW", "counterclockwise") == 2
    assert small_number_index(4, 5, 10, 10, "spiral_center_out", "by_rows", "NW", "counterclockwise") == 3


def test_spiral_edge_in_10x10_default_anchor_clockwise() -> None:
    assert small_number_index(0, 9, 10, 10, "spiral_edge_in", "by_rows", "NW", "clockwise") == 0
    assert small_number_index(4, 4, 10, 10, "spiral_edge_in", "by_rows", "NW", "clockwise") == 99
    assert small_number_index(5, 4, 10, 10, "spiral_edge_in", "by_rows", "NW", "clockwise") == 98


def test_spiral_center_anchor_variants() -> None:
    assert small_number_index(4, 4, 10, 10, "spiral_center_out", "by_rows", "NW", "clockwise") == 0
    assert small_number_index(4, 5, 10, 10, "spiral_center_out", "by_rows", "NE", "clockwise") == 0
    assert small_number_index(5, 4, 10, 10, "spiral_center_out", "by_rows", "SW", "clockwise") == 0
    assert small_number_index(5, 5, 10, 10, "spiral_center_out", "by_rows", "SE", "clockwise") == 0


def test_small_numbering_has_no_duplicates_for_10x10_modes() -> None:
    for mode in SmallNumberingMode:
        for direction in SmallNumberingDirection:
            for corner in StartCorner:
                for spiral_direction in SpiralDirection:
                    values = {
                        small_number_index(row, col, 10, 10, mode, direction, corner, spiral_direction)
                        for row in range(10)
                        for col in range(10)
                    }
                    assert values == set(range(100))


def test_large_export_warnings_and_limit_are_reported() -> None:
    options = GridOptions(
        include_1000=False,
        include_100=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )
    large_bounds = Bounds(5_800_000, 5_700_000, 6_650_000, 6_670_000)

    stats = calculate_grid_stats(large_bounds, options)

    assert not stats.errors
    assert estimate_export_placemarks(stats, options) == 200_000
    assert estimate_export_size_bytes(stats, options) > 0
    assert any("Большой экспорт" in warning for warning in stats.warnings)
    assert any("Предпросмотр" in warning for warning in stats.warnings)

    too_large_bounds = Bounds(5_800_100, 5_700_000, 6_650_000, 6_750_000)

    too_large_stats = calculate_grid_stats(too_large_bounds, options)

    assert any("Экспорт слишком большой" in error for error in too_large_stats.errors)
