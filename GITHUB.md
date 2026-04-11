# GITHUB: правила работы с репозиторием

Этот файл описывает, как мы работаем с GitHub в проекте LIMUZIN GRID MANAGER.

## Репозиторий

- GitHub: https://github.com/VLETVKONTENT/limuzin-grid-manager
- Видимость: репозиторий готовится к публичной поддерживаемой публикации.
- Основная ветка: `main`
- Теги версий: `vX.Y.Z`, например `v2.1.4`
- Готовый `LIMUZIN_GRID_MANAGER.exe` не хранится в git-истории и публикуется как GitHub Release asset

## Новые workflows с v2.1.4

В репозитории есть два штатных workflow:

- `.github/workflows/ci.yml` (`CI`) — автоматически запускается для push и pull request, работает на Windows и выполняет `uv sync --extra dev --locked`, `uv run --extra dev pytest`, `uv run --extra dev python -m compileall src tests` и `uv build`
- `.github/workflows/release-windows.yml` (`Release Windows EXE`) — запускается вручную через `workflow_dispatch` или автоматически по тегу `v*`, собирает unsigned `dist/LIMUZIN_GRID_MANAGER.exe` через `build_exe_windows.bat` и публикует EXE как GitHub Actions artifact

Эти workflow не заменяют ручной пользовательский тест. Они добавляют автоматическую дисциплину между локальной подготовкой и публичным релизом.

## Главное правило

Новая версия не коммитится и не пушится сразу после разработки. До коммита версия должна пройти локальную проверку и ручной пользовательский тест, а публикация делается только после явного подтверждения пользователя.

Базовый порядок такой:

1. Codex реализует новую версию в рабочем дереве и обновляет version metadata и release-документы.
2. Codex выполняет локальную smoke-проверку и собирает тестовый EXE.
3. Пользователь вручную тестирует новую версию.
4. Если пользователь находит проблемы, Codex вносит правки и цикл локальной проверки повторяется.
5. Только после подтверждения пользователя Codex делает commit и push.
6. После push workflow `CI` должен завершиться успешно.
7. Затем должен быть доступен собранный EXE-артефакт из workflow `Release Windows EXE`.
8. Только после этого создаются git tag и GitHub Release, если версия должна стать опубликованной.

Нельзя коммитить, пушить и тем более публиковать новую версию до пользовательского теста и явного подтверждения, что версия принята.

## Что обновлять при новой версии

Для версии `vX.Y.Z` нужно обновить:

- `pyproject.toml`
- `src/limuzin_grid_manager/__init__.py`
- `version_info.txt`
- `README.md`, если меняется текущая рабочая/публичная версия или описание возможностей
- `USER_GUIDE.md`, если меняется пользовательский сценарий или чеклист ручной проверки
- `GRIDBASE.md`, если меняется базовая архитектура, процесс поддержки или важные правила проекта
- `roadmap.md`, если меняется статус линии развития
- `versions/GRIDVERSIONS.md`
- `versions/vX.Y.Z.md`
- `FIXPROD.md`, если новая версия реализует очередной этап production-hardening плана

## Локальная smoke-проверка перед ручным тестом

Перед передачей версии пользователю на ручной тест:

```powershell
uv lock --offline
uv run --offline --extra dev pytest
uv run --offline --extra dev python -m compileall src tests
$env:UV_OFFLINE='1'; .\build_exe_windows.bat
```

После сборки проверить:

- `dist/LIMUZIN_GRID_MANAGER.exe` существует
- версия EXE соответствует новой версии
- приложение запускается хотя бы smoke-проходом
- рабочее дерево не содержит лишних build/cache-артефактов

## Что должно быть готово перед публикацией

Перед тем как создавать публичный релиз, различаем три разных состояния:

- `Локальная smoke-проверка пройдена` — офлайн-команды выше завершились успешно, EXE собран локально и пользователь принял ручной тест
- `CI green` — после commit/push workflow `CI` завершился успешно на GitHub
- `Artifact build available` — workflow `Release Windows EXE` успешно собрал и сохранил `LIMUZIN_GRID_MANAGER.exe` как GitHub Actions artifact

Без всех трех пунктов релиз не считается дисциплинированно подготовленным.

## Что делать после подтверждения пользователя

После того как пользователь протестировал версию и подтвердил, что она принята:

```powershell
git status --short --branch
git add .
git commit -m "Release vX.Y.Z"
git push origin main
```

Дальше дождаться зеленого `CI` и вручную запустить EXE workflow, если нужен артефакт до создания тега:

```powershell
gh run list --workflow ci.yml --limit 5 --repo VLETVKONTENT/limuzin-grid-manager
gh workflow run release-windows.yml --ref main --repo VLETVKONTENT/limuzin-grid-manager
gh run list --workflow release-windows.yml --limit 5 --repo VLETVKONTENT/limuzin-grid-manager
```

Когда `CI` зеленый и EXE-артефакт доступен, можно оформить релиз:

```powershell
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z ".\dist\LIMUZIN_GRID_MANAGER.exe" --repo VLETVKONTENT/limuzin-grid-manager --title "vX.Y.Z" --notes-file "versions\vX.Y.Z.md"
```

Если релиз уже был создан, сначала проверить его состояние:

```powershell
gh release view vX.Y.Z --repo VLETVKONTENT/limuzin-grid-manager
```

## Что не делать

- Не пушить непроверенную пользователем версию
- Не создавать GitHub Release без подтверждения пользователя
- Не считать локальную сборку заменой GitHub Actions CI
- Не считать зеленый CI заменой ручного пользовательского теста
- Не коммитить временные файлы: `.venv/`, `build/`, `dist/`, `.pytest_cache/`, `__pycache__/`, `*.spec`
- Не добавлять EXE в git, если только пользователь прямо не попросит хранить бинарник в репозитории

## Проверка перед публичным репозиторием

Перед переключением видимости на public нужно проверить:

- `git status --short --branch --ignored`: не должно быть неигнорируемых личных или временных файлов
- `git ls-files`: в индексе не должно быть `.env`, ключей, локальных `.lgm.json`, пользовательских KML/KMZ/ZIP-экспортов, EXE или баз данных
- `git grep -n -i "token\|secret\|password\|api_key"`: не должно быть секретов
- История git не должна содержать EXE, архивы, локальные проекты, ключи или `.env`
- `.venv/`, `dist/`, `build/`, `.pytest_cache/`, `__pycache__/`, `*.spec`, `*.exe`, пользовательские `*.kml`, `*.kmz`, `*.zip` и `*.lgm.json` должны оставаться игнорируемыми
- Готовый EXE прикрепляется только к GitHub Release как asset

## Текущий статус

- Текущая рабочая версия: `v2.1.4`
- Текущая принятая стабильная версия: `v2.1.4`
- Последний опубликованный release: https://github.com/VLETVKONTENT/limuzin-grid-manager/releases/tag/v2.1.4
- Предыдущий опубликованный release: https://github.com/VLETVKONTENT/limuzin-grid-manager/releases/tag/v2.1.3
- Основной источник технического контекста: `GRIDBASE.md`
- История версий: `versions/GRIDVERSIONS.md`
