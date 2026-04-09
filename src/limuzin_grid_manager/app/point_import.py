from __future__ import annotations

from dataclasses import dataclass

from limuzin_grid_manager.core.points import PointRecord


@dataclass(frozen=True)
class PointImportError:
    source_row: int
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_row", int(self.source_row))
        object.__setattr__(self, "message", str(self.message).strip())


@dataclass(frozen=True)
class PointImportResult:
    sheet_name: str
    records: tuple[PointRecord, ...]
    errors: tuple[PointImportError, ...]
    total_rows: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "sheet_name", str(self.sheet_name).strip())
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "total_rows", max(0, int(self.total_rows)))

    @property
    def is_exportable(self) -> bool:
        return bool(self.records) and not self.errors

    @property
    def summary(self) -> str:
        lines = [
            f"Лист: {self.sheet_name or 'без имени'}",
            f"Строк данных: {self.total_rows}.",
            f"Корректных точек: {len(self.records)}.",
        ]
        if self.errors:
            lines.append(f"Ошибок: {len(self.errors)}. Экспорт заблокирован.")
        else:
            lines.append("Ошибок нет. Экспорт доступен.")
        return "\n".join(lines)
