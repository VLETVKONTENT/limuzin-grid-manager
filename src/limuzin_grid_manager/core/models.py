from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from limuzin_grid_manager.core.zones import ZoneSegment


DEFAULT_BIG_FILL_PALETTE = (
    "#e53935",
    "#43a047",
    "#1e88e5",
    "#fdd835",
    "#8e24aa",
    "#fb8c00",
    "#00acc1",
    "#6d4c41",
)


class RoundingMode(StrEnum):
    IN = "in"
    OUT = "out"
    NONE = "none"


class ExportMode(StrEnum):
    KML = "kml"
    ZIP = "zip"
    SVG = "svg"
    GEOJSON = "geojson"
    CSV = "csv"


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


class BigTileFillMode(StrEnum):
    NONE = "none"
    SINGLE = "single"
    BY_NUMBER = "by_number"
    CUSTOM = "custom"


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
class KmlStyle:
    big_line_color: str = "#000000"
    small_line_color: str = "#000000"
    big_line_width: int = 2
    small_line_width: int = 1
    big_fill_mode: BigTileFillMode = BigTileFillMode.NONE
    big_fill_color: str = "#fdd835"
    big_fill_opacity: int = 35
    big_fill_palette: tuple[str, ...] = DEFAULT_BIG_FILL_PALETTE
    custom_big_fill_colors: tuple[tuple[int, str], ...] = ()
    small_fill_enabled: bool = False
    small_fill_color: str = "#90caf9"
    small_fill_opacity: int = 25

    def normalized(self) -> "KmlStyle":
        palette = tuple(normalize_rgb_color(color) for color in self.big_fill_palette) or DEFAULT_BIG_FILL_PALETTE
        return KmlStyle(
            big_line_color=normalize_rgb_color(self.big_line_color),
            small_line_color=normalize_rgb_color(self.small_line_color),
            big_line_width=normalize_line_width(self.big_line_width),
            small_line_width=normalize_line_width(self.small_line_width),
            big_fill_mode=BigTileFillMode(self.big_fill_mode),
            big_fill_color=normalize_rgb_color(self.big_fill_color),
            big_fill_opacity=normalize_opacity_percent(self.big_fill_opacity),
            big_fill_palette=palette,
            custom_big_fill_colors=normalize_big_fill_colors(self.custom_big_fill_colors),
            small_fill_enabled=bool(self.small_fill_enabled),
            small_fill_color=normalize_rgb_color(self.small_fill_color),
            small_fill_opacity=normalize_opacity_percent(self.small_fill_opacity),
        )


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
    kml_style: KmlStyle = field(default_factory=KmlStyle)

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
            kml_style=self.kml_style.normalized(),
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
    zone_segments: tuple[ZoneSegment, ...] = ()

    @property
    def zone(self) -> int | None:
        if self.zone_left is None or self.zone_right is None:
            return None
        if self.zone_left != self.zone_right:
            return None
        if self.zone_segments and any(segment.zone != self.zone_left for segment in self.zone_segments):
            return None
        return self.zone_left

    @property
    def is_multi_zone(self) -> bool:
        return len({segment.zone for segment in self.zone_segments}) > 1


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


def normalize_big_fill_colors(
    value: Mapping[int | str, str] | Iterable[tuple[int | str, str]],
) -> tuple[tuple[int, str], ...]:
    items = value.items() if isinstance(value, Mapping) else value
    colors: dict[int, str] = {}
    for number_value, color_value in items:
        number = int(number_value)
        if number > 0:
            colors[number] = normalize_rgb_color(color_value)
    return tuple(sorted(colors.items()))


def normalize_rgb_color(value: str) -> str:
    text = str(value).strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6 or any(char not in "0123456789abcdefABCDEF" for char in text):
        raise ValueError(f"Цвет должен быть в формате #RRGGBB: {value!r}.")
    return f"#{text.lower()}"


def normalize_line_width(value: int) -> int:
    return max(1, min(12, int(value)))


def normalize_opacity_percent(value: int) -> int:
    return max(0, min(100, int(value)))
