from __future__ import annotations

import json

import pytest

from limuzin_grid_manager.app.project import (
    CoordinateState,
    ProjectFileError,
    ProjectState,
    apply_project_preset,
    load_project_state,
    normalize_project_path,
    save_project_state,
)
from limuzin_grid_manager.core.models import (
    BigTileFillMode,
    ExportMode,
    GridOptions,
    KmlStyle,
    RoundingMode,
    SmallNumberingDirection,
    SmallNumberingMode,
    StartCorner,
)


def test_project_state_roundtrip_preserves_settings(tmp_path) -> None:
    state = ProjectState(
        coordinates=CoordinateState(
            x_nw="5 662 000",
            y_nw="6 650 000",
            x_se="5 660 000",
            y_se="6 652 000",
        ),
        options=GridOptions(
            include_1000=True,
            include_100=True,
            snake_big=False,
            big_tile_names=((2, "Север"),),
            small_numbering_mode=SmallNumberingMode.LINEAR,
            small_numbering_direction=SmallNumberingDirection.BY_COLUMNS,
            small_numbering_start_corner=StartCorner.SE,
            rounding_mode=RoundingMode.OUT,
            export_mode=ExportMode.ZIP,
            kml_style=KmlStyle(
                big_fill_mode=BigTileFillMode.CUSTOM,
                big_fill_color="#43a047",
                custom_big_fill_colors=((2, "#1e88e5"),),
                small_fill_enabled=True,
                small_fill_color="#90caf9",
            ),
        ),
        export_folder=str(tmp_path),
        export_filename="tiles.zip",
    )

    saved_path = save_project_state(tmp_path / "test-project", state)
    loaded = load_project_state(saved_path)

    assert saved_path.name == "test-project.lgm.json"
    assert loaded.coordinates == state.coordinates
    assert loaded.export_folder == str(tmp_path)
    assert loaded.export_filename == "tiles.zip"
    assert loaded.options.include_1000 is True
    assert loaded.options.snake_big is False
    assert loaded.options.big_tile_names == ((2, "Север"),)
    assert loaded.options.small_numbering_mode == SmallNumberingMode.LINEAR
    assert loaded.options.small_numbering_direction == SmallNumberingDirection.BY_COLUMNS
    assert loaded.options.small_numbering_start_corner == StartCorner.SE
    assert loaded.options.rounding_mode == RoundingMode.OUT
    assert loaded.options.export_mode == ExportMode.ZIP
    assert loaded.options.kml_style.big_fill_mode == BigTileFillMode.CUSTOM
    assert loaded.options.kml_style.custom_big_fill_colors == ((2, "#1e88e5"),)
    assert loaded.options.kml_style.small_fill_enabled is True


def test_project_path_normalization_prefers_lgm_json(tmp_path) -> None:
    assert normalize_project_path(tmp_path / "grid").name == "grid.lgm.json"
    assert normalize_project_path(tmp_path / "grid.json").name == "grid.lgm.json"
    assert normalize_project_path(tmp_path / "grid.lgm.json").name == "grid.lgm.json"


def test_project_loader_reports_unknown_schema(tmp_path) -> None:
    path = tmp_path / "old.json"
    path.write_text('{"schema": "old"}', encoding="utf-8")

    with pytest.raises(ProjectFileError, match="неподдерживаемый формат"):
        load_project_state(path)


def test_project_loader_rejects_string_booleans(tmp_path) -> None:
    path = tmp_path / "string-bool.lgm.json"
    path.write_text(
        json.dumps(
            {
                "schema": "limuzin-grid-manager-project",
                "schema_version": 1,
                "coordinates": {},
                "options": {
                    "include_1000": "false",
                },
                "export": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProjectFileError, match="include_1000"):
        load_project_state(path)


def test_project_loader_reports_malformed_named_pairs(tmp_path) -> None:
    path = tmp_path / "bad-pairs.lgm.json"
    path.write_text(
        json.dumps(
            {
                "schema": "limuzin-grid-manager-project",
                "schema_version": 1,
                "coordinates": {},
                "options": {
                    "big_tile_names": [{"name": "Север"}],
                },
                "export": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProjectFileError, match="Некорректная запись списка"):
        load_project_state(path)


def test_project_preset_applies_numbering_without_resetting_style() -> None:
    options = GridOptions(
        kml_style=KmlStyle(big_fill_mode=BigTileFillMode.BY_NUMBER),
    )

    updated = apply_project_preset("numbering_linear_columns", options)

    assert updated.small_numbering_mode == SmallNumberingMode.LINEAR
    assert updated.small_numbering_direction == SmallNumberingDirection.BY_COLUMNS
    assert updated.kml_style.big_fill_mode == BigTileFillMode.BY_NUMBER


def test_legacy_preset_restores_v001_style() -> None:
    updated = apply_project_preset(
        "legacy_v001",
        GridOptions(
            include_1000=False,
            include_100=True,
            export_mode=ExportMode.ZIP,
            kml_style=KmlStyle(big_fill_mode=BigTileFillMode.BY_NUMBER),
        ),
    )

    assert updated.include_1000 is True
    assert updated.include_100 is True
    assert updated.export_mode == ExportMode.KML
    assert updated.kml_style.big_fill_mode == BigTileFillMode.NONE
