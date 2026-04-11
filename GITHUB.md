# GITHUB: правила работы с репозиторием

Этот файл описывает, как мы работаем с GitHub в проекте LIMUZIN GRID MANAGER.

## Репозиторий

- GitHub: https://github.com/VLETVKONTENT/limuzin-grid-manager
- Видимость: готовится к публичному репозиторию; последняя принятая стабильная версия `v2.1.3`.
- Основная ветка: `main`.
- Теги версий: `vX.Y.Z`, например `v0.1.0`.
- EXE-файлы не хранятся напрямую в git-истории. Готовый `LIMUZIN_GRID_MANAGER.exe` прикрепляется к GitHub Release как asset.

## Главное правило

Новая версия не коммитится и не пушится сразу после разработки.

Порядок всегда такой:

1. Codex реализует новую версию в рабочем дереве.
2. Codex обновляет номер версии и файлы истории версий.
3. Codex собирает тестовый EXE.
4. Пользователь вручную тестирует новую версию.
5. Если пользователь находит проблемы, Codex вносит правки.
6. Пользователь повторно проверяет исправленную версию.
7. Только после подтверждения пользователя Codex делает commit.
8. Только после commit Codex делает push в GitHub.
9. После push создается git tag и GitHub Release, если версия должна стать опубликованной.

Нельзя коммитить и пушить новую версию до пользовательского теста и явного подтверждения, что версия принята.

## Что обновлять при новой версии

Для версии `vX.Y.Z` нужно обновить:

- `pyproject.toml`
- `src/limuzin_grid_manager/__init__.py`
- `version_info.txt`
- `README.md`, если меняется текущая публичная версия или описание возможностей
- `USER_GUIDE.md`, если меняется пользовательский сценарий или чеклист ручной проверки
- `GRIDBASE.md`, если меняется базовая архитектура или логика приложения
- `roadmap.md`, если меняется статус пункта roadmap
- `versions/GRIDVERSIONS.md`
- `versions/vX.Y.Z.md`

## Что проверять перед пользовательским тестом

Перед передачей версии пользователю на ручной тест:

```powershell
uv lock --offline
uv run --offline --extra dev pytest
uv run --offline --extra dev python -m compileall src tests
$env:UV_OFFLINE='1'; .\build_exe_windows.bat
```

После сборки проверить:

- `dist/LIMUZIN_GRID_MANAGER.exe` существует;
- версия EXE соответствует новой версии;
- приложение запускается хотя бы smoke-тестом;
- рабочее дерево не содержит лишних build/cache-артефактов.

## Что делать после подтверждения пользователя

После того как пользователь протестировал версию и подтвердил, что она принята:

```powershell
git status --short --branch
git add .
git commit -m "Release vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin main
git push origin vX.Y.Z
gh release create vX.Y.Z ".\dist\LIMUZIN_GRID_MANAGER.exe" --repo VLETVKONTENT/limuzin-grid-manager --title "vX.Y.Z" --notes-file "versions\vX.Y.Z.md"
```

Если релиз уже был создан, сначала проверить его состояние через:

```powershell
gh release view vX.Y.Z --repo VLETVKONTENT/limuzin-grid-manager
```

## Что не делать

- Не пушить непроверенную пользователем версию.
- Не создавать GitHub Release без подтверждения пользователя.
- Не коммитить временные файлы:
  - `.venv/`
  - `build/`
  - `__pycache__/`
  - `.pytest_cache/`
  - `.spec`
  - `dist/`
- Не добавлять EXE в git, если только пользователь прямо не попросит хранить бинарник в репозитории.

## Проверка перед публичным репозиторием

Перед переключением видимости на public нужно проверить:

- `git status --short --branch --ignored`: не должно быть неигнорируемых личных или временных файлов.
- `git ls-files`: в индексе не должно быть `.env`, ключей, локальных `.lgm.json`, пользовательских KML/KMZ/ZIP-экспортов, EXE или баз данных.
- `git grep` по словам `token`, `secret`, `password`, `api_key` и шаблонам приватных ключей: не должно быть секретов.
- История git не должна содержать EXE, архивы, локальные проекты, ключи или `.env`.
- `.venv/`, `dist/`, `build/`, `.pytest_cache/`, `__pycache__/`, `*.spec`, `*.exe`, пользовательские `*.kml`, `*.kmz`, `*.zip` и `*.lgm.json` должны оставаться игнорируемыми.
- Готовый EXE прикрепляется только к GitHub Release как asset.

## Текущий статус

- Последняя подготовленная и принятая версия: `v2.1.3`.
- Последний опубликованный release после публикации: https://github.com/VLETVKONTENT/limuzin-grid-manager/releases/tag/v2.1.3
- Предыдущий опубликованный release: https://github.com/VLETVKONTENT/limuzin-grid-manager/releases/tag/v2.1.2
- Основной источник технического контекста: `GRIDBASE.md`.
- История версий: `versions/GRIDVERSIONS.md`.
