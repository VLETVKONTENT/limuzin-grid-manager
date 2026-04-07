from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum


class RoundingMode(StrEnum):
    IN = "in"
    OUT = "out"
    NONE = "none"


class ExportMode(StrEnum):
    KML = "kml"
    ZIP = "zip"


class SmallNumberingMode(StrEnum):
    LINEAR = "linear"
    SNAKE = "snake"
    SPIRAL_CENTER_OUT = "spiral_center_out"
    SPIRAL_EDGE_IN = "spiral_edge_in"


class SmallNumberingDirection(StrEnum):
    BY_ROWS = "by_rows"
    BY_COLUMNS = "by_columns"


class SpiralDirection(StrEnum):
    CLOCKWISE = "clockwise"
    COUNTERCLOCKWISE = "counterclockwise"


class StartCorner(StrEnum):
    NW = "NW"
    NE = "NE"
    SW = "SW"
    SE = "SE"


@dataclass(frozen=True)
class Bounds:
    x_top: int
    x_bottom: int
    y_left: int
    y_right: int

    def width_m(self) -> int:
        return self.y_right - self.y_left

    def height_m(self) -> int:
        return self.x_top - self.x_bottom


@dataclass(frozen=True)
class GridOptions:
    include_1000: bool = True
    include_100: bool = True
    snake_big: bool = True
    big_tile_names: tuple[tuple[int, str], ...] = ()
    small_numbering_mode: SmallNumberingMode = SmallNumberingMode.SNAKE
    small_numbering_direction: SmallNumberingDirection = SmallNumberingDirection.BY_ROWS
    small_numbering_start_corner: StartCorner = StartCorner.NW
    small_spiral_direction: SpiralDirection = SpiralDirection.CLOCKWISE
    rounding_mode: RoundingMode = RoundingMode.IN
    export_mode: ExportMode = ExportMode.KML

    def normalized(self) -> "GridOptions":
        return GridOptions(
            include_1000=self.include_1000,
            include_100=self.include_100,
            snake_big=self.snake_big,
            big_tile_names=normalize_big_tile_names(self.big_tile_names),
            small_numbering_mode=SmallNumberingMode(self.small_numbering_mode),
            small_numbering_direction=SmallNumberingDirection(self.small_numbering_direction),
            small_numbering_start_corner=StartCorner(self.small_numbering_start_corner),
            small_spiral_direction=SpiralDirection(self.small_spiral_direction),
            rounding_mode=RoundingMode(self.rounding_mode),
            export_mode=ExportMode(self.export_mode),
        )


@dataclass(frozen=True)
class GridSize:
    rows: int
    cols: int

    @property
    def total(self) -> int:
        return self.rows * self.cols


@dataclass(frozen=True)
class GridStats:
    raw_bounds: Bounds
    rounded_bounds: Bounds | None
    big_bounds: Bounds | None
    small_bounds: Bounds | None
    big_grid: GridSize | None
    small_grid: GridSize | None
    zone_left: int | None
    zone_right: int | None
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def zone(self) -> int | None:
        if self.zone_left is None or self.zone_right is None:
            return None
        if self.zone_left != self.zone_right:
            return None
        return self.zone_left


def normalize_big_tile_names(
    value: Mapping[int | str, str] | Iterable[tuple[int | str, str]],
) -> tuple[tuple[int, str], ...]:
    items = value.items() if isinstance(value, Mapping) else value
    names: dict[int, str] = {}
    for number_value, name_value in items:
        number = int(number_value)
        name = str(name_value).strip()
        if number > 0 and name:
            names[number] = name
    return tuple(sorted(names.items()))
