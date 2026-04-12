# GITHUB: правила работы с репозиторием

Этот файл описывает, как мы работаем с GitHub в проекте LIMUZIN GRID MANAGER.

## Репозиторий

- GitHub: https://github.com/VLETVKONTENT/limuzin-grid-manager
- Видимость: репозиторий готовится к публичной поддерживаемой публикации.
- Основная ветка: `main`
- Теги версий: `vX.Y.Z`, например `v2.2.0`
- Готовый `LIMUZIN_GRID_MANAGER.exe` не хранится в git-истории и публикуется как GitHub Release asset

## Workflows с v2.2.0

В репозитории есть два штатных workflow:

- `.github/workflows/ci.yml` (`CI`) — автоматически запускается для push и pull request, работает на Windows и выполняет `uv sync --extra dev --locked`, `uv run --extra dev pytest`, `uv run --extra dev python -m compileall src tests` и `uv build`
- `.github/workflows/release-windows.yml` (`Release Windows EXE`) — запускается вручную через `workflow_dispatch` или автоматически по тегу `v*`, собирает `dist/LIMUZIN_GRID_MANAGER.exe` через `build_exe_windows.bat` и публикует EXE как GitHub Actions artifact

Эти workflow не заменяют ручной пользовательский тест. Они добавляют автоматическую дисциплину между локальной подготовкой и публикацией версии.

## Локальная и CI-подпись EXE

Локальная сборка по умолчанию остается unsigned. Это удобно для обычной разработки и smoke-проверок. При необходимости можно дополнительно проверить signing-пайплайн локальным `.pfx`, включая self-signed сертификат для собственных машин.

Для локальной подписи `build_exe_windows.bat` понимает env-переменные:

- `LGM_SIGN_EXE=1` — включить этап подписи после PyInstaller
- `LGM_SIGN_PFX_PATH` — путь к `.pfx`-сертификату вне репозитория
- `LGM_SIGN_PFX_PASSWORD` — пароль к `.pfx`
- `LGM_SIGN_TIMESTAMP_URL` — optional URL timestamp-сервера; по умолчанию используется `http://timestamp.digicert.com`

Если `LGM_SIGN_EXE=1`, скрипт до сборки делает fast-fail preflight: проверяет наличие `.pfx`, пароля и `signtool.exe`. После подписи он сразу запускает `Get-AuthenticodeSignature` и считает сборку успешной только при `Status : Valid`.

Подпись EXE в GitHub Actions для текущего релиза не используется. Если нужно проверить signing-путь, это делается локально через `build_exe_windows.bat` и собственный `.pfx`.

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

Если вы хотите дополнительно проверить signing-пайплайн, соберите signed EXE и проверьте:

```powershell
$env:LGM_SIGN_EXE='1'
$env:LGM_SIGN_PFX_PATH='C:\path\to\certificate.pfx'
$env:LGM_SIGN_PFX_PASSWORD='***'
.\build_exe_windows.bat
Get-AuthenticodeSignature dist\LIMUZIN_GRID_MANAGER.exe | Format-List Status,StatusMessage,SignerCertificate
```

Если подпись включена, ожидается `Status : Valid`. Для проекта допустимо выпускать версию и без коммерческого публичного сертификата, но тогда нужно честно понимать, что внешнего доверия SmartScreen такая схема не дает.

## Что должно быть готово перед публикацией

Перед тем как создавать релиз, различаем четыре разных состояния:

- `Локальная smoke-проверка пройдена` — офлайн-команды выше завершились успешно, EXE собран локально и пользователь принял ручной тест
- `CI green` — после commit/push workflow `CI` завершился успешно на GitHub
- `Artifact build available` — workflow `Release Windows EXE` успешно собрал и сохранил `LIMUZIN_GRID_MANAGER.exe` как GitHub Actions artifact
- `Signed EXE verified (optional)` — либо локальный, либо GitHub Actions EXE проходит `Get-AuthenticodeSignature` со статусом `Valid`

Для текущего процесса обязательны первые три пункта. Четвертый пункт выполняется, если вы используете локальный или CI signing-flow.

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

Когда `CI` зеленый и EXE-артефакт доступен, можно оформить релиз. Если signing использовался, перед релизом также полезно проверить `Valid`:

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
- Не выдавать unsigned или self-signed EXE за externally trusted публичный релиз без пояснения ограничений
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

- Текущая рабочая версия: `v2.2.0`
- Текущая принятая стабильная версия: `v2.2.0`
- Последний опубликованный release: https://github.com/VLETVKONTENT/limuzin-grid-manager/releases/tag/v2.2.0
- Предыдущий опубликованный release: https://github.com/VLETVKONTENT/limuzin-grid-manager/releases/tag/v2.1.4
- Основной источник технического контекста: `GRIDBASE.md`
- История версий: `versions/GRIDVERSIONS.md`
