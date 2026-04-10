from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import isfinite

from limuzin_grid_manager.core.models import normalize_opacity_percent, normalize_rgb_color
from limuzin_grid_manager.core.zones import validate_gk_zone

_EXCEL_EPOCH = datetime(1899, 12, 30)
_COORDINATE_TRANSLATION = str.maketrans(
    {
        "x": " ",
        "X": " ",
        "y": " ",
        "Y": " ",
        "х": " ",
        "Х": " ",
        "у": " ",
        "У": " ",
        ",": " ",
        ";": " ",
        ":": " ",
        "=": " ",
        "(": " ",
        ")": " ",
        "[": " ",
        "]": " ",
        "{": " ",
        "}": " ",
        "\u00a0": " ",
    }
)
_LABELED_COORDINATE_PATTERN = re.compile(
    r"^\s*[xXхХ]\s*[-:=]?\s*(\d+)\s*[,;]?\s*[yYуУ]\s*[-:=]?\s*(\d+)\s*$"
)


@dataclass(frozen=True)
class PointRecord:
    name: str
    source_date: str
    display_date: str
    x: int
    y: int
    zone: int
    lon: float
    lat: float
    source_row: int

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ValueError("Имя точки не заполнено.")

        source_date = str(self.source_date).strip()
        if not source_date:
            raise ValueError("Исходная дата точки не заполнена.")

        display_date = normalize_point_date(self.display_date)
        x = int(self.x)
        y = int(self.y)
        zone = validate_gk_zone(int(self.zone))
        lon = float(self.lon)
        lat = float(self.lat)
        source_row = int(self.source_row)

        if source_row < 1:
            raise ValueError("Номер строки источника должен быть положительным.")
        if not isfinite(lon) or not isfinite(lat):
            raise ValueError("Координаты WGS84 должны быть конечными числами.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "source_date", source_date)
        object.__setattr__(self, "display_date", display_date)
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "zone", zone)
        object.__setattr__(self, "lon", lon)
        object.__setattr__(self, "lat", lat)
        object.__setattr__(self, "source_row", source_row)


@dataclass(frozen=True)
class PointStyle:
    color: str = "#32ca00"
    opacity: int = 100

    def normalized(self) -> "PointStyle":
        return PointStyle(
            color=normalize_point_color(self.color),
            opacity=normalize_point_opacity(self.opacity),
        )


def normalize_point_color(value: str) -> str:
    return normalize_rgb_color(value)


def normalize_point_opacity(value: int) -> int:
    return normalize_opacity_percent(value)


def point_style_to_kml_color(style: PointStyle) -> str:
    normalized = style.normalized()
    rgb = normalized.color.removeprefix("#")
    alpha = max(0, min(255, int(normalized.opacity * 255 / 100 + 0.5)))
    red = rgb[0:2]
    green = rgb[2:4]
    blue = rgb[4:6]
    return f"{alpha:02X}{blue.upper()}{green.upper()}{red.upper()}"


def normalize_point_date(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, bool):
        raise ValueError("Дата точки не может быть логическим значением.")
    if isinstance(value, int | float):
        if not isfinite(float(value)):
            raise ValueError("Дата точки должна быть конечным числом.")
        excel_date = _EXCEL_EPOCH + timedelta(days=float(value))
        return excel_date.strftime("%d.%m.%Y")

    text = str(value).strip()
    if not text:
        raise ValueError("Дата точки не заполнена.")

    number_text = text.replace(",", ".")
    if _looks_like_number(number_text):
        return normalize_point_date(float(number_text))

    try:
        parsed = datetime.strptime(text, "%d.%m.%Y")
    except ValueError as exc:
        raise ValueError(f"Дата точки должна быть в формате dd.mm.yyyy: {value!r}.") from exc
    return parsed.strftime("%d.%m.%Y")


def parse_point_coordinates(value: str) -> tuple[int, int]:
    text = str(value).strip()
    if not text:
        raise ValueError(
            "Координаты точки не заполнены."
        )

    labeled_match = _LABELED_COORDINATE_PATTERN.fullmatch(text)
    if labeled_match:
        return int(labeled_match.group(1)), int(labeled_match.group(2))

    tokens = text.translate(_COORDINATE_TRANSLATION).split()
    if len(tokens) != 2:
        raise ValueError(
            "Координаты точки должны содержать ровно два целых числа X и Y, например 'х-5649764 y-6661612'."
        )

    try:
        x = int(tokens[0])
        y = int(tokens[1])
    except ValueError as exc:
        raise ValueError("Координаты точки должны быть целыми числами X и Y.") from exc
    return x, y
def _looks_like_number(value: str) -> bool:
    if value.count(".") > 1:
        return False
    if value.startswith(("+", "-")):
        value = value[1:]
    return bool(value) and all(char.isdigit() or char == "." for char in value)
