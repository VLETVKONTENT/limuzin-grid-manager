from __future__ import annotations

import pytest

from limuzin_grid_manager.core.models import Bounds, ExportMode, GridOptions, RoundingMode
from limuzin_grid_manager.core.stats import calculate_grid_stats
from limuzin_grid_manager.core.zones import (
    ZoneSegment,
    split_bounds_by_zone,
    validate_gk_zone,
    zone_for_y,
    zone_for_y_interval,
)


def test_zone_for_y_matches_gk_million_prefix() -> None:
    assert zone_for_y(6_650_000) == 6
    assert zone_for_y(7_000_000) == 7
    assert zone_for_y(-7_250_000) == 7


def test_split_bounds_by_zone_keeps_single_zone_bounds() -> None:
    bounds = Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_650_000, y_right=6_652_000)

    assert split_bounds_by_zone(bounds) == (ZoneSegment(zone=6, bounds=bounds),)


def test_split_bounds_by_zone_handles_left_edge_on_boundary() -> None:
    bounds = Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=7_000_000, y_right=7_002_000)

    assert split_bounds_by_zone(bounds) == (ZoneSegment(zone=7, bounds=bounds),)


def test_split_bounds_by_zone_splits_two_zones() -> None:
    bounds = Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_999_000, y_right=7_001_000)

    assert split_bounds_by_zone(bounds) == (
        ZoneSegment(zone=6, bounds=Bounds(5_662_000, 5_660_000, 6_999_000, 7_000_000)),
        ZoneSegment(zone=7, bounds=Bounds(5_662_000, 5_660_000, 7_000_000, 7_001_000)),
    )


def test_split_bounds_by_zone_splits_multiple_zones() -> None:
    bounds = Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_999_000, y_right=9_001_000)

    segments = split_bounds_by_zone(bounds)

    assert [segment.zone for segment in segments] == [6, 7, 8, 9]
    assert [segment.bounds.y_left for segment in segments] == [6_999_000, 7_000_000, 8_000_000, 9_000_000]
    assert [segment.bounds.y_right for segment in segments] == [7_000_000, 8_000_000, 9_000_000, 9_001_000]


def test_split_bounds_by_zone_rejects_unsupported_zone() -> None:
    bounds = Bounds(x_top=1_000, x_bottom=0, y_left=33_000_000, y_right=33_001_000)

    with pytest.raises(ValueError, match="Ожидается 1..32"):
        split_bounds_by_zone(bounds)

    with pytest.raises(ValueError, match="Ожидается 1..32"):
        validate_gk_zone(33)


def test_zone_for_y_interval_rejects_cell_crossing_boundary() -> None:
    assert zone_for_y_interval(6_999_000, 7_000_000) == 6
    assert zone_for_y_interval(7_000_000, 7_001_000) == 7

    with pytest.raises(ValueError, match="Экспортируемая ячейка пересекает границу зон"):
        zone_for_y_interval(6_999_500, 7_000_500)


def test_stats_allows_aligned_multi_zone_export() -> None:
    options = GridOptions(
        include_1000=True,
        include_100=False,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )
    bounds = Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_999_000, y_right=7_001_000)

    stats = calculate_grid_stats(bounds, options)

    assert stats.is_multi_zone
    assert [segment.zone for segment in stats.zone_segments] == [6, 7]
    assert stats.zone is None
    assert stats.errors == ()


def test_stats_rejects_cell_crossing_zone_boundary() -> None:
    options = GridOptions(
        include_1000=True,
        include_100=False,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )
    bounds = Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_999_500, y_right=7_001_500)

    stats = calculate_grid_stats(bounds, options)

    assert stats.is_multi_zone
    assert any("внутри одной ячейки" in error for error in stats.errors)
