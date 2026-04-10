# ROADMAPv2.1: LIMUZIN GRID MANAGER v2.0 -> v2.1

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

В корне репозитория есть `PLANS.md`. Этот файл нужно поддерживать по правилам `PLANS.md`, но его роль - roadmap-уровень для перехода от стабильной версии `v2.0.0` к стабильной версии `v2.1.0`, а не одноразовый план реализации одной функции.

Этот roadmap не заменяет `ROADMAPv2.md`. `ROADMAPv2.md` остается живой историей пути к `v2.0.0`, а `ROADMAPv2.1.md` становится следующим живым документом для отдельного направления: импорта точек из Excel и экспорта point-KML для AlpineQuest.

## Purpose / Big Picture

Цель `v2.1` - добавить в LIMUZIN GRID MANAGER новый пользовательский сценарий, который не смешивается с генерацией сеток `1000x1000` и `100x100`: загрузку Excel-файла с точками и генерацию готового KML-файла для импорта в AlpineQuest.

После выполнения этой дорожной карты пользователь сможет в том же EXE открыть отдельное окно точек, выбрать `.xlsx` по шаблону `ФИО | Дата | Координаты`, увидеть сводку импорта, задать один общий цвет и прозрачность для всех точек и получить AlpineQuest-совместимый `.kml`, где каждая строка Excel превращается в отдельный `Placemark`.

Важно не только добавить новый экспорт, но и сохранить архитектурную чистоту `v2.0.0`. Генерация сеток и работа с точками должны развиваться независимо: общий EXE и общая тема интерфейса сохраняются, но point-flow не внедряется в `GridOptions`, `ExportMode`, `.lgm.json` или текущую вкладку `Экспорт`.

В начале реализации нужно считать зафиксированными следующие входные факты, подтвержденные по реальным образцам пользователя. Текущая стабильная версия приложения - `v2.0.0`. Образец Excel содержит лист `Лист1` с колонками `ФИО`, `Дата`, `Координаты`. Значение даты `46115` соответствует `03.04.2026`. Образец итогового KML содержит `Placemark`-точки с именем в `<name>`, датой в `description` и `ExtendedData/comment`, а цвет точки задается через `IconStyle/color`.

## Progress

- [x] 2026-04-09 Europe/Moscow: Прочитаны `PLANS.md`, `ROADMAPv2.md`, `GRIDBASE.md`, текущие `pyproject.toml`, `build_exe_windows.bat`, `ui/main_window.py`, `core/crs.py`, `core/kml.py`, `app/exporter.py`, `app/project.py` и набор тестов.
- [x] 2026-04-09 Europe/Moscow: Проверены реальные пользовательские образцы вне репозитория: `образец для excel.xlsx` и `пример итогового файла.kml`; подтверждены колонки `ФИО | Дата | Координаты`, Excel serial `46115 -> 03.04.2026`, структура `Placemark` и использование `IconStyle/color`.
- [x] 2026-04-09 Europe/Moscow: Подтверждено, что текущее главное окно приложения остается grid-ориентированным: вкладки `Предпросмотр`, `Проверка`, `Экспорт`; отдельное окно точек безопаснее, чем встраивание новой вкладки.
- [x] 2026-04-09 Europe/Moscow: Создан `ROADMAPv2.1.md` как самостоятельный living ExecPlan-roadmap для пути `v2.0.0 -> v2.1.0`.
- [x] 2026-04-09 Europe/Moscow: Реализован `v2.0.1`: добавлены `src/limuzin_grid_manager/core/points.py`, `src/limuzin_grid_manager/core/point_kml.py`, `src/limuzin_grid_manager/app/point_import.py` и `src/limuzin_grid_manager/app/point_exporter.py`; point-flow остается изолированным от `GridOptions`, `ExportMode`, `.lgm.json` и grid-UI.
- [x] 2026-04-09 Europe/Moscow: Для `v2.0.1` добавлен `tests/test_points.py`; `uv run --extra dev pytest` прошло с результатом `76 passed`, `uv run --extra dev python -m compileall src tests` завершился без ошибок.
- [x] 2026-04-09 Europe/Moscow: Пользователь вручную протестировал `v2.0.1` и подтвердил, что изменения работают; выполнены `uv lock --offline`, `uv run --offline --extra dev pytest`, `uv run --offline --extra dev python -m compileall src tests`, сборка EXE и smoke-запуск `dist/LIMUZIN_GRID_MANAGER.exe`.
- [x] 2026-04-10 Europe/Moscow: Реализован `v2.0.2`: в `pyproject.toml` добавлен `openpyxl`, в `src/limuzin_grid_manager/app/point_import.py` реализован `import_points_from_excel()` с поиском первого листа с данными, strict sample-first заголовком `ФИО | Дата | Координаты`, построчной валидацией и преобразованием `X/Y -> zone from Y -> pyproj(y, x) -> lon/lat`.
- [x] 2026-04-10 Europe/Moscow: Для `v2.0.2` расширен `tests/test_points.py`; `uv run --extra dev pytest tests\test_points.py` прошло с результатом `11 passed`, `uv run --extra dev python -m compileall src tests` завершился без ошибок.
- [x] 2026-04-10 Europe/Moscow: Пользователь вручную протестировал `v2.0.2` и подтвердил, что изменения работают; выполнены `uv lock --offline`, `uv run --offline --extra dev pytest`, `uv run --offline --extra dev python -m compileall src tests`, сборка EXE `2.0.2.0` и подготовка версии к публикации.
- [x] 2026-04-10 Europe/Moscow: Реализован `v2.0.3`: добавлено отдельное окно `Точки из Excel` в `src/limuzin_grid_manager/ui/points_window.py` с выбором `.xlsx`, сводкой импорта, таблицей точек, блоком ошибок, общим стилем точек, выбором пути `.kml` и локальными `QSettings`; в `src/limuzin_grid_manager/ui/main_window.py` добавлено меню `Инструменты -> Точки из Excel...` с повторным открытием того же окна без внедрения point-state в grid-flow.
- [x] 2026-04-10 Europe/Moscow: Для `v2.0.3` расширен `tests/test_ui.py`; `uv run --extra dev pytest tests\test_points.py tests\test_ui.py` прошло с результатом `15 passed`, `uv run --extra dev pytest` прошло с результатом `81 passed`, `uv run --extra dev python -m compileall src tests` завершился без ошибок.
- [ ] Реализация `v2.0.4`: безопасная запись point-KML через временный файл, отмена, полировка UX и EXE-готовность с новой Excel-зависимостью.
- [ ] Подготовка `v2.1.0`: синхронизация версий, обновление документации, офлайн-проверка, сборка EXE и ручной пользовательский тест.

## Surprises & Discoveries

- Observation: Образец Excel не хранит `X` и `Y` в отдельных колонках; обе координаты лежат в одной строке вида `х-5649764 y-6661612`.
  Evidence: при чтении `образец для excel.xlsx` лист `Лист1` содержит строки `['ФИО', 'Дата', 'Координаты']`, `['Мишарин Александр Витальевич', '46115', 'х-5649764 y-6661612']`, `['Педьков Михаил Иванович', '46115', 'х-5649800 y-6661934']`.

- Observation: В sample-строке координат дефис после `x/y` является разделителем образца, а не знаком минуса; иначе преобразование в WGS84 уводит точку в неверное полушарие.
  Evidence: `parse_point_coordinates("х-5649764 y-6661612") -> (5649764, 6661612)` дает `lon/lat`, совпадающие с эталонным sample KML в разумной погрешности, тогда как интерпретация этих чисел как отрицательных приводит к `lon=-47.543...`, `lat=-10.914...`.

- Observation: Образец даты в Excel реально приходит как serial, а не как готовая строка.
  Evidence: значение `46115` при интерпретации по Excel-эпохе `1899-12-30` дает `03.04.2026`, что совпадает с датой в образце KML.

- Observation: Эталонный KML пользователя - это point-KML, а не polygon/grid-KML. Он использует `Placemark` + `Point`, а не текущие прямоугольные `Polygon`.
  Evidence: в `пример итогового файла.kml` два `Placemark`, каждый содержит `<Point><coordinates>lon,lat</coordinates></Point>`, а не `Polygon`.

- Observation: В эталонном KML дата дублируется в двух местах: `description` и `ExtendedData/comment`.
  Evidence: каждый `Placemark` содержит `<description><![CDATA[<i>03.04.2026</i>]]></description>` и `<Data name="comment"><![CDATA[03.04.2026]]></Data>`.

- Observation: Цвет точки в образце задается не через текущий grid-`KmlStyle`, а через `IconStyle/color`.
  Evidence: в каждом `Placemark` образца есть inline `<Style><IconStyle><color>...</color></IconStyle></Style>`.

- Observation: Текущее главное окно приложения целиком собрано вокруг сеток, расчета области, grid-preview и grid-export.
  Evidence: `src/limuzin_grid_manager/ui/main_window.py` строит слева блоки координат, сеток, имен `1000x1000` и `Стиль KML`, а справа вкладки только `Предпросмотр`, `Проверка`, `Экспорт`.

- Observation: Текущая модель проекта `.lgm.json` завязана на `CoordinateState`, `GridOptions`, путь экспорта и имя файла, поэтому point-state не должен попадать в этот формат без лишней архитектурной связи.
  Evidence: `src/limuzin_grid_manager/app/project.py` сериализует только `coordinates`, `options` и `export`, а `GridOptions` содержит исключительно grid-настройки.

- Observation: Текущая runtime-конфигурация не умеет читать `.xlsx`.
  Evidence: `pyproject.toml` содержит только `PySide6` и `pyproj` в runtime dependencies; Excel-библиотек пока нет.

- Observation: В этой среде удобнее находить пользовательские sample-файлы через PowerShell, чем через прямые литералы путей в inline Python, потому что Unicode-имена файлов могут ломать наивные строковые литералы.
  Evidence: прямое открытие образцов по вручную набранному пути завершалось `OSError: [Errno 22] Invalid argument`, а получение полного пути через `Get-ChildItem` и передачу через environment variable сработало.

- Observation: Foundation-слой точек удалось ввести без раннего подключения `openpyxl` и без изменений runtime-UI.
  Evidence: `v2.0.1` ограничился новыми `core/app`-модулями и тестами; полный прогон `pytest` дал `76 passed`, при этом `pyproject.toml` пока не получил Excel-зависимость и `ui/main_window.py` не менялся.

- Observation: Точное `lon/lat` из `pyproj` может немного отличаться в последних знаках от вручную зафиксированного эталона, поэтому для milestone `v2.0.2` нужна проверка с разумным tolerance, а не побайтное сравнение float-значений.
  Evidence: `pytest.approx(..., abs=1e-7)` покрывает расхождение между sample-значением `35.29845459878114,50.955512683199146` и расчетом текущей сборки `35.29845459800664,50.95551264506717`, не меняя географический смысл точки.

- Observation: Separate window хорошо ложится на текущую архитектуру, если `MainWindow` хранит одну живую ссылку и повторно поднимает уже созданный `PointsWindow`, а не пересоздает его и не расширяет grid-вкладки.
  Evidence: `tests/test_ui.py` открывает `MainWindow`, вызывает действие `Инструменты -> Точки из Excel...`, получает `PointsWindow`, загружает sample workbook и подтверждает, что список вкладок остается `Предпросмотр`, `Проверка`, `Экспорт`.

## Decision Log

- Decision: Целевой крупный стабильный релиз этого roadmap - `v2.1.0`, но промежуточные patch-версии `v2.0.x` могут отдельно фиксироваться как принятые стабильные релизы после ручного теста пользователя и офлайн-релизной проверки.
  Rationale: Пользователь хочет пошаговый путь от текущей стабильной `v2.0.0` к следующей стабильной версии, а patch-версии подходят для инкрементального внедрения новой функции без обещания стабильности на каждом промежуточном шаге.
  Date/Author: 2026-04-09, Codex.

- Decision: Стабильная `v2.1.0` поддерживает только `.xlsx` и только sample-first шаблон `ФИО | Дата | Координаты`.
  Rationale: Это покрывает реальную пользовательскую задачу и позволяет сделать надежную реализацию без преждевременного ухода в мастер сопоставления колонок, `.xls` или произвольные табличные схемы.
  Date/Author: 2026-04-09, Codex.

- Decision: Новый сценарий точек реализуется как отдельное top-level окно, открываемое через `Инструменты -> Точки из Excel...`, а не как новая вкладка в `MainWindow`.
  Rationale: Пользователь явно попросил отдельное окно, не связанное с генерацией сеток, а текущая структура `MainWindow` уже является grid-центричной и не выигрывает от смешивания двух независимых сценариев.
  Date/Author: 2026-04-09, Codex.

- Decision: Point-flow не внедряется в `GridOptions`, `ExportMode`, `ProjectState` и `.lgm.json`.
  Rationale: Это сохраняет независимость доработок сеток и точек и не размывает текущую модель проекта, которая относится только к расчету области и экспортам сетки.
  Date/Author: 2026-04-09, Codex.

- Decision: Для `v2.1.0` используется один общий стиль точек: цвет `#RRGGBB` и прозрачность `0..100` для всех импортированных строк.
  Rationale: Пользователь явно обозначил потребность в управлении цветом и прозрачностью точек, но не просил per-row стиль; единый стиль дает простую и надежную первую версию окна точек.
  Date/Author: 2026-04-09, Codex.

- Decision: Цвет точки в KML кодируется в том же формате `aabbggrr`, что и grid-KML, но через отдельную point-style модель, а не через пользовательское API `KmlStyle`.
  Rationale: Нужно сохранить согласованность KML-кодирования внутри проекта, не связывая point-flow с настройками линий и заливки сетки.
  Date/Author: 2026-04-09, Codex.

- Decision: Point-KML writer должен писать AlpineQuest-совместимые `Placemark`-точки с inline `<Style><IconStyle><color>...</color></IconStyle></Style>` внутри каждого `Placemark`.
  Rationale: Это ближе всего к фактическому образцу пользователя и снимает лишнюю сложность вокруг общих style id и `styleUrl`, которые для этой задачи не дают пользы.
  Date/Author: 2026-04-09, Codex.

- Decision: При импорте Excel первая невалидная строка не прерывает анализ; окно собирает все ошибки по строкам, но экспорт остается заблокированным, пока ошибки не устранены.
  Rationale: Пользователю полезнее увидеть полный список проблем за один проход, но экспорт не должен молча создавать частичный KML.
  Date/Author: 2026-04-09, Codex.

- Decision: `openpyxl` добавляется как runtime dependency, а загрузка workbook выполняется через `load_workbook(..., read_only=True, data_only=True)`.
  Rationale: `openpyxl` является стандартным решением для `.xlsx` в Python, а read-only/data-only режимы подходят для безопасного и предсказуемого чтения шаблонной таблицы без формул и записи обратно.
  Date/Author: 2026-04-09, Codex.

- Decision: Первая рабочая таблица определяется как первый лист workbook с хотя бы одной непустой строкой; первая непустая строка на этом листе считается заголовком.
  Rationale: Это соответствует формулировке "первая рабочая таблица с данными" и оставляет предсказуемое поведение без ручного выбора листа в `v2.1.0`.
  Date/Author: 2026-04-09, Codex.

- Decision: Координатная строка считается валидной только тогда, когда после нормализации в ней обнаруживаются ровно два целочисленных числа; первое число интерпретируется как `X`, второе как `Y`.
  Rationale: Такой контракт покрывает sample-формат `х-5649764 y-6661612`, устойчив к регистру и кириллической/латинской букве, но не допускает двусмысленный ввод.
  Date/Author: 2026-04-09, Codex.

- Decision: В sample-first формате `х-5649764 y-6661612` дефис после метки оси трактуется как разделитель `x-`/`y-`, а не как знак отрицательного числа; отрицательные значения допускаются только в явной форме вроде `x=-5649764 y=-6661612` или в unlabeled fallback.
  Rationale: Только такая интерпретация согласуется с реальным sample workbook и эталонным point-KML пользователя; иначе `lon/lat` оказываются в неверном полушарии и milestone `v2.0.2` не достигает цели совместимости с AlpineQuest.
  Date/Author: 2026-04-10, Codex.

- Decision: `PointImportResult` и `PointImportError` вводятся уже в `v2.0.1`, хотя чтение workbook остается задачей `v2.0.2`.
  Rationale: Это фиксирует доменный контракт между core, будущим importer и будущим окном точек, не добавляя `openpyxl` и не смешивая milestone-этапы.
  Date/Author: 2026-04-09, Codex.

- Decision: `v2.0.1` фиксируется как рабочая версия в `pyproject.toml`, `src/limuzin_grid_manager/__init__.py`, `version_info.txt` и `versions/`, но последней принятой стабильной версией остается `v2.0.0`.
  Rationale: milestone выполнен и проверен автоматическими тестами, однако roadmap прямо говорит, что стабильным релизом этого направления станет только `v2.1.0` после следующих этапов и ручного пользовательского теста.
  Date/Author: 2026-04-09, Codex.

- Decision: Дата точки нормализуется в `dd.mm.yyyy`; поддерживаются как минимум Excel serial, `datetime/date` от `openpyxl` и уже готовая текстовая строка `dd.mm.yyyy`.
  Rationale: Это покрывает sample-файл и позволяет принять обычные датовые ячейки Excel, не расширяя задачу до универсального парсинга всех форматов дат.
  Date/Author: 2026-04-09, Codex.

- Decision: QSettings для point-flow ограничиваются локальными предпочтениями окна точек: `points/last_excel_path`, `points/last_export_folder`, `points/style/color`, `points/style/opacity`.
  Rationale: Пользователю полезно восстанавливать последний файл и стиль, но эти данные не должны переезжать между проектами и не должны попадать в `.lgm.json`.
  Date/Author: 2026-04-09, Codex.

- Decision: В `v2.0.4` сборочный `build_exe_windows.bat` нужно обновить так, чтобы PyInstaller явно собирал `openpyxl` через `--collect-submodules openpyxl` и `--collect-data openpyxl`.
  Rationale: Для новой Excel-зависимости лучше сразу зафиксировать безопасную EXE-стратегию, чем откладывать возможную проблему импорта модулей до финального smoke-теста релиза.
  Date/Author: 2026-04-09, Codex.

- Decision: Для `v2.0.3` окно точек остается самостоятельным top-level окном с собственными локальными `QSettings`, а `MainWindow` только открывает его через меню и хранит ссылку для повторного показа.
  Rationale: Это дает отдельный point-flow внутри того же EXE, но не тащит импортированные точки, цвет и путь `.kml` в grid-состояние, `ProjectState` или `.lgm.json`, сохраняя минимальную поверхность интеграции.
  Date/Author: 2026-04-10, Codex.

## Outcomes & Retrospective

Milestone `v2.0.1` завершен как рабочий этап roadmap. В репозитории появился минимальный, но уже проверяемый point-domain: `PointRecord`, `PointStyle`, helpers нормализации, `PointImportResult`/`PointImportError`, отдельный `point_kml` writer и `point_exporter`. Все это живет в новых `core/app`-модулях и не расширяет существующие grid-модели.

Самое важное достижение этапа - зафиксирован контракт point-flow до появления Excel-импорта и отдельного окна. Следующие milestones теперь могут опираться на готовые сущности, формат итогового point-KML и тесты, не переизобретая базовые типы и не споря о структуре `Placemark`.

Roadmap при этом остается активным: `v2.0.2`, `v2.0.3`, `v2.0.4` и финальная подготовка `v2.1.0` еще впереди. Последняя принятая стабильная версия приложения все еще `v2.0.0`; `v2.0.1` зафиксирован как рабочая версия после автоматической проверки `pytest` и `compileall`, но без ручного пользовательского теста и без релизной EXE-подготовки.
Roadmap при этом остается активным: `v2.0.2`, `v2.0.3`, `v2.0.4` и финальная подготовка `v2.1.0` еще впереди. При этом сам milestone `v2.0.1` уже доведен до принятой версии: после ручного теста пользователя и офлайн-релизной проверки текущей принятой версией проекта стала `v2.0.1`.

Milestone `v2.0.2` завершен как принятый этап roadmap. В репозитории появился реальный sample-first importer `.xlsx`: первый лист с данными, строгий заголовок `ФИО | Дата | Координаты`, нормализация Excel serial/text/date значений, построчная валидация и преобразование точек в WGS84 без смешивания point-flow с grid-flow.

Главный итог этапа - зафиксирован строгий контракт входных данных до появления отдельного UI-окна. Теперь `v2.0.3` может опираться на готовый `PointImportResult`, показывать таблицу и ошибки, не споря о заголовке workbook, трактовке sample-координат или правилах блокировки экспорта. После ручного теста пользователя, офлайн-релизной проверки и сборки EXE текущей принятой версией проекта стала `v2.0.2`.

Milestone `v2.0.3` завершен как рабочий этап roadmap. В приложении появилось отдельное окно `Точки из Excel` в `src/limuzin_grid_manager/ui/points_window.py`: оно загружает sample-first `.xlsx`, показывает сводку импорта, таблицу корректных точек, ошибки по строкам, единый стиль точек и путь итогового `.kml`. Через `QSettings` окно сохраняет только локальные удобства point-flow и не вмешивается в `ProjectState` или `.lgm.json`.

Главный итог этапа - point-flow впервые стал доступен из интерфейса того же EXE без смешивания с grid-вкладками. `src/limuzin_grid_manager/ui/main_window.py` получил только меню `Инструменты -> Точки из Excel...` и удержание ссылки на окно, а offscreen-smoke тесты подтвердили открытие окна, загрузку workbook, изменение цвета и прозрачности и отсутствие регрессии в текущих вкладках `Предпросмотр`, `Проверка`, `Экспорт`. Автоматическая проверка этапа завершилась результатами `15 passed` для таргетированных point/UI-тестов, `81 passed` для полного `pytest` и успешным `compileall`.

## Context and Orientation

LIMUZIN GRID MANAGER `v2.0.0` - Windows desktop-приложение на Python `>=3.11,<3.15` и PySide6. Основной сценарий сегодня - построение сеток `1000x1000` и `100x100` по двум точкам области в СК-42 / Пулково-42, Гаусса-Крюгера, с экспортом в KML, ZIP, SVG, GeoJSON и CSV. Главное окно приложения находится в `src/limuzin_grid_manager/ui/main_window.py`. Оно строит grid-ориентированный интерфейс: координаты, настройки сетки, переименование больших квадратов, стиль KML/SVG, вкладки `Предпросмотр`, `Проверка`, `Экспорт`.

Текущая координатная логика уже подходит и для точек. Входные координаты пользователя живут как `X/Y`. В `pyproj` они передаются в порядке `Y/X`. Зона Гаусса-Крюгера определяется как `int(abs(Y) // 1_000_000)`, а трансформер создается в `src/limuzin_grid_manager/core/crs.py` через EPSG `28400 + zone`. Поддерживаемые зоны - `1..32`. Это нужно переиспользовать для point-flow без дублирования новой координатной математики.

Текущее grid-KML пишется в `src/limuzin_grid_manager/core/kml.py`, а надежная запись через временный файл и атомарную замену результата собрана в `src/limuzin_grid_manager/app/exporter.py`. Эти модули важны как ориентир по качеству реализации, но point-flow не должен превращаться в еще один `ExportMode`. Вместо этого ему нужны отдельные модули и отдельный UI-path.

С точки зрения пользовательских образцов задача уже конкретизирована. Sample workbook содержит лист `Лист1` и строки с `ФИО`, `Дата`, `Координаты`. В sample KML каждая строка Excel превращается в точку AlpineQuest: имя попадает в `<name>`, дата - в `description` и `ExtendedData/comment`, а lon/lat пишутся в `<Point><coordinates>`. Этот KML не обязан быть побайтно идентичен образцу, но по структуре и смыслу должен быть совместимым с AlpineQuest.

Новый сценарий должен жить рядом с grid-приложением, а не внутри него. Главная причина не только в пожелании пользователя, но и в устройстве текущего кода: `GridOptions`, `ProjectState`, `KmlStyle`, preview и export summary уже заточены под прямоугольные сетки, а не под списки точек. Поэтому point-flow проектируется как соседний, а не вложенный subsurface.

## Plan of Work

Работу нужно вести в четыре прикладных слоя: dependency и importer, point-domain и writer, UI-окно точек, затем стабилизация и релизная подготовка. Сначала в `pyproject.toml` и `uv.lock` добавляется runtime dependency `openpyxl`, а в `src/limuzin_grid_manager/app/point_import.py` появляется импорт `.xlsx` в режиме только чтения. Этот модуль берет `Path`, находит первую рабочую таблицу, читает первую непустую строку как заголовок, валидирует sample-first колонки и преобразует строки в результат импорта с накопленными ошибками.

Затем в `src/limuzin_grid_manager/core/points.py` появляется отдельная point-модель. В ней должны жить `PointRecord`, `PointStyle`, helpers нормализации цвета и даты, а также преобразование строки координат в `X/Y`. Point-domain переиспользует `zone_for_y`, `make_transformer_for_zone` и `ck42_to_wgs84` из текущего core, но не зависит от `GridOptions` и не читает `.lgm.json`.

После этого в `src/limuzin_grid_manager/core/point_kml.py` и `src/limuzin_grid_manager/app/point_exporter.py` нужно собрать point-KML path. Первый модуль отвечает только за KML-писатель и структуру `Placemark`, второй - за прикладную запись через временный файл, проверку свободного места, прогресс и отмену. Существующий `app/exporter.py` остается только для grid-flow и не превращается в монолит "экспорт всего".

UI-слой строится отдельно в `src/limuzin_grid_manager/ui/points_window.py`. Это окно должно быть полноценным `QMainWindow` или эквивалентным top-level окном с собственным layout, status-текстом и действиями. В `src/limuzin_grid_manager/ui/main_window.py` добавляется только новый пункт меню `Инструменты -> Точки из Excel...`, создание окна по требованию и удержание ссылки на него, чтобы окно не уничтожалось сборщиком мусора. Grid-вкладки, `GridPreviewWidget`, `ProjectState` и текущая вкладка `Экспорт` не меняют назначение.

Последним слоем идут тесты и документация. Новую логику ядра лучше покрывать в `tests/test_points.py`, а UI-smoke удобно добавить в `tests/test_ui.py`, чтобы сохранить единый offscreen-паттерн. Образцовый workbook для тестов не нужно коммитить бинарником: его следует создавать прямо в тестах через `openpyxl` во временной папке. В финале `v2.1.0` синхронизируются версии, обновляются `README.md`, `USER_GUIDE.md`, `GRIDBASE.md`, `versions/GRIDVERSIONS.md` и создается `versions/v2.1.0.md`.

## Milestones

### v2.0.1 - Point domain foundation

Цель этапа - заложить отдельный point-flow, не трогая существующий grid-flow. В `src/limuzin_grid_manager/core/points.py` нужно определить `PointRecord`, `PointStyle` и helpers для нормализации даты, координат и цвета. `PointRecord` хранит `name`, `source_date`, `display_date`, `x`, `y`, `zone`, `lon`, `lat` и `source_row`. `PointStyle` хранит `color` и `opacity`. Рядом или в `src/limuzin_grid_manager/app/point_import.py` должен появиться `PointImportResult`, который хранит валидные записи, ошибки по строкам, количество строк источника и краткую сводку.

В этом же milestone нужен отдельный KML-writer, ориентировочно `src/limuzin_grid_manager/core/point_kml.py`. Он должен писать только point-KML и не знать ничего про сетки, прямоугольники, `GridOptions` и режимы `ExportMode`. Структура результата фиксируется сразу: `Document` с именем `Waypoints`, затем `Placemark` на каждую точку, inline `Style` с `IconStyle/color`, `name`, `description`, `ExtendedData/comment` и `Point/coordinates`.

Приемка этапа: появляются unit-тесты на `PointRecord`, `PointStyle`, на кодирование KML-цвета `aabbggrr` для точек и на XML-структуру одного-двух `Placemark` с `Point`. Grid-тесты не меняются и продолжают проходить без адаптаций под новый режим.

### v2.0.2 - Excel import and strict validation

Цель этапа - дать приложению надежный импорт sample-first `.xlsx`. В `pyproject.toml` добавляется runtime dependency `openpyxl`, затем в `src/limuzin_grid_manager/app/point_import.py` реализуется чтение workbook через `openpyxl.load_workbook(path, read_only=True, data_only=True)`. Импорт ищет первый лист с данными, берет первую непустую строку как заголовок и требует после нормализации ровно три колонки: `фио`, `дата`, `координаты`.

Каждая строка данных валидируется независимо. Пустое `ФИО` дает ошибку строки. Дата поддерживает три формы: Excel serial, `datetime/date` из `openpyxl` и готовую строку `dd.mm.yyyy`. Координаты валидны только при наличии ровно двух целочисленных чисел, где первое - `X`, второе - `Y`. Для `Y` вычисляется зона; если зона вне `1..32`, строка считается ошибочной. После этого используется текущая цепочка `zone from Y -> make_transformer_for_zone(zone) -> ck42_to_wgs84(x, y, transformer)`.

Экспорт при этом milestone обязан быть строгим: если в workbook есть хотя бы одна ошибка, `PointImportResult` возвращает все найденные проблемы, но point-export остается недоступным. Никакого частичного KML "только по валидным строкам" в `v2.1.0` быть не должно.

Приемка этапа: тесты программно собирают workbook во временной папке, затем проверяют sample workbook path, serial date `46115 -> 03.04.2026`, текстовую дату `03.04.2026`, извлечение `X/Y`, ошибки пустых ячеек, ошибки некорректных координат, ошибку зоны вне `1..32` и совпадение lon/lat с эталонными значениями образца в разумной погрешности.

### v2.0.3 - Separate points window inside the app

Цель этапа - дать новый пользовательский сценарий в интерфейсе, не ломая grid-UI. В `src/limuzin_grid_manager/ui/points_window.py` создается отдельное окно `PointsWindow`. Оно должно содержать выбор Excel-файла, сводку импорта, таблицу предварительного просмотра, текстовый блок ошибок, настройки общего стиля точек, выбор выходного `.kml`, кнопку генерации и строку состояния. Таблица предварительного просмотра должна показывать как минимум `Строка`, `ФИО`, `Дата`, `X`, `Y`, `Зона`, `Lon`, `Lat`. Ошибки по строкам можно показывать отдельно, но они обязаны ссылаться на номер строки источника.

В `src/limuzin_grid_manager/ui/main_window.py` добавляется меню `Инструменты` и действие `Точки из Excel...`. Это действие открывает или поднимает существующее окно точек. Главное окно не получает новых вкладок и не начинает хранить point-state в своем `ProjectState`. Новое окно использует текущую тему приложения через общий stylesheet `QApplication`; отдельных theme-файлов для point-flow не требуется, если не появятся custom widgets.

Через `QSettings` окно точек хранит только локальные удобства: последний путь к `.xlsx`, последнюю папку экспорта, последний цвет и прозрачность. Эти значения не попадают в `.lgm.json`, не сериализуются через `ProjectState` и не влияют на текущий grid-workflow.

Приемка этапа: offscreen UI-smoke тесты открывают `MainWindow`, вызывают новое действие меню, получают `PointsWindow`, загружают sample workbook, видят строки таблицы, меняют цвет и прозрачность и убеждаются, что текущие вкладки `Предпросмотр`, `Проверка`, `Экспорт` остаются grid-ориентированными и не получают point-controls.

### v2.0.4 - Export hardening, UX polish, EXE readiness

Цель этапа - довести point-flow до того же уровня надежности, что и grid-export. В `src/limuzin_grid_manager/app/point_exporter.py` нужно повторить паттерн безопасной записи: временный файл в папке назначения, запись KML, проверка на отмену, атомарная замена результата и очистка `.tmp` при ошибке. Интерфейс окна точек должен показывать статус, прогресс и недоступность кнопки генерации во время записи. Даже если point-KML короче grid-KML, надежность не должна быть упрощенной.

В этом же milestone закрепляется итоговая структура point-KML для `v2.1.0`: один файл, один `Document`, по одному `Placemark` на каждую строку Excel, имя в `<name>`, дата в `description` и `ExtendedData/comment`, координаты в `lon,lat`, один общий `IconStyle/color` для всех точек. Документ должен быть AlpineQuest-совместимым по структуре и смыслу, но roadmap не требует побайтного совпадения с внешним образцом.

Сборочный pipeline должен стать EXE-готовым для `openpyxl`. В `build_exe_windows.bat` нужно добавить явный сбор подмодулей и данных `openpyxl`, затем проверить, что офлайн-сборка и smoke-запуск EXE открывают окно точек и умеют читать `.xlsx`.

Приемка этапа: тесты проверяют atomic write, удаление `.tmp` при ошибке и отмене, XML-валидность point-KML, количество `Placemark`, общий `IconStyle/color`, а также EXE-smoke с открытием окна точек после сборки.

### v2.1.0 - Stabilization and release preparation

Цель этапа - зафиксировать новую стабильную версию после промежуточных patch-этапов. Нужно синхронизировать версии в `pyproject.toml`, `src/limuzin_grid_manager/__init__.py` и `version_info.txt`, обновить `README.md`, `USER_GUIDE.md`, `GRIDBASE.md`, `versions/GRIDVERSIONS.md` и создать `versions/v2.1.0.md`. В `README.md` и `USER_GUIDE.md` должен появиться новый пользовательский сценарий окна точек. В `GRIDBASE.md` нужно описать новые point-модули и границы между point-flow и grid-flow.

Финальная ручная приемка состоит из двух независимых сценариев. Первый сценарий подтверждает отсутствие регрессий в сетках `v2.0.0`: расчет области, preview, KML/ZIP/SVG/GeoJSON/CSV и проекты `.lgm.json` продолжают работать как раньше. Второй сценарий открывает sample Excel, показывает точки, дает выбрать общий цвет и прозрачность, экспортирует KML и подтверждает, что AlpineQuest импортирует результат как список точек.

Как и в прошлых релизах, нельзя коммитить, пушить, создавать tag и GitHub Release без ручного пользовательского теста и явного подтверждения.

## Concrete Steps

Работу по этому roadmap нужно выполнять из корня репозитория `C:\Users\user\Desktop\LIMUZIN GRID MANAGER`.

Сначала подготовить окружение:

    uv sync --extra dev

После обычных изменений point-core, importer или writer запускать:

    uv run --extra dev pytest
    uv run --extra dev python -m compileall src tests

Во время реализации `v2.0.2` и `v2.0.3` полезно отдельно гонять таргетированные тесты point-flow:

    uv run --extra dev pytest tests\test_points.py tests\test_ui.py

Для ручной локальной проверки нового окна во время реализации запускать приложение так:

    uv run limuzin-grid-manager

Перед релизной подготовкой `v2.1.0` выполнять тот же офлайн-пайплайн, что и для прошлых стабильных версий:

    uv lock --offline
    uv run --offline --extra dev pytest
    uv run --offline --extra dev python -m compileall src tests
    $env:UV_OFFLINE='1'; .\build_exe_windows.bat

После офлайн-сборки проверять, что `dist/LIMUZIN_GRID_MANAGER.exe` существует, запускается и позволяет открыть окно `Точки из Excel...`.

## Validation and Acceptance

Для проверки самого `ROADMAPv2.1.md` нужно прочитать файл и убедиться, что в нем есть все обязательные living-разделы `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`, а также самостоятельные milestone-этапы `v2.0.1`, `v2.0.2`, `v2.0.3`, `v2.0.4` и `v2.1.0`.

Для будущей реализации point-flow acceptance считается достигнутой только тогда, когда одновременно выполняются все условия. Точка входа в новый сценарий существует как отдельное окно, а не как вкладка в grid-интерфейсе. Sample workbook `ФИО | Дата | Координаты` загружается без ручного маппинга колонок. Excel serial и текстовая дата нормализуются в `dd.mm.yyyy`. Координаты идут по инварианту `X/Y -> zone from Y -> pyproj(y, x) -> lon/lat`. Экспорт блокируется при наличии хотя бы одной ошибки строки. Point-KML содержит `Placemark`-точки с `Point`, `description`, `ExtendedData/comment` и общим цветом через `IconStyle/color`.

Обязательная автоматическая проверка перед принятием любого milestone-а включает `pytest` и `compileall`. Для `v2.0.4` и `v2.1.0` дополнительно обязательны офлайн-проверка, сборка EXE и smoke-запуск. Для `v2.1.0` окончательная приемка требует ручной пользовательский тест и подтверждение, что grid-сценарии `v2.0.0` не регрессировали.

## Idempotence and Recovery

Этот файл добавляется к репозиторию и не заменяет `roadmap.md` или `ROADMAPv2.md`. Если будущий агент начинает работу и `ROADMAPv2.1.md` уже существует, он обязан сначала прочитать его целиком и обновлять как living document, а не перезаписывать с нуля.

Если во время реализации выяснится, что point-flow требует другой архитектуры, изменение курса нужно сначала записать в `Surprises & Discoveries` и `Decision Log`, а затем обновить соответствующий milestone. Нельзя молча отступать от зафиксированного решения о separate window, strict validation или независимости от `.lgm.json`.

Если импорт Excel окажется нестабилен в EXE без дополнительных флагов PyInstaller, это должно быть исправлено в milestone `v2.0.4` до финальной стабилизации. Нельзя переносить такой риск в `v2.1.0` и надеяться, что ручной тест "как-нибудь пройдет".

Любое изменение, которое начнет вмешиваться в grid-flow или ломать старые `.lgm.json`, KML, ZIP, SVG, GeoJSON или CSV-сценарии, должно рассматриваться как регрессия. Путь восстановления - откат point-изменений к их изолированным модулям, а не расширение grid-моделей под точки.

## Artifacts and Notes

Ниже зафиксированы краткие факты по реальным пользовательским образцам, которые должны оставаться эталоном для `v2.1.0`.

    Лист sample workbook:
    ФИО | Дата | Координаты
    Мишарин Александр Витальевич | 46115 | х-5649764 y-6661612
    Педьков Михаил Иванович      | 46115 | х-5649800 y-6661934

    Нормализация sample date:
    46115 -> 03.04.2026

    Смысловая структура sample KML:
    <Placemark>
      <name>Мишарин Александр Витальевич</name>
      <description><![CDATA[<i>03.04.2026</i>]]></description>
      <ExtendedData>
        <Data name="comment"><![CDATA[03.04.2026]]></Data>
      </ExtendedData>
      <Style>
        <IconStyle>
          <color>FF32CA00</color>
        </IconStyle>
      </Style>
      <Point>
        <coordinates>35.29845459878114,50.955512683199146</coordinates>
      </Point>
    </Placemark>

Автотесты не должны зависеть от внешних пользовательских файлов из `C:\Users\user\Documents`. Workbook для тестов нужно создавать во временной папке программно через `openpyxl`, а sample KML-проверки строить через ожидаемую XML-структуру, а не через сравнение с внешним файлом.

Что не входит в обязательный объем `v2.1.0`: импорт `.xls`, мастер сопоставления колонок, per-row стиль из Excel, встроенное редактирование таблицы как spreadsheet, объединение point-flow и grid-flow в один проектный файл, пакетная обработка нескольких Excel-файлов, дополнительные KML-иконки и map-backed preview для точек.

## Interfaces and Dependencies

Новые или переработанные интерфейсы этого roadmap должны быть следующими.

В `src/limuzin_grid_manager/core/points.py` определить:

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

    @dataclass(frozen=True)
    class PointStyle:
        color: str = "#32ca00"
        opacity: int = 100

    def normalize_point_color(value: str) -> str: ...
    def normalize_point_opacity(value: int) -> int: ...
    def point_style_to_kml_color(style: PointStyle) -> str: ...
    def normalize_point_date(value: object) -> str: ...
    def parse_point_coordinates(value: str) -> tuple[int, int]: ...

В `src/limuzin_grid_manager/app/point_import.py` определить:

    @dataclass(frozen=True)
    class PointImportError:
        source_row: int
        message: str

    @dataclass(frozen=True)
    class PointImportResult:
        sheet_name: str
        records: tuple[PointRecord, ...]
        errors: tuple[PointImportError, ...]
        total_rows: int

    def import_points_from_excel(path: Path) -> PointImportResult: ...

В `src/limuzin_grid_manager/core/point_kml.py` определить:

    def write_points_kml(
        out_path: Path,
        records: Sequence[PointRecord],
        style: PointStyle,
        progress: Callable[[int, int], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> None: ...

В `src/limuzin_grid_manager/app/point_exporter.py` определить:

    def export_points_kml(
        out_path: Path,
        records: Sequence[PointRecord],
        style: PointStyle,
        progress: Callable[[int, int], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> None: ...

В `src/limuzin_grid_manager/ui/points_window.py` определить top-level окно:

    class PointsWindow(QMainWindow):
        ...

    Оно должно уметь:
    - выбирать `.xlsx`;
    - показывать `PointImportResult`;
    - редактировать общий `PointStyle`;
    - выбирать путь выходного `.kml`;
    - запускать `export_points_kml()`;
    - хранить локальные настройки через `QSettings`.

В `src/limuzin_grid_manager/ui/main_window.py` добавить только интеграцию открытия окна точек и удержание живой ссылки на него. Никакие новые point-режимы не должны добавляться в `GridOptions`, `ExportMode`, `ProjectState` или текущий grid-export registry.

В `pyproject.toml` добавить runtime dependency:

    openpyxl>=3.1

В `build_exe_windows.bat` добавить явный сбор Excel-зависимости:

    --collect-submodules openpyxl
    --collect-data openpyxl

Revision note 2026-04-09 Europe/Moscow: файл создан как новый living roadmap для пути `v2.0.0 -> v2.1.0` после проверки текущего репозитория и реальных пользовательских образцов Excel/KML; зафиксированы отдельное окно точек, sample-first `.xlsx`, один общий стиль точек и независимость point-flow от grid-flow.
Revision note 2026-04-09 Europe/Moscow: roadmap обновлен после реализации milestone `v2.0.1`; зафиксированы новый point-domain, point-KML writer, point export service, автотесты (`76 passed`) и оформление `v2.0.1` как рабочей версии при сохранении `v2.0.0` последней принятой стабильной версии.
Revision note 2026-04-09 Europe/Moscow: roadmap обновлен после ручного теста пользователя и офлайн-релизной проверки; `v2.0.1` переведена из рабочей в принятую версию, зафиксированы сборка EXE `2.0.1.0` и smoke-запуск.
Revision note 2026-04-10 Europe/Moscow: roadmap обновлен после реализации milestone `v2.0.2`; зафиксированы `openpyxl`, рабочий `import_points_from_excel()`, strict sample-first `.xlsx`, трактовка sample-координат `х-... y-...` как положительных `X/Y` и новые workbook-тесты (`11 passed`).
Revision note 2026-04-10 Europe/Moscow: roadmap обновлен после ручного теста пользователя и офлайн-релизной проверки; `v2.0.2` переведена из рабочего milestone в принятую версию, зафиксированы сборка EXE `2.0.2.0` и подготовка публикации.
Revision note 2026-04-10 Europe/Moscow: roadmap обновлен после реализации milestone `v2.0.3`; зафиксированы `PointsWindow`, меню `Инструменты -> Точки из Excel...`, локальные `QSettings` point-flow и автоматическая проверка (`15 passed`, `81 passed`, успешный `compileall`).
