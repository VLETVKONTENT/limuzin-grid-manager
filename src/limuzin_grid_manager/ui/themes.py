from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication


SYSTEM_LIGHT_THEME_ID = "system/light"
DARK_THEME_ID = "dark"
HIGH_CONTRAST_THEME_ID = "high-contrast"
DEFAULT_THEME_ID = SYSTEM_LIGHT_THEME_ID


@dataclass(frozen=True)
class PreviewPalette:
    canvas_background: str
    grid_background: str
    grid_border: str
    message_text: str
    help_text: str
    big_label_text: str
    small_label_text: str
    selected_fill_rgba: tuple[int, int, int, int]
    selected_border: str


@dataclass(frozen=True)
class ThemeSpec:
    theme_id: str
    title: str
    description: str
    stylesheet: str
    preview_palette: PreviewPalette


def available_themes() -> tuple[ThemeSpec, ...]:
    return _THEMES


def normalize_theme_id(theme_id: object) -> str:
    if isinstance(theme_id, str) and theme_id in _THEME_BY_ID:
        return theme_id
    return DEFAULT_THEME_ID


def theme_by_id(theme_id: object) -> ThemeSpec:
    return _THEME_BY_ID[normalize_theme_id(theme_id)]


def apply_app_theme(app: QApplication, theme_id: object) -> ThemeSpec:
    theme = theme_by_id(theme_id)
    app.setStyleSheet(theme.stylesheet)
    return theme


def preview_palette_for_theme(theme_id: object) -> PreviewPalette:
    return theme_by_id(theme_id).preview_palette


def _stylesheet(
    *,
    text: str,
    window: str,
    panel: str,
    muted: str,
    field_text: str,
    border: str,
    input_background: str,
    button_background: str,
    button_text: str,
    button_border: str,
    selection_background: str,
    disabled: str,
) -> str:
    return f"""
    QMainWindow, QWidget {{
        color: {text};
        background: {window};
        font-size: 10.5pt;
    }}
    QLabel#Title {{
        font-size: 20pt;
        font-weight: 700;
    }}
    QLabel#Subtitle, QLabel#Hint, QLabel#Status {{
        color: {muted};
    }}
    QLabel#PanelTitle {{
        font-size: 13pt;
        font-weight: 700;
    }}
    QLabel#SectionTitle {{
        font-size: 11pt;
        font-weight: 700;
        margin-top: 8px;
    }}
    QLabel#FieldLabel {{
        color: {field_text};
        font-weight: 600;
        margin-top: 2px;
    }}
    QGroupBox {{
        background: {panel};
        border: 1px solid {border};
        border-radius: 6px;
        font-weight: 600;
        margin-top: 10px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        background: {window};
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }}
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QTableWidget {{
        background: {input_background};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px;
        selection-background-color: {selection_background};
    }}
    QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
        color: {disabled};
    }}
    QComboBox {{
        min-height: 30px;
        padding: 5px 34px 5px 8px;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 30px;
        border-left: 1px solid {border};
    }}
    QPushButton {{
        background: {button_background};
        color: {button_text};
        border: 1px solid {button_border};
        border-radius: 6px;
        padding: 8px 14px;
    }}
    QPushButton:disabled {{
        color: {disabled};
    }}
    QPushButton:hover:!disabled {{
        border-color: {selection_background};
    }}
    QTabWidget::pane {{
        border: 1px solid {border};
        border-radius: 6px;
    }}
    QTabBar::tab {{
        background: {panel};
        color: {text};
        border: 1px solid {border};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 12px;
    }}
    QTabBar::tab:selected {{
        background: {input_background};
        font-weight: 700;
    }}
    QScrollArea, QMenuBar, QMenu {{
        background: {window};
        color: {text};
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 4px 10px;
    }}
    QMenuBar::item:selected {{
        background: {input_background};
    }}
    QMenu::item {{
        padding: 6px 96px 6px 24px;
        min-width: 220px;
    }}
    QMenu::item:selected {{
        background: {selection_background};
        color: #ffffff;
    }}
    QMenu::separator {{
        height: 1px;
        background: {border};
        margin: 4px 10px;
    }}
    QProgressBar {{
        border: 1px solid {border};
        border-radius: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {selection_background};
        border-radius: 6px;
    }}
    """


_THEMES: tuple[ThemeSpec, ...] = (
    ThemeSpec(
        theme_id=SYSTEM_LIGHT_THEME_ID,
        title="Светлая",
        description="Стандартная светлая тема, близкая к прежнему виду приложения.",
        stylesheet=_stylesheet(
            text="#111820",
            window="#f7f9fc",
            panel="#ffffff",
            muted="#555555",
            field_text="#333333",
            border="#b8bec8",
            input_background="#ffffff",
            button_background="#f3f6fb",
            button_text="#111820",
            button_border="#b8bec8",
            selection_background="#1e88e5",
            disabled="#7a8493",
        ),
        preview_palette=PreviewPalette(
            canvas_background="#f7f9fc",
            grid_background="#ffffff",
            grid_border="#7f8793",
            message_text="#4b5563",
            help_text="#667085",
            big_label_text="#111820",
            small_label_text="#1d2733",
            selected_fill_rgba=(30, 136, 229, 28),
            selected_border="#1565c0",
        ),
    ),
    ThemeSpec(
        theme_id=DARK_THEME_ID,
        title="Темная",
        description="Темная тема для работы в слабом освещении.",
        stylesheet=_stylesheet(
            text="#e6edf5",
            window="#161b22",
            panel="#1f2630",
            muted="#a9b4c2",
            field_text="#d7e0ea",
            border="#445163",
            input_background="#0f141b",
            button_background="#263241",
            button_text="#e6edf5",
            button_border="#526174",
            selection_background="#42a5f5",
            disabled="#7d8794",
        ),
        preview_palette=PreviewPalette(
            canvas_background="#161b22",
            grid_background="#0f141b",
            grid_border="#66758a",
            message_text="#c4ceda",
            help_text="#a9b4c2",
            big_label_text="#ecf3fb",
            small_label_text="#dde8f4",
            selected_fill_rgba=(66, 165, 245, 54),
            selected_border="#90caf9",
        ),
    ),
    ThemeSpec(
        theme_id=HIGH_CONTRAST_THEME_ID,
        title="Контрастная",
        description="Высокий контраст для яркого света и слабых экранов.",
        stylesheet=_stylesheet(
            text="#000000",
            window="#ffffff",
            panel="#ffffff",
            muted="#000000",
            field_text="#000000",
            border="#000000",
            input_background="#ffffff",
            button_background="#ffffff",
            button_text="#000000",
            button_border="#000000",
            selection_background="#005fcc",
            disabled="#4d4d4d",
        ),
        preview_palette=PreviewPalette(
            canvas_background="#ffffff",
            grid_background="#ffffff",
            grid_border="#000000",
            message_text="#000000",
            help_text="#000000",
            big_label_text="#000000",
            small_label_text="#000000",
            selected_fill_rgba=(0, 95, 204, 72),
            selected_border="#000000",
        ),
    ),
)

_THEME_BY_ID = {theme.theme_id: theme for theme in _THEMES}
