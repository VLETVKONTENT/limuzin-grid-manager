from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from limuzin_grid_manager.core.geometry import snake_index
from limuzin_grid_manager.core.models import (
    BigTileFillMode,
    GridOptions,
    GridStats,
    KmlStyle,
    SmallNumberingMode,
)
from limuzin_grid_manager.core.numbering import small_number
from limuzin_grid_manager.ui.themes import DEFAULT_THEME_ID, PreviewPalette, preview_palette_for_theme


@dataclass(frozen=True)
class _PreviewShape:
    rows: int
    cols: int
    step: int
    is_big_grid: bool

    @property
    def width_m(self) -> int:
        return self.cols * self.step

    @property
    def height_m(self) -> int:
        return self.rows * self.step


class GridPreviewWidget(QWidget):
    selectionChanged = Signal(int)

    _MARGIN = 26
    _MIN_ZOOM = 0.05
    _MAX_ZOOM = 1200.0
    _MAX_LABELS = 450
    _MAX_DENSE_FILLS = 2500
    _MAX_SPIRAL_LABEL_CELLS = 10000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._stats: GridStats | None = None
        self._options = GridOptions().normalized()
        self._message = "Введите координаты, чтобы увидеть предпросмотр."
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._selected_big_number = 0
        self._press_pos: QPointF | None = None
        self._press_pan = QPointF(0.0, 0.0)
        self._is_dragging = False
        self._palette: PreviewPalette = preview_palette_for_theme(DEFAULT_THEME_ID)

    def set_preview(self, stats: GridStats, options: GridOptions) -> None:
        self._stats = stats
        self._options = options.normalized()
        self._message = ""
        self._normalize_selection()
        self.update()

    def set_message(self, message: str) -> None:
        self._stats = None
        self._message = message
        self._set_selected_big_number(0)
        self.update()

    def set_theme(self, theme_id: str) -> None:
        self._palette = preview_palette_for_theme(theme_id)
        self.update()

    def selected_big_number(self) -> int:
        return self._selected_big_number

    def fit_to_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self.update()

    def focus_selected_big_tile(self) -> None:
        shape = self._shape()
        if shape is None or not shape.is_big_grid or self._selected_big_number <= 0:
            return

        row_col = self._big_row_col_from_number(self._selected_big_number, shape)
        if row_col is None:
            return

        row, col = row_col
        self._focus_world_rect(shape, col * shape.step, row * shape.step, shape.step, shape.step)

    def zoom_in(self) -> None:
        self._zoom_at(QPointF(self.width() / 2, self.height() / 2), 1.25)

    def zoom_out(self) -> None:
        self._zoom_at(QPointF(self.width() / 2, self.height() / 2), 0.8)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(self._palette.canvas_background))

        shape = self._shape()
        if shape is None:
            self._draw_message(painter, self._message)
            return

        scale, offset = self._scale_and_offset(shape)
        area = self._world_rect(shape, scale, offset, 0, 0, shape.width_m, shape.height_m)
        painter.fillRect(area, QColor(self._palette.grid_background))
        painter.setPen(QPen(QColor(self._palette.grid_border), 1))
        painter.drawRect(area)

        if shape.is_big_grid:
            self._draw_big_grid(painter, shape, scale, offset)
        else:
            self._draw_small_grid(painter, shape, scale, offset)

        self._draw_help(painter, shape)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if self._shape() is None:
            return
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom_at(event.position(), factor)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._shape() is not None:
            self._press_pos = event.position()
            self._press_pan = QPointF(self._pan)
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._press_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.position() - self._press_pos
            if abs(delta.x()) + abs(delta.y()) > 4:
                self._is_dragging = True
            if self._is_dragging:
                self._pan = self._press_pan + delta
                self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            if not self._is_dragging:
                self._select_big_tile_at(event.position())
            self._press_pos = None
            self._is_dragging = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.update()

    def _shape(self) -> _PreviewShape | None:
        if self._stats is None:
            return None
        if self._options.include_1000 and self._stats.big_grid is not None:
            return _PreviewShape(self._stats.big_grid.rows, self._stats.big_grid.cols, 1000, True)
        if self._options.include_100 and self._stats.small_grid is not None:
            return _PreviewShape(self._stats.small_grid.rows, self._stats.small_grid.cols, 100, False)
        return None

    def _normalize_selection(self) -> None:
        shape = self._shape()
        if shape is None or not shape.is_big_grid:
            self._set_selected_big_number(0)
            return
        total = shape.rows * shape.cols
        selected = self._selected_big_number
        if selected <= 0 or selected > total:
            selected = 1
        self._set_selected_big_number(selected)

    def _set_selected_big_number(self, number: int) -> None:
        if self._selected_big_number == number:
            return
        self._selected_big_number = number
        self.selectionChanged.emit(number)

    def _scale_and_offset(self, shape: _PreviewShape) -> tuple[float, QPointF]:
        base_scale = self._base_scale(shape)
        scale = base_scale * self._zoom
        offset = QPointF(
            (self.width() - shape.width_m * scale) / 2 + self._pan.x(),
            (self.height() - shape.height_m * scale) / 2 + self._pan.y(),
        )
        return scale, offset

    def _base_scale(self, shape: _PreviewShape) -> float:
        usable_width = max(1, self.width() - self._MARGIN * 2)
        usable_height = max(1, self.height() - self._MARGIN * 2)
        return max(0.000001, min(usable_width / max(1, shape.width_m), usable_height / max(1, shape.height_m)))

    def _world_to_screen(self, scale: float, offset: QPointF, x: float, y: float) -> QPointF:
        return QPointF(offset.x() + x * scale, offset.y() + y * scale)

    def _screen_to_world(self, shape: _PreviewShape, point: QPointF) -> QPointF:
        scale, offset = self._scale_and_offset(shape)
        return QPointF((point.x() - offset.x()) / scale, (point.y() - offset.y()) / scale)

    def _world_rect(
        self,
        shape: _PreviewShape,
        scale: float,
        offset: QPointF,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> QRectF:
        del shape
        return QRectF(
            self._world_to_screen(scale, offset, x, y),
            self._world_to_screen(scale, offset, x + width, y + height),
        ).normalized()

    def _focus_world_rect(self, shape: _PreviewShape, x: float, y: float, width: float, height: float) -> None:
        base_scale = self._base_scale(shape)
        target_scale = min(
            max(1, self.width() - self._MARGIN * 2) / max(1.0, width),
            max(1, self.height() - self._MARGIN * 2) / max(1.0, height),
        )
        self._zoom = _clamp(target_scale / base_scale, self._MIN_ZOOM, self._MAX_ZOOM)

        scale = base_scale * self._zoom
        offset_without_pan = QPointF(
            (self.width() - shape.width_m * scale) / 2,
            (self.height() - shape.height_m * scale) / 2,
        )
        target_center = self._world_to_screen(scale, offset_without_pan, x + width / 2, y + height / 2)
        self._pan = QPointF(self.width() / 2 - target_center.x(), self.height() / 2 - target_center.y())
        self.update()

    def _zoom_at(self, point: QPointF, factor: float) -> None:
        shape = self._shape()
        if shape is None:
            return

        before = self._screen_to_world(shape, point)
        self._zoom = _clamp(self._zoom * factor, self._MIN_ZOOM, self._MAX_ZOOM)
        scale, offset = self._scale_and_offset(shape)
        after_screen = self._world_to_screen(scale, offset, before.x(), before.y())
        self._pan += point - after_screen
        self.update()

    def _visible_cell_range(self, shape: _PreviewShape, scale: float, offset: QPointF) -> tuple[int, int, int, int]:
        left = (0 - offset.x()) / scale
        right = (self.width() - offset.x()) / scale
        top = (0 - offset.y()) / scale
        bottom = (self.height() - offset.y()) / scale

        col_start = max(0, floor(min(left, right) / shape.step) - 1)
        col_stop = min(shape.cols, ceil(max(left, right) / shape.step) + 1)
        row_start = max(0, floor(min(top, bottom) / shape.step) - 1)
        row_stop = min(shape.rows, ceil(max(top, bottom) / shape.step) + 1)
        return row_start, row_stop, col_start, col_stop

    def _draw_big_grid(self, painter: QPainter, shape: _PreviewShape, scale: float, offset: QPointF) -> None:
        style = self._options.kml_style.normalized()
        cell_px = shape.step * scale
        self._draw_big_fills(painter, shape, scale, offset, cell_px, style)
        self._draw_grid_lines(painter, shape, scale, offset, style.big_line_color, style.big_line_width, cell_px)
        self._draw_big_labels(painter, shape, scale, offset, cell_px)
        self._draw_selected_big_tile(painter, shape, scale, offset)

        if self._options.include_100:
            self._draw_selected_small_grid(painter, shape, scale, offset)

    def _draw_small_grid(self, painter: QPainter, shape: _PreviewShape, scale: float, offset: QPointF) -> None:
        style = self._options.kml_style.normalized()
        cell_px = shape.step * scale
        self._draw_small_fills(painter, shape, scale, offset, cell_px, style)
        self._draw_grid_lines(painter, shape, scale, offset, style.small_line_color, style.small_line_width, cell_px)
        self._draw_small_labels(painter, shape, scale, offset, cell_px)

    def _draw_big_fills(
        self,
        painter: QPainter,
        shape: _PreviewShape,
        scale: float,
        offset: QPointF,
        cell_px: float,
        style: KmlStyle,
    ) -> None:
        if style.big_fill_mode == BigTileFillMode.NONE or style.big_fill_opacity <= 0:
            return

        row_start, row_stop, col_start, col_stop = self._visible_cell_range(shape, scale, offset)
        visible_count = max(0, row_stop - row_start) * max(0, col_stop - col_start)
        if visible_count > self._MAX_DENSE_FILLS and cell_px < 8:
            return

        for row in range(row_start, row_stop):
            for col in range(col_start, col_stop):
                number = _big_number_for_cell(row, col, shape.cols, self._options.snake_big)
                fill_color = _big_tile_fill_color(number, style)
                if fill_color is None:
                    continue
                rect = self._world_rect(shape, scale, offset, col * shape.step, row * shape.step, shape.step, shape.step)
                painter.fillRect(rect, _qcolor_with_opacity(fill_color, style.big_fill_opacity))

    def _draw_small_fills(
        self,
        painter: QPainter,
        shape: _PreviewShape,
        scale: float,
        offset: QPointF,
        cell_px: float,
        style: KmlStyle,
    ) -> None:
        if not style.small_fill_enabled or style.small_fill_opacity <= 0:
            return

        row_start, row_stop, col_start, col_stop = self._visible_cell_range(shape, scale, offset)
        visible_count = max(0, row_stop - row_start) * max(0, col_stop - col_start)
        if visible_count > self._MAX_DENSE_FILLS and cell_px < 8:
            return

        color = _qcolor_with_opacity(style.small_fill_color, style.small_fill_opacity)
        for row in range(row_start, row_stop):
            for col in range(col_start, col_stop):
                rect = self._world_rect(shape, scale, offset, col * shape.step, row * shape.step, shape.step, shape.step)
                painter.fillRect(rect, color)

    def _draw_grid_lines(
        self,
        painter: QPainter,
        shape: _PreviewShape,
        scale: float,
        offset: QPointF,
        color: str,
        width: int,
        cell_px: float,
    ) -> None:
        row_start, row_stop, col_start, col_stop = self._visible_cell_range(shape, scale, offset)
        stride = _line_stride(cell_px)
        pen_color = QColor(color)
        if cell_px < 4:
            pen_color.setAlpha(150)
        painter.setPen(QPen(pen_color, max(1, min(4, int(width)))))

        col_lines = list(range(col_start, col_stop + 1, stride))
        row_lines = list(range(row_start, row_stop + 1, stride))
        if shape.cols not in col_lines and col_start <= shape.cols <= col_stop:
            col_lines.append(shape.cols)
        if shape.rows not in row_lines and row_start <= shape.rows <= row_stop:
            row_lines.append(shape.rows)

        for col in col_lines:
            x = col * shape.step
            painter.drawLine(
                self._world_to_screen(scale, offset, x, 0),
                self._world_to_screen(scale, offset, x, shape.height_m),
            )
        for row in row_lines:
            y = row * shape.step
            painter.drawLine(
                self._world_to_screen(scale, offset, 0, y),
                self._world_to_screen(scale, offset, shape.width_m, y),
            )

    def _draw_big_labels(
        self,
        painter: QPainter,
        shape: _PreviewShape,
        scale: float,
        offset: QPointF,
        cell_px: float,
    ) -> None:
        row_start, row_stop, col_start, col_stop = self._visible_cell_range(shape, scale, offset)
        visible_count = max(0, row_stop - row_start) * max(0, col_stop - col_start)
        if cell_px < 30 or visible_count > self._MAX_LABELS:
            return

        painter.setPen(QColor(self._palette.big_label_text))
        painter.setFont(_label_font(painter, cell_px, 7, 12))
        names = dict(self._options.big_tile_names)
        for row in range(row_start, row_stop):
            for col in range(col_start, col_stop):
                number = _big_number_for_cell(row, col, shape.cols, self._options.snake_big)
                name = names.get(number)
                text = f"{number:03d}"
                if name and cell_px >= 78:
                    text = f"{number:03d}\n{_short_text(name, 22)}"
                rect = self._world_rect(shape, scale, offset, col * shape.step, row * shape.step, shape.step, shape.step)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

    def _draw_small_labels(
        self,
        painter: QPainter,
        shape: _PreviewShape,
        scale: float,
        offset: QPointF,
        cell_px: float,
    ) -> None:
        row_start, row_stop, col_start, col_stop = self._visible_cell_range(shape, scale, offset)
        visible_count = max(0, row_stop - row_start) * max(0, col_stop - col_start)
        if cell_px < 20 or visible_count > self._MAX_LABELS:
            return
        if _small_numbering_is_spiral(self._options) and shape.rows * shape.cols > self._MAX_SPIRAL_LABEL_CELLS:
            return

        painter.setPen(QColor(self._palette.small_label_text))
        painter.setFont(_label_font(painter, cell_px, 6, 10))
        for row in range(row_start, row_stop):
            for col in range(col_start, col_stop):
                number = small_number(
                    row,
                    col,
                    shape.rows,
                    shape.cols,
                    self._options.small_numbering_mode,
                    self._options.small_numbering_direction,
                    self._options.small_numbering_start_corner,
                    self._options.small_spiral_direction,
                )
                rect = self._world_rect(shape, scale, offset, col * shape.step, row * shape.step, shape.step, shape.step)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(number))

    def _draw_selected_big_tile(
        self,
        painter: QPainter,
        shape: _PreviewShape,
        scale: float,
        offset: QPointF,
    ) -> None:
        row_col = self._big_row_col_from_number(self._selected_big_number, shape)
        if row_col is None:
            return

        row, col = row_col
        rect = self._world_rect(shape, scale, offset, col * shape.step, row * shape.step, shape.step, shape.step)
        painter.fillRect(rect, QColor(*self._palette.selected_fill_rgba))
        painter.setPen(QPen(QColor(self._palette.selected_border), 3))
        painter.drawRect(rect)

    def _draw_selected_small_grid(
        self,
        painter: QPainter,
        shape: _PreviewShape,
        scale: float,
        offset: QPointF,
    ) -> None:
        row_col = self._big_row_col_from_number(self._selected_big_number, shape)
        if row_col is None:
            return

        row, col = row_col
        style = self._options.kml_style.normalized()
        x0 = col * shape.step
        y0 = row * shape.step
        small_step = shape.step / 10
        small_px = small_step * scale

        if style.small_fill_enabled and style.small_fill_opacity > 0 and small_px >= 2:
            fill = _qcolor_with_opacity(style.small_fill_color, style.small_fill_opacity)
            for small_row in range(10):
                for small_col in range(10):
                    rect = self._world_rect(
                        shape,
                        scale,
                        offset,
                        x0 + small_col * small_step,
                        y0 + small_row * small_step,
                        small_step,
                        small_step,
                    )
                    painter.fillRect(rect, fill)

        painter.setPen(QPen(QColor(style.small_line_color), max(1, min(3, style.small_line_width))))
        for index in range(11):
            x = x0 + index * small_step
            y = y0 + index * small_step
            painter.drawLine(
                self._world_to_screen(scale, offset, x, y0),
                self._world_to_screen(scale, offset, x, y0 + shape.step),
            )
            painter.drawLine(
                self._world_to_screen(scale, offset, x0, y),
                self._world_to_screen(scale, offset, x0 + shape.step, y),
            )

        if small_px < 18:
            return

        painter.setPen(QColor(self._palette.small_label_text))
        painter.setFont(_label_font(painter, small_px, 6, 9))
        for small_row in range(10):
            for small_col in range(10):
                number = small_number(
                    small_row,
                    small_col,
                    10,
                    10,
                    self._options.small_numbering_mode,
                    self._options.small_numbering_direction,
                    self._options.small_numbering_start_corner,
                    self._options.small_spiral_direction,
                )
                rect = self._world_rect(
                    shape,
                    scale,
                    offset,
                    x0 + small_col * small_step,
                    y0 + small_row * small_step,
                    small_step,
                    small_step,
                )
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(number))

    def _draw_message(self, painter: QPainter, message: str) -> None:
        painter.setPen(QColor(self._palette.message_text))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        rect = QRectF(24, 24, max(1, self.width() - 48), max(1, self.height() - 48))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, message)

    def _draw_help(self, painter: QPainter, shape: _PreviewShape) -> None:
        if self.width() < 360 or self.height() < 160:
            return
        text = "Колесо - масштаб, перетаскивание - сдвиг"
        if shape.is_big_grid:
            text += ", клик - выбрать 1000x1000"
        painter.setPen(QColor(self._palette.help_text))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(12, self.height() - 12, text)

    def _select_big_tile_at(self, point: QPointF) -> None:
        shape = self._shape()
        if shape is None or not shape.is_big_grid:
            return

        world = self._screen_to_world(shape, point)
        col = floor(world.x() / shape.step)
        row = floor(world.y() / shape.step)
        if 0 <= row < shape.rows and 0 <= col < shape.cols:
            self._set_selected_big_number(_big_number_for_cell(row, col, shape.cols, self._options.snake_big))
            self.update()

    def _big_row_col_from_number(self, number: int, shape: _PreviewShape) -> tuple[int, int] | None:
        if not shape.is_big_grid or number <= 0 or number > shape.rows * shape.cols:
            return None
        index = number - 1
        row = index // shape.cols
        col = index % shape.cols
        if self._options.snake_big and row % 2 == 1:
            col = shape.cols - 1 - col
        return row, col


def _line_stride(cell_px: float) -> int:
    if cell_px <= 0:
        return 1
    return max(1, ceil(5 / cell_px))


def _label_font(painter: QPainter, cell_px: float, min_size: int, max_size: int) -> QFont:
    font = QFont(painter.font())
    font.setPointSize(max(min_size, min(max_size, int(cell_px / 4))))
    return font


def _small_numbering_is_spiral(options: GridOptions) -> bool:
    return options.small_numbering_mode in (
        SmallNumberingMode.SPIRAL_CENTER_OUT,
        SmallNumberingMode.SPIRAL_EDGE_IN,
    )


def _big_number_for_cell(row: int, col: int, cols: int, snake_big: bool) -> int:
    index = snake_index(row, col, cols) if snake_big else row * cols + col
    return index + 1


def _big_tile_fill_color(big_num: int, style: KmlStyle) -> str | None:
    if style.big_fill_mode == BigTileFillMode.NONE or style.big_fill_opacity <= 0:
        return None
    if style.big_fill_mode == BigTileFillMode.SINGLE:
        return style.big_fill_color
    if style.big_fill_mode == BigTileFillMode.BY_NUMBER:
        return style.big_fill_palette[(big_num - 1) % len(style.big_fill_palette)]
    custom_colors = dict(style.custom_big_fill_colors)
    return custom_colors.get(big_num) or style.big_fill_color


def _qcolor_with_opacity(color: str, opacity_percent: int) -> QColor:
    result = QColor(color)
    result.setAlpha(max(0, min(255, int(max(0, min(100, opacity_percent)) * 255 / 100 + 0.5))))
    return result


def _short_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max(1, max_len - 1)] + "..."


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
