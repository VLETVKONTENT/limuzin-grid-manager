from __future__ import annotations

from dataclasses import dataclass

from limuzin_grid_manager.core.models import Bounds


GK_ZONE_WIDTH_M = 1_000_000
GK_ZONE_MIN = 1
GK_ZONE_MAX = 32


@dataclass(frozen=True)
class ZoneSegment:
    zone: int
    bounds: Bounds


def zone_for_y(y: float) -> int:
    return int(abs(y) // GK_ZONE_WIDTH_M)


def zone_for_y_interval(y_left: int, y_right: int) -> int:
    if y_right <= y_left:
        raise ValueError("Интервал Y должен иметь положительную ширину.")

    boundaries = _zone_boundaries_inside(y_left, y_right)
    if boundaries:
        formatted = ", ".join(str(boundary) for boundary in boundaries)
        raise ValueError(
            "Экспортируемая ячейка пересекает границу зон Гаусса-Крюгера "
            f"по Y={formatted}. Выровняйте границы по сетке или разделите область."
        )

    sample_y = (y_left + y_right) / 2
    return validate_gk_zone(zone_for_y(sample_y))


def zone_boundaries_inside(y_left: int, y_right: int) -> tuple[int, ...]:
    return _zone_boundaries_inside(y_left, y_right)


def validate_gk_zone(zone: int) -> int:
    if zone < GK_ZONE_MIN or zone > GK_ZONE_MAX:
        raise ValueError(
            f"Некорректная зона Гаусса-Крюгера: {zone}. "
            f"Ожидается {GK_ZONE_MIN}..{GK_ZONE_MAX}."
        )
    return zone


def split_bounds_by_zone(bounds: Bounds) -> tuple[ZoneSegment, ...]:
    if bounds.width_m() <= 0 or bounds.height_m() <= 0:
        raise ValueError("Область должна иметь положительную ширину и высоту.")

    split_points = sorted({bounds.y_left, bounds.y_right, *_zone_boundaries_inside(bounds.y_left, bounds.y_right)})
    segments: list[ZoneSegment] = []
    for y_left, y_right in zip(split_points, split_points[1:]):
        if y_right <= y_left:
            continue
        sample_y = (y_left + y_right) / 2
        zone = validate_gk_zone(zone_for_y(sample_y))
        segments.append(
            ZoneSegment(
                zone=zone,
                bounds=Bounds(
                    x_top=bounds.x_top,
                    x_bottom=bounds.x_bottom,
                    y_left=y_left,
                    y_right=y_right,
                ),
            )
        )

    if not segments:
        raise ValueError("Не удалось разбить область по зонам Гаусса-Крюгера.")
    return tuple(segments)


def format_zone_segments(segments: tuple[ZoneSegment, ...]) -> str:
    return "; ".join(
        f"зона {segment.zone}: Y {segment.bounds.y_left}..{segment.bounds.y_right}" for segment in segments
    )


def _zone_boundaries_inside(y_left: int, y_right: int) -> tuple[int, ...]:
    boundaries: list[int] = []
    for zone_boundary in range(0, GK_ZONE_MAX + 2):
        positive = zone_boundary * GK_ZONE_WIDTH_M
        if y_left < positive < y_right:
            boundaries.append(positive)
        if positive:
            negative = -positive
            if y_left < negative < y_right:
                boundaries.append(negative)
    return tuple(boundaries)
