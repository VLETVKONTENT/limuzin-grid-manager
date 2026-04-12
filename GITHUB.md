# GITHUB: LIMUZIN GRID MANAGER

This file defines the practical workflow for commits, releases, CI, and public repository hygiene.

Repository: <https://github.com/VLETVKONTENT/limuzin-grid-manager>

Main branch: `main`

Current stable version: `v2.2.0`

## Core rule

Do not commit, push, tag, or publish a new version until:

- local checks are complete
- the user has manually tested the version
- the user has explicitly accepted the version for publication

CI helps, but it does not replace manual user testing.

## What to update for a new version

Always update:

- `pyproject.toml`
- `src/limuzin_grid_manager/__init__.py`
- `version_info.txt`
- `versions/GRIDVERSIONS.md`
- `versions/vX.Y.Z.md`

Update when relevant:

- `README.md`
- `USER_GUIDE.md`
- `GRIDBASE.md`
- `GITHUB.md`

Historical planning documents are archived under:

- `versions/roadmaps_archive/roadmap.md`
- `versions/roadmaps_archive/ROADMAPv2.md`
- `versions/roadmaps_archive/ROADMAPv2.1.md`
- `versions/roadmaps_archive/FIXPROD.md`

These archived files should not be treated as active release checklists.

## Local validation before user testing

Run from the repository root:

```powershell
uv lock --offline
uv run --offline --extra dev pytest
uv run --offline --extra dev python -m compileall src tests
$env:UV_OFFLINE='1'; .\build_exe_windows.bat
```

Then verify:

- `dist/LIMUZIN_GRID_MANAGER.exe` exists
- version numbers are synchronized
- build artifacts are not accidentally staged

## GitHub Actions

The repository contains:

- `.github/workflows/ci.yml`
- `.github/workflows/release-windows.yml`

Expected meaning:

- `CI` validates the repo on Windows for push and pull request
- `Release Windows EXE` rebuilds `LIMUZIN_GRID_MANAGER.exe` as a GitHub Actions artifact

Publication readiness should be read in this order:

1. local validation passed
2. user manual testing passed
3. code was committed and pushed
4. `CI` is green
5. EXE artifact build is available
6. only then create tag and GitHub Release

## EXE signing

`build_exe_windows.bat` builds an unsigned EXE by default.

Optional local Authenticode signing is supported through:

- `LGM_SIGN_EXE=1`
- `LGM_SIGN_PFX_PATH`
- `LGM_SIGN_PFX_PASSWORD`
- optional `LGM_SIGN_TIMESTAMP_URL`

Rules:

- certificates and passwords must stay outside git
- self-signed or local signing is allowed for validation
- unsigned or self-signed EXE must not be presented as publicly trusted commercial signing

## Recommended publication flow

After the user accepts the version:

```powershell
git status --short --branch
git add .
git commit -m "Release vX.Y.Z"
git push origin main
```

Check GitHub Actions, then create tag and release:

```powershell
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z ".\dist\LIMUZIN_GRID_MANAGER.exe" --repo VLETVKONTENT/limuzin-grid-manager --title "vX.Y.Z" --notes-file "versions\vX.Y.Z.md"
```

If you need to inspect release state:

```powershell
gh release view vX.Y.Z --repo VLETVKONTENT/limuzin-grid-manager
```

## What must never be committed

- `.venv/`
- `build/`
- `dist/`
- `.pytest_cache/`
- `__pycache__/`
- `*.spec`
- `*.exe`
- local `.env` and secrets
- user `.lgm.json`
- generated `*.kml`, `*.kmz`, `*.zip`, `*.svg`, `*.geojson`, `*.csv`
- certificates and private keys
- local `AGENTS.md` and `PLANS.md`

## Public repository hygiene

Before a public release or visibility change, run:

```powershell
git status --short --branch --ignored
git ls-files
git grep -n -i "token\|secret\|password\|api_key"
```

The index and history must not contain:

- secrets
- `.env`
- certificates
- local project files
- exported user data
- EXE binaries

## Current release line

- current stable version: `v2.2.0`
- previous stable version: `v2.1.4`
- current release notes: `versions/v2.2.0.md`
- version index: `versions/GRIDVERSIONS.md`
