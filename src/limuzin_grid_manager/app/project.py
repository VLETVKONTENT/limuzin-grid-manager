from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from limuzin_grid_manager import __version__
from limuzin_grid_manager.app.export_formats import default_export_directory, export_format_by_id, export_format_for_mode
from limuzin_grid_manager.core.models import (
    BigTileFillMode,
    ExportMode,
    GridOptions,
    KmlStyle,
    RoundingMode,
    SmallNumberingDirection,
    SmallNumberingMode,
    SpiralDirection,
    StartCorner,
)


PROJECT_SCHEMA = "limuzin-grid-manager-project"
PROJECT_SCHEMA_VERSION = 1
PROJECT_EXTENSION = ".lgm.json"
PROJECT_DIALOG_FILTER = "Проект LIMUZIN GRID MANAGER (*.lgm.json);;JSON (*.json);;Все файлы (*)"


class ProjectFileError(ValueError):
    pass


@dataclass(frozen=True)
class CoordinateState:
    x_nw: str = "5660000"
    y_nw: str = "6650000"
    x_se: str = "5650000"
    y_se: str = "6670000"


@dataclass(frozen=True)
class ProjectState:
    coordinates: CoordinateState
    options: GridOptions
    export_folder: str
    export_filename: str


@dataclass(frozen=True)
class ProjectPreset:
    id: str
    title: str
    description: str


PROJECT_PRESETS: tuple[ProjectPreset, ...] = (
    ProjectPreset(
        id="legacy_v001",
        title="Режим v0.0.1",
        description="Черные линии, без заливки, обе сетки и старая змейка 100x100.",
    ),
    ProjectPreset(
        id="numbering_snake_rows",
        title="Нумерация: змейка по строкам",
        description="100x100 идут змейкой по строкам от верхнего левого угла.",
    ),
    ProjectPreset(
        id="numbering_linear_rows",
        title="Нумерация: обычная по строкам",
        description="100x100 идут обычным порядком по строкам от верхнего левого угла.",
    ),
    ProjectPreset(
        id="numbering_linear_columns",
        title="Нумерация: обычная по колонкам",
        description="100x100 идут обычным порядком по колонкам от верхнего левого угла.",
    ),
    ProjectPreset(
        id="numbering_spiral_center",
        title="Нумерация: спираль от центра",
        description="100x100 нумеруются от центрального якоря наружу по часовой стрелке.",
    ),
    ProjectPreset(
        id="numbering_spiral_edge",
        title="Нумерация: спираль к центру",
        description="100x100 нумеруются от края к центральному якорю.",
    ),
    ProjectPreset(
        id="style_default",
        title="Стиль: черные линии",
        description="Стандартный KML без заливки, совместимый со старым поведением.",
    ),
    ProjectPreset(
        id="style_big_palette",
        title="Стиль: палитра 1000x1000",
        description="Большие квадраты получают мягкую цветную заливку по номерам.",
    ),
    ProjectPreset(
        id="style_small_fill",
        title="Стиль: заливка 100x100",
        description="Все малые квадраты получают одну легкую голубую заливку.",
    ),
)


def default_project_state() -> ProjectState:
    export_format = export_format_for_mode(ExportMode.KML)
    return ProjectState(
        coordinates=CoordinateState(),
        options=GridOptions(),
        export_folder=str(default_export_directory()),
        export_filename=export_format.default_filename,
    )


def available_project_presets() -> tuple[ProjectPreset, ...]:
    return PROJECT_PRESETS


def apply_project_preset(preset_id: str, options: GridOptions) -> GridOptions:
    current = options.normalized()

    if preset_id == "legacy_v001":
        return GridOptions(
            include_1000=True,
            include_100=True,
            snake_big=True,
            small_numbering_mode=SmallNumberingMode.SNAKE,
            small_numbering_direction=SmallNumberingDirection.BY_ROWS,
            small_numbering_start_corner=StartCorner.NW,
            small_spiral_direction=SpiralDirection.CLOCKWISE,
            rounding_mode=RoundingMode.IN,
            export_mode=ExportMode.KML,
            kml_style=KmlStyle(),
        )

    if preset_id == "numbering_snake_rows":
        return replace(
            current,
            small_numbering_mode=SmallNumberingMode.SNAKE,
            small_numbering_direction=SmallNumberingDirection.BY_ROWS,
            small_numbering_start_corner=StartCorner.NW,
        )

    if preset_id == "numbering_linear_rows":
        return replace(
            current,
            small_numbering_mode=SmallNumberingMode.LINEAR,
            small_numbering_direction=SmallNumberingDirection.BY_ROWS,
            small_numbering_start_corner=StartCorner.NW,
        )

    if preset_id == "numbering_linear_columns":
        return replace(
            current,
            small_numbering_mode=SmallNumberingMode.LINEAR,
            small_numbering_direction=SmallNumberingDirection.BY_COLUMNS,
            small_numbering_start_corner=StartCorner.NW,
        )

    if preset_id == "numbering_spiral_center":
        return replace(
            current,
            small_numbering_mode=SmallNumberingMode.SPIRAL_CENTER_OUT,
            small_spiral_direction=SpiralDirection.CLOCKWISE,
            small_numbering_start_corner=StartCorner.NW,
        )

    if preset_id == "numbering_spiral_edge":
        return replace(
            current,
            small_numbering_mode=SmallNumberingMode.SPIRAL_EDGE_IN,
            small_spiral_direction=SpiralDirection.CLOCKWISE,
            small_numbering_start_corner=StartCorner.NW,
        )

    if preset_id == "style_default":
        return replace(current, kml_style=KmlStyle())

    if preset_id == "style_big_palette":
        return replace(
            current,
            kml_style=KmlStyle(
                big_line_color="#000000",
                small_line_color="#000000",
                big_line_width=2,
                small_line_width=1,
                big_fill_mode=BigTileFillMode.BY_NUMBER,
                big_fill_opacity=35,
            ),
        )

    if preset_id == "style_small_fill":
        return replace(
            current,
            kml_style=KmlStyle(
                big_line_color="#000000",
                small_line_color="#000000",
                big_line_width=2,
                small_line_width=1,
                small_fill_enabled=True,
                small_fill_color="#90caf9",
                small_fill_opacity=25,
            ),
        )

    raise ValueError(f"Неизвестный пресет: {preset_id!r}.")


def normalize_project_path(path: str | Path) -> Path:
    result = Path(path).expanduser()
    name = result.name.lower()
    if name.endswith(PROJECT_EXTENSION):
        return result
    if result.suffix.lower() == ".json":
        return result.with_name(f"{result.stem}{PROJECT_EXTENSION}")
    return result.with_name(f"{result.name}{PROJECT_EXTENSION}")


def save_project_state(path: str | Path, state: ProjectState) -> Path:
    out_path = normalize_project_path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = project_state_to_dict(state)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def load_project_state(path: str | Path) -> ProjectState:
    project_path = Path(path).expanduser()
    try:
        data = json.loads(project_path.read_text(encoding="utf-8"))
        return project_state_from_dict(data)
    except JSONDecodeError as exc:
        raise ProjectFileError(f"Файл проекта поврежден или не является JSON: {exc.msg}.") from exc
    except OSError as exc:
        raise ProjectFileError(f"Не удалось прочитать файл проекта: {exc}.") from exc
    except (TypeError, ValueError) as exc:
        raise ProjectFileError(f"Не удалось открыть проект: {exc}.") from exc


def project_state_to_dict(state: ProjectState) -> dict[str, Any]:
    return {
        "schema": PROJECT_SCHEMA,
        "schema_version": PROJECT_SCHEMA_VERSION,
        "app_version": __version__,
        "coordinates": {
            "x_nw": state.coordinates.x_nw,
            "y_nw": state.coordinates.y_nw,
            "x_se": state.coordinates.x_se,
            "y_se": state.coordinates.y_se,
        },
        "options": grid_options_to_dict(state.options.normalized()),
        "export": {
            "folder": state.export_folder,
            "filename": state.export_filename,
        },
    }


def project_state_from_dict(data: object) -> ProjectState:
    source = _require_mapping(data, "Корень файла проекта")
    schema = source.get("schema")
    schema_version = source.get("schema_version")
    if schema != PROJECT_SCHEMA:
        raise ValueError("неподдерживаемый формат файла проекта")
    if schema_version != PROJECT_SCHEMA_VERSION:
        raise ValueError(f"неподдерживаемая версия файла проекта: {schema_version!r}")

    coordinates_data = _require_mapping(source.get("coordinates"), "Координаты")
    export_data = _require_mapping(source.get("export"), "Настройки экспорта")

    return ProjectState(
        coordinates=CoordinateState(
            x_nw=str(coordinates_data.get("x_nw", "")),
            y_nw=str(coordinates_data.get("y_nw", "")),
            x_se=str(coordinates_data.get("x_se", "")),
            y_se=str(coordinates_data.get("y_se", "")),
        ),
        options=grid_options_from_dict(source.get("options")),
        export_folder=str(export_data.get("folder", default_export_directory())),
        export_filename=str(export_data.get("filename", export_format_for_mode(ExportMode.KML).default_filename)),
    )


def grid_options_to_dict(options: GridOptions) -> dict[str, Any]:
    return {
        "include_1000": options.include_1000,
        "include_100": options.include_100,
        "snake_big": options.snake_big,
        "big_tile_names": [
            {"number": number, "name": name}
            for number, name in options.big_tile_names
        ],
        "small_numbering_mode": options.small_numbering_mode.value,
        "small_numbering_direction": options.small_numbering_direction.value,
        "small_numbering_start_corner": options.small_numbering_start_corner.value,
        "small_spiral_direction": options.small_spiral_direction.value,
        "rounding_mode": options.rounding_mode.value,
        "export_format_id": export_format_for_mode(options.export_mode).format_id,
        "export_mode": options.export_mode.value,
        "kml_style": kml_style_to_dict(options.kml_style.normalized()),
    }


def grid_options_from_dict(data: object) -> GridOptions:
    source = _require_mapping(data, "Настройки сетки")
    return GridOptions(
        include_1000=_bool_from_data(source, "include_1000", True),
        include_100=_bool_from_data(source, "include_100", True),
        snake_big=_bool_from_data(source, "snake_big", True),
        big_tile_names=_named_pairs_from_data(source.get("big_tile_names", ()), "name"),
        small_numbering_mode=SmallNumberingMode(source.get("small_numbering_mode", SmallNumberingMode.SNAKE.value)),
        small_numbering_direction=SmallNumberingDirection(
            source.get("small_numbering_direction", SmallNumberingDirection.BY_ROWS.value)
        ),
        small_numbering_start_corner=StartCorner(source.get("small_numbering_start_corner", StartCorner.NW.value)),
        small_spiral_direction=SpiralDirection(source.get("small_spiral_direction", SpiralDirection.CLOCKWISE.value)),
        rounding_mode=RoundingMode(source.get("rounding_mode", RoundingMode.IN.value)),
        export_mode=_export_mode_from_project_options(source),
        kml_style=kml_style_from_dict(source.get("kml_style", {})),
    ).normalized()


def kml_style_to_dict(style: KmlStyle) -> dict[str, Any]:
    return {
        "big_line_color": style.big_line_color,
        "small_line_color": style.small_line_color,
        "big_line_width": style.big_line_width,
        "small_line_width": style.small_line_width,
        "big_fill_mode": style.big_fill_mode.value,
        "big_fill_color": style.big_fill_color,
        "big_fill_opacity": style.big_fill_opacity,
        "big_fill_palette": list(style.big_fill_palette),
        "custom_big_fill_colors": [
            {"number": number, "color": color}
            for number, color in style.custom_big_fill_colors
        ],
        "small_fill_enabled": style.small_fill_enabled,
        "small_fill_color": style.small_fill_color,
        "small_fill_opacity": style.small_fill_opacity,
    }


def kml_style_from_dict(data: object) -> KmlStyle:
    source = _require_mapping(data, "KML-стиль")
    return KmlStyle(
        big_line_color=str(source.get("big_line_color", "#000000")),
        small_line_color=str(source.get("small_line_color", "#000000")),
        big_line_width=int(source.get("big_line_width", 2)),
        small_line_width=int(source.get("small_line_width", 1)),
        big_fill_mode=BigTileFillMode(source.get("big_fill_mode", BigTileFillMode.NONE.value)),
        big_fill_color=str(source.get("big_fill_color", "#fdd835")),
        big_fill_opacity=int(source.get("big_fill_opacity", 35)),
        big_fill_palette=tuple(str(color) for color in _sequence_from_data(source.get("big_fill_palette", ()))),
        custom_big_fill_colors=_named_pairs_from_data(source.get("custom_big_fill_colors", ()), "color"),
        small_fill_enabled=_bool_from_data(source, "small_fill_enabled", False),
        small_fill_color=str(source.get("small_fill_color", "#90caf9")),
        small_fill_opacity=int(source.get("small_fill_opacity", 25)),
    ).normalized()


def _bool_from_data(source: Mapping[str, Any], key: str, default: bool) -> bool:
    value = source.get(key, default)
    if isinstance(value, bool):
        return value
    raise ValueError(f"{key}: ожидалось true/false.")


def _export_mode_from_project_options(source: Mapping[str, Any]) -> ExportMode:
    format_id = source.get("export_format_id")
    if format_id is not None:
        return export_format_by_id(str(format_id)).mode
    return ExportMode(source.get("export_mode", ExportMode.KML.value))


def _named_pairs_from_data(data: object, value_key: str) -> tuple[tuple[int, str], ...]:
    if isinstance(data, Mapping):
        return tuple((int(number), str(value)) for number, value in data.items())
    items = _sequence_from_data(data)
    pairs: list[tuple[int, str]] = []
    for item in items:
        if isinstance(item, Mapping):
            if "number" not in item or value_key not in item:
                raise ValueError(f"Некорректная запись списка: {item!r}")
            pairs.append((int(item["number"]), str(item[value_key])))
        elif isinstance(item, Sequence) and not isinstance(item, str) and len(item) == 2:
            number, value = item
            pairs.append((int(number), str(value)))
        else:
            raise ValueError(f"Некорректная запись списка: {item!r}")
    return tuple(pairs)


def _sequence_from_data(data: object) -> Sequence[Any]:
    if data is None:
        return ()
    if isinstance(data, str) or not isinstance(data, Sequence):
        raise ValueError(f"Ожидался список, получено: {type(data).__name__}.")
    return data


def _require_mapping(data: object, label: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise ValueError(f"{label}: ожидался объект JSON.")
    return data
