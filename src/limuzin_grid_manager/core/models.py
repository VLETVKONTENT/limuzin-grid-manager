from __future__ import annotations

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


class SmallNumberingDirection(StrEnum):
    BY_ROWS = "by_rows"
    BY_COLUMNS = "by_columns"


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
    small_numbering_mode: SmallNumberingMode = SmallNumberingMode.SNAKE
    small_numbering_direction: SmallNumberingDirection = SmallNumberingDirection.BY_ROWS
    small_numbering_start_corner: StartCorner = StartCorner.NW
    rounding_mode: RoundingMode = RoundingMode.IN
    export_mode: ExportMode = ExportMode.KML

    def normalized(self) -> "GridOptions":
        return GridOptions(
            include_1000=self.include_1000,
            include_100=self.include_100,
            snake_big=self.snake_big,
            small_numbering_mode=SmallNumberingMode(self.small_numbering_mode),
            small_numbering_direction=SmallNumberingDirection(self.small_numbering_direction),
            small_numbering_start_corner=StartCorner(self.small_numbering_start_corner),
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
