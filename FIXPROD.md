# Production Hardening Roadmap from v2.1.0 to v2.2.0

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

The repository already contains `PLANS.md` at the repository root. This document must be maintained in accordance with `PLANS.md`, and every future revision of this plan must remain fully self-contained.

## Purpose / Big Picture

As of `v2.1.0`, LIMUZIN GRID MANAGER already has strong functional coverage: the tests pass, the wheel and source distribution build, and the Windows EXE can be rebuilt from source. The remaining gaps are production gaps rather than feature gaps. A user can already generate grids and point-KML, but they still face avoidable operational risk: `.lgm.json` project saves can be torn by a mid-write failure, Excel import can freeze the UI, the application does not leave behind useful crash logs, GitHub has no automated CI gate, and the public EXE is not digitally signed.

After completing this plan, a user should be able to save projects without fear of silent corruption, import large Excel files without a frozen window, report failures with a real log file, trust that every pull request has passed an automated Windows validation pipeline, and download a signed Windows EXE that passes `Get-AuthenticodeSignature`. The route to that outcome is intentionally staged through small patch releases `v2.1.1` through `v2.1.4`, followed by a final production-hardening minor release `v2.2.0`.

## Progress

- [x] (2026-04-10 17:08Z) Reviewed `PLANS.md`, re-checked the current repository state, and converted the production-readiness audit into this staged ExecPlan.
- [x] (2026-04-11 09:15+03:00) Implemented `v2.1.1`: `src/limuzin_grid_manager/app/project.py` now writes `.lgm.json` through a sibling temporary file plus `replace()`, cleans up `.tmp` files on failure, and preserves the previous project file when replacement fails.
- [x] (2026-04-11 09:15+03:00) Added regression coverage in `tests/test_project.py` for successful atomic saves and for a mocked `replace()` failure that proves the previous project content survives intact.
- [x] (2026-04-11 09:15+03:00) Synced `v2.1.1` working-version metadata and release docs in `pyproject.toml`, `src/limuzin_grid_manager/__init__.py`, `version_info.txt`, `README.md`, `USER_GUIDE.md`, `GRIDBASE.md`, `roadmap.md`, `versions/GRIDVERSIONS.md`, and `versions/v2.1.1.md`.
- [x] (2026-04-11 11:20+03:00) Implemented `v2.1.2`: `src/limuzin_grid_manager/ui/points_window.py` now imports Excel in a dedicated `QThread` worker, keeps the window responsive, disables conflicting controls during import, and blocks window closing until the worker finishes.
- [x] (2026-04-11 11:20+03:00) Added UI smoke coverage in `tests/test_ui.py` for the import-running state, background import behavior, and close blocking while Excel import is active.
- [x] (2026-04-11 11:20+03:00) Synced `v2.1.2` working-version metadata and release docs in `pyproject.toml`, `src/limuzin_grid_manager/__init__.py`, `version_info.txt`, `README.md`, `USER_GUIDE.md`, `GRIDBASE.md`, `roadmap.md`, `versions/GRIDVERSIONS.md`, and `versions/v2.1.2.md`.
- [x] (2026-04-11 13:25+03:00) Implemented `v2.1.3`: added `src/limuzin_grid_manager/app/runtime.py` with rotating runtime logging, local app-data log placement plus fallback, and global hooks for main-thread and Python-thread exceptions.
- [x] (2026-04-11 13:25+03:00) Updated `src/limuzin_grid_manager/__main__.py`, `src/limuzin_grid_manager/ui/main_window.py`, and `src/limuzin_grid_manager/ui/points_window.py` so startup installs diagnostics before showing the UI and worker failures log full tracebacks while user-facing messages include the log-file path.
- [x] (2026-04-11 13:25+03:00) Added regression coverage in `tests/test_runtime.py` and `tests/test_ui.py` for runtime-log creation, exception-hook diagnostics, and point-import worker failures that now leave behind a traceback-containing log.
- [x] (2026-04-11 13:25+03:00) Synced `v2.1.3` working-version metadata and release docs in `pyproject.toml`, `src/limuzin_grid_manager/__init__.py`, `version_info.txt`, `README.md`, `USER_GUIDE.md`, `GRIDBASE.md`, `roadmap.md`, `versions/GRIDVERSIONS.md`, and `versions/v2.1.3.md`.
- [x] (2026-04-11 14:58+03:00) Implemented `v2.1.4`: added `.github/workflows/ci.yml` for Windows validation on push and pull request and `.github/workflows/release-windows.yml` for manual or tag-triggered EXE artifact builds.
- [x] (2026-04-11 14:58+03:00) Updated release-process documentation in `GITHUB.md` so the checklist now distinguishes local smoke validation, green CI, and an available EXE artifact from Actions before tag/release publication.
- [x] (2026-04-11 14:58+03:00) Synced `v2.1.4` working-version metadata and release docs in `pyproject.toml`, `src/limuzin_grid_manager/__init__.py`, `version_info.txt`, `uv.lock`, `README.md`, `USER_GUIDE.md`, `GRIDBASE.md`, `roadmap.md`, `versions/GRIDVERSIONS.md`, and `versions/v2.1.4.md`.
- [ ] Implement `v2.2.0`: optional local and CI code-signing path, signed release verification, and final production release checklist.

## Surprises & Discoveries

- Observation: the current codebase is already healthier than a typical desktop side project, so the next releases should focus on operational safety rather than broad refactors.
  Evidence: `uv run --extra dev pytest` completed with `85 passed in 2.19s`, and `uv run --extra dev python -m compileall src tests` completed without errors.

- Observation: the EXE build path is already real and repeatable, so the plan should preserve `PyInstaller` and harden it instead of replacing it.
  Evidence: `.\build_exe_windows.bat` rebuilt `dist\LIMUZIN_GRID_MANAGER.exe` successfully on 2026-04-10.

- Observation: the repository has no GitHub workflow directory at all, so CI must be introduced from zero rather than repaired.
  Evidence: `Test-Path .github\workflows` returned `False`.

- Observation: the public EXE trust problem is external to Python logic and depends on access to a signing certificate.
  Evidence: `Get-AuthenticodeSignature dist\LIMUZIN_GRID_MANAGER.exe` returned `Status : NotSigned`.

- Observation: the two most concrete code-level risks are easy to point to and should be fixed first because they are isolated and low-risk.
  Evidence: `src/limuzin_grid_manager/app/project.py` currently writes project JSON with a direct `write_text(...)`, and `src/limuzin_grid_manager/ui/points_window.py` currently calls `import_points_from_excel(...)` directly from `load_excel_path(...)`.

- Observation: `v2.1.1` could be implemented without touching UI or project schema because the entire risk lived in the final write step.
  Evidence: replacing the direct `write_text(...)` call with `_write_project_text_atomically(...)` plus two focused tests was enough to move `tests/test_project.py` from 10 to 12 passing tests while keeping the rest of the suite green at `87 passed`.

- Observation: moving Excel import off the GUI thread did not require changes to the workbook parsing rules; the whole patch lived in `PointsWindow` orchestration and UI state.
  Evidence: `src/limuzin_grid_manager/app/point_import.py` stayed untouched while `tests/test_points.py` and `tests/test_ui.py` passed together at `20 passed`.

- Observation: Qt already knows the correct per-user application-data directory once `QApplication` names are set, so `QStandardPaths` can choose the primary log directory without adding a new dependency.
  Evidence: `src/limuzin_grid_manager/__main__.py` now sets the app and organization names before `configure_runtime_logging()`, and `src/limuzin_grid_manager/app/runtime.py` resolves logs through `QStandardPaths.AppLocalDataLocation`.

- Observation: the worker diagnostics patch is easiest to validate through the point-import path because it already has UI tests that monkeypatch the failing service and capture `QMessageBox.warning`.
  Evidence: `tests/test_ui.py::test_points_window_import_failure_logs_traceback_and_shows_log_path` proves both the user-facing message and the traceback inside `runtime.log`.

- Observation: adding repository-native CI did not require new helper scripts because the existing `uv` commands and `build_exe_windows.bat` were already automation-friendly.
  Evidence: `.github/workflows/ci.yml` only needs `uv sync --extra dev --locked`, `uv run --extra dev pytest`, `uv run --extra dev python -m compileall src tests`, and `uv build`, while `.github/workflows/release-windows.yml` can call `build_exe_windows.bat` directly.

- Observation: bumping the package version also updates the local editable package entry in `uv.lock`, so release synchronization for this repository should include the lock file even when dependencies stay the same.
  Evidence: after changing the project to `2.1.4`, `uv.lock` changed `limuzin-grid-manager` from `version = "2.1.3"` to `version = "2.1.4"`.

## Decision Log

- Decision: ship the hardening work as several patch releases before `v2.2.0` instead of one large change set.
  Rationale: each missing production behavior is independently testable, and smaller releases reduce regression risk in a desktop GUI project.
  Date/Author: 2026-04-10 / Codex

- Decision: keep the existing `PyInstaller`-based one-file EXE pipeline and extend it.
  Rationale: it already builds successfully, is documented in the repository, and matches the user’s current release workflow.
  Date/Author: 2026-04-10 / Codex

- Decision: treat digital signing as the `v2.2.0` gate instead of a `v2.1.x` patch.
  Rationale: signing is the only task here that depends on external credentials and Windows tooling outside the repository; all purely code-local hardening should land first.
  Date/Author: 2026-04-10 / Codex

- Decision: run the first CI workflows on Windows as the primary platform.
  Rationale: this is a Windows desktop application with a Windows EXE deliverable, so the highest-value automation is Windows validation first.
  Date/Author: 2026-04-10 / Codex

- Decision: keep the new atomic-save helper local to `src/limuzin_grid_manager/app/project.py` instead of extracting a shared file-write utility first.
  Rationale: `v2.1.1` only needs one additional atomic write path, and a local helper keeps the patch release small while still mirroring the proven temp-file-and-replace pattern from the export services.
  Date/Author: 2026-04-11 / Codex

- Decision: do not add import cancellation in `v2.1.2`; only add background execution and explicit running-state UX.
  Rationale: the user-visible freeze is solved by moving import to a worker thread, while safe mid-read cancellation for `openpyxl` would add more risk than value to this patch release.
  Date/Author: 2026-04-11 / Codex

- Decision: use a dedicated runtime module with Python `logging` plus `RotatingFileHandler` instead of scattering ad-hoc file writes through the UI.
  Rationale: the new diagnostics behavior spans startup, worker code, and future background paths, so a single module keeps path resolution, hook installation, and user-facing log hints consistent.
  Date/Author: 2026-04-11 / Codex

- Decision: choose the runtime-log directory through Qt first and only then fall back to `%LOCALAPPDATA%` or the user profile.
  Rationale: `QStandardPaths` keeps the log path aligned with the running desktop app on Windows, while the fallback path prevents startup failure on systems where the preferred directory cannot be created.
  Date/Author: 2026-04-11 / Codex

- Decision: keep the first repository-native CI matrix on Windows with Python `3.11` and `3.12`, while the EXE artifact workflow builds on Python `3.11`.
  Rationale: Windows is the product target, a two-version matrix adds meaningful coverage without overcomplicating the first CI rollout, and a single Python version for EXE packaging keeps the artifact path deterministic.
  Date/Author: 2026-04-11 / Codex

- Decision: install `uv` in GitHub Actions through `python -m pip install uv` instead of adding another setup action dependency.
  Rationale: the workflows stay self-explanatory, depend on fewer external action interfaces, and remain easy to reproduce locally from the same commands shown in the documentation.
  Date/Author: 2026-04-11 / Codex

## Outcomes & Retrospective

The roadmap is now in motion. `v2.1.1` is implemented as the current working version and closes the most immediate project-data-loss risk: saving a project can no longer overwrite a valid `.lgm.json` with a half-written file. The observable proof is in the new regression coverage for interrupted saves and the passing validation runs (`12 passed` for `tests/test_project.py`, then `87 passed` for the full suite, plus `compileall` without errors).

What remains is still the higher-level production hardening originally planned: moving Excel import off the GUI thread, adding crash logs, introducing CI, and finally wiring in code signing. The expected end-state after `v2.2.0` is unchanged from plan creation, but the first milestone now has concrete evidence instead of only intent.

`v2.1.2` now closes the next operational gap: loading a workbook in `Точки из Excel` no longer freezes the window. The observable proof is the new background-import worker, the import-running UI state, and the targeted validation run `uv run --extra dev pytest tests/test_points.py tests/test_ui.py` with `20 passed`, followed by `compileall` without errors.

`v2.1.3` closes the supportability gap that remained after the UI became responsive: failures now leave behind actionable diagnostics instead of only transient dialogs. The observable proof is the new `runtime.log`, the exception-hook tests in `tests/test_runtime.py`, the UI regression that captures the log path from a failed Excel import, and the full-suite validation moving to `91 passed`.

`v2.1.4` closes the automation gap that remained after the app itself became safer to run and support. The repository now has a Windows CI gate for push and pull request validation plus a dedicated workflow that rebuilds the unsigned EXE and publishes it as an Actions artifact. The observable proof is the new workflow pair in `.github/workflows`, the updated release procedure in `GITHUB.md`, and the local validation run staying green at `91 passed`, `compileall` without errors, and `uv build` producing the `2.1.4` wheel and source distribution.

## Context and Orientation

The repository root already contains the release and behavior map needed for this work. `README.md` explains the product surface and build steps. `GRIDBASE.md` is the technical source of truth for architecture and constraints. `GITHUB.md` defines how versions, releases, tags, CI, and public repository hygiene are handled. `versions/GRIDVERSIONS.md` records accepted versions, and each release note lives in `versions/vX.Y.Z.md`. The new repository automation lives under `.github/workflows`.

The Python package is under `src/limuzin_grid_manager`. The file `src/limuzin_grid_manager/app/project.py` owns `.lgm.json` serialization and deserialization. The file `src/limuzin_grid_manager/ui/points_window.py` owns the separate “Точки из Excel” window and already imports workbooks through a background `QThread` worker. The file `src/limuzin_grid_manager/ui/main_window.py` already contains a working background export pattern with `QThread` and worker objects. The new file `src/limuzin_grid_manager/app/runtime.py` is now the shared home for log-path selection, rotating-file logging, and global exception hooks. The file `src/limuzin_grid_manager/__main__.py` is the GUI bootstrap and is the correct place to install startup-time runtime helpers. The file `build_exe_windows.bat` is the canonical EXE builder and must remain the authoritative local build path.

In this plan, an “atomic save” means writing the full new content to a temporary file in the same directory and replacing the target file only after the write succeeds. A “worker” means a `QObject` moved to a `QThread` so the PySide6 GUI event loop stays responsive. A “crash log” means a timestamped or rotating text log file that captures stack traces and context after an unexpected failure. A “signed EXE” means the result of Windows Authenticode signing, which can be checked with `Get-AuthenticodeSignature`.

## Plan of Work

### v2.1.1: Safe Project Save

This patch release closes the easiest and most user-visible data-loss risk. In `src/limuzin_grid_manager/app/project.py`, keep the public behavior of `save_project_state(path, state) -> Path`, but replace the direct text write with an atomic write helper that mirrors the export safety pattern already used elsewhere in the repository. The helper must create the parent directory, write UTF-8 JSON plus the trailing newline into a temporary file placed beside the target, flush and close it, then replace the target with `Path.replace`. If anything fails before replacement, the temporary file must be removed and any pre-existing project file must remain unchanged.

`tests/test_project.py` must gain regression coverage for the success case and for at least one injected failure path. The failure test must prove that the existing project content survives when the new write path fails partway through. The version files `pyproject.toml`, `src/limuzin_grid_manager/__init__.py`, `version_info.txt`, `versions/GRIDVERSIONS.md`, and a new `versions/v2.1.1.md` must be updated only after the code and tests pass. `GRIDBASE.md` and `README.md` should be updated only if they currently describe project saves in a way that implies stronger guarantees than the code provides.

### v2.1.2: Responsive Excel Import

This patch release removes a GUI freeze without changing the Excel import rules. `src/limuzin_grid_manager/app/point_import.py` should remain the import service and continue to own workbook parsing and validation. The UI change belongs in `src/limuzin_grid_manager/ui/points_window.py`: introduce a background import worker, modeled after the existing export worker pattern in `src/limuzin_grid_manager/ui/main_window.py`, and make `load_excel_path(...)` start that worker instead of calling `import_points_from_excel(...)` inline.

The import UI should become explicitly stateful. While import is running, the Excel browse and load controls, style controls, output-path controls, and generate button must be disabled. The status label must say that import is running, and the progress bar should become visible in indeterminate mode. A dedicated import cancel mechanism is intentionally out of scope for this patch because `openpyxl` read-only iteration does not provide a cheap or obviously safe interruption boundary; the win here is responsiveness, not cancellability. The close behavior of `PointsWindow` must therefore block closing while an import is active in the same way it already blocks closing during export. `tests/test_ui.py` must be extended so the new import-running state is exercised and the window never regresses back to synchronous import.

### v2.1.3: Crash Logging and Diagnostics

This patch release makes failures supportable. Add a new runtime support module at `src/limuzin_grid_manager/app/runtime.py`. That module should own the logging directory choice, log file creation, and installation of global exception hooks. Use the Python standard `logging` module with a rotating file handler so logs do not grow forever. The log directory should live in the user’s local application-data area for this application; when that cannot be resolved, fall back to a safe writable directory under the user profile.

`src/limuzin_grid_manager/__main__.py` must call the runtime setup after `QApplication` is created and before `MainWindow` is shown. The hooks should capture uncaught exceptions from the main thread and from Python worker threads, write stack traces to the log, and surface a short user-facing message that tells the user where the log file lives. Existing worker classes in `src/limuzin_grid_manager/ui/main_window.py` and `src/limuzin_grid_manager/ui/points_window.py` should also log full tracebacks when they emit failure messages so that support has more than `str(exc)`. The documentation update for this release should be small but explicit: `README.md` and `USER_GUIDE.md` should mention where runtime logs are stored and why they matter.

### v2.1.4: CI and Release Discipline

This patch release introduces an automated gate without changing user-visible application behavior. Create `.github/workflows/ci.yml` and make it the default validation workflow for pushes and pull requests. It should run on Windows, install Python and `uv`, restore dependencies, run `uv run --extra dev pytest`, run `uv run --extra dev python -m compileall src tests`, and run `uv build`. If runtime is acceptable, add a small matrix over two supported Python versions, but Windows must remain the primary target.

Also add `.github/workflows/release-windows.yml` as a manual or tag-triggered workflow that rebuilds the Windows EXE and uploads it as an artifact. This workflow does not need to sign yet; it exists to prove that EXE packaging is reproducible in automation before the certificate step is introduced. `GITHUB.md` must be updated so the manual release checklist now distinguishes between “local smoke pass,” “CI green,” and “artifact build available.” The release notes for `v2.1.4` should clearly say that this is the first version with repository-native CI.

### v2.2.0: Signed Public Release Gate

This minor release closes the final credibility gap for public distribution. Extend `build_exe_windows.bat` so it still builds unsigned EXEs by default, but can also perform Authenticode signing when a secure set of environment variables is present. The signing stage must be optional for everyday development and mandatory for the final public release flow. Do not commit certificates, private keys, or password files. The script should fail fast with a clear message if signing is requested but the required secrets are missing.

In the repository automation, extend the Windows release workflow so a signed tag build can happen on GitHub Actions when the necessary secrets are configured. If the repository owner prefers local signing only, the workflow should build the unsigned artifact and the documented release procedure in `GITHUB.md` should describe the local signing step explicitly. The final acceptance target for `v2.2.0` is concrete: the built `dist\LIMUZIN_GRID_MANAGER.exe` must pass `Get-AuthenticodeSignature`, the release notes must record that the public EXE is signed, and the normal regression suite must still pass. `versions/v2.2.0.md` should act as the public production-hardening summary that ties the whole sequence together.

## Concrete Steps

All commands below are run from the repository root:

    Set-Location "C:\Users\user\Desktop\LIMUZIN GRID MANAGER"

For `v2.1.1`, implement the atomic-save helper, update the project save path, add regression tests, and then run:

    uv run --extra dev pytest tests/test_project.py
    uv run --extra dev pytest
    uv run --extra dev python -m compileall src tests

Completed on 2026-04-11. The observed outcome was:

    uv run --extra dev pytest tests/test_project.py
    ...
    ============================= 12 passed in 0.22s =============================

    uv run --extra dev pytest
    ...
    ============================= 87 passed in 4.24s =============================

    uv run --extra dev python -m compileall src tests
    Listing 'src'...
    Listing 'tests'...

The failure-path test confirms that no temporary `.tmp` file remains in the test directory after a forced replacement failure.

For `v2.1.2`, add the import worker and import-running UI state, extend `tests/test_ui.py`, and then run:

    uv run --extra dev pytest tests/test_points.py tests/test_ui.py
    uv run limuzin-grid-manager

The expected outcome is that the tests pass, the application launches, and loading a non-trivial workbook no longer freezes the window while the import is in progress.

For `v2.1.3`, add the runtime logging module, install the hooks in startup, make worker failures log tracebacks, and then run:

    uv run --extra dev pytest
    uv run limuzin-grid-manager

Completed on 2026-04-11. The observed outcome was:

    uv run --extra dev pytest tests/test_runtime.py tests/test_ui.py
    ...
    ============================== 9 passed in 6.41s ==============================

    uv run --extra dev pytest
    ...
    ============================= 91 passed in 5.92s ==============================

    uv run --extra dev python -m compileall src tests
    Listing 'src'...
    Listing 'tests'...

The new runtime tests prove that the exception hook logs a traceback to `runtime.log` and shows the log path to the user, while the UI regression proves the same behavior for a failed Excel import worker.

For `v2.1.4`, add the workflow files and documentation changes, then run:

    uv run --extra dev pytest
    uv run --extra dev python -m compileall src tests
    uv build
    git status --short

Completed on 2026-04-11. The observed outcome was:

    uv run --extra dev pytest
    ...
    ============================= 91 passed in 2.84s ==============================

    uv run --extra dev python -m compileall src tests
    Listing 'src'...
    Listing 'src\\limuzin_grid_manager'...
    Listing 'tests'...

    uv build
    Building source distribution...
    Building wheel from source distribution...
    Successfully built dist\\limuzin_grid_manager-2.1.4.tar.gz
    Successfully built dist\\limuzin_grid_manager-2.1.4-py3-none-any.whl

The repository now contains `.github/workflows/ci.yml` and `.github/workflows/release-windows.yml`, while the generated `dist` package artifacts remain untracked build output.

For `v2.2.0`, add the signing hooks and the final release procedure, then run:

    .\build_exe_windows.bat
    Get-AuthenticodeSignature dist\LIMUZIN_GRID_MANAGER.exe | Format-List Status,StatusMessage,SignerCertificate

If signing is enabled for the run, the expected outcome is `Status : Valid`. If signing is intentionally not enabled on a developer machine, the script should still build the EXE and print a clear message that the result is unsigned and not suitable for the final public release.

## Validation and Acceptance

`v2.1.1` is accepted when saving a project no longer risks replacing a valid `.lgm.json` with a half-written file. This must be demonstrated by a test that fails before the change and passes after it, and by preserving an existing file when a mocked write or replace step fails.

`v2.1.2` is accepted when the “Точки из Excel” window remains responsive while import work happens in the background. The user should see disabled controls and a visible running indicator instead of a frozen interface. The import rules, validation messages, and output records must remain unchanged.

`v2.1.3` is accepted when an unexpected exception leaves behind a supportable log file with a traceback and the user receives a short, actionable message instead of a silent failure. The app must still start normally after the logging system is introduced.

`v2.1.4` is accepted when a pull request or push to the repository can trigger an automated Windows validation run that executes tests, compile checks, and packaging checks without manual desktop intervention.

`v2.2.0` is accepted only when the final public EXE is signed and the signature is independently verifiable with Windows tooling. The normal regression suite, package build, and EXE build must still pass, and no certificate material may be added to git.

## Idempotence and Recovery

Each milestone is designed to be independently releasable and safely repeatable. If a milestone is interrupted before the version bump, leave the version metadata unchanged and continue the implementation on the same branch. If the atomic save work is interrupted, the helper must clean up its temporary file so rerunning the same save path behaves normally. If the background import work is interrupted, restarting the application should be sufficient; no persistent state should be mutated during import. If runtime logging misbehaves, the fallback is to preserve the old application behavior while keeping the log initialization additive and isolated in `app/runtime.py`.

The CI milestone is safe to re-run because workflow files are declarative. The signing milestone is the only one with external risk. The certificate file must always stay outside git, and any temporary certificate material reconstructed on CI runners must be deleted before job exit. If signing secrets are not yet available, `v2.2.0` must not be tagged as the final public production release; keep the code path merged, but do not claim the trust problem is closed until `Get-AuthenticodeSignature` returns `Valid`.

## Artifacts and Notes

The current baseline evidence for this plan is:

    uv run --extra dev pytest
    ...
    ============================= 91 passed in 2.84s ==============================

    uv run --extra dev python -m compileall src tests
    Listing 'src'...
    Listing 'src\\limuzin_grid_manager'...
    Listing 'tests'...

    uv build
    Building source distribution...
    Building wheel from source distribution...
    Successfully built dist\\limuzin_grid_manager-2.1.4.tar.gz
    Successfully built dist\\limuzin_grid_manager-2.1.4-py3-none-any.whl

    git status --short
     M GITHUB.md
     M GRIDBASE.md
     M README.md
     M USER_GUIDE.md
     M pyproject.toml
     M roadmap.md
     M src/limuzin_grid_manager/__init__.py
     M uv.lock
     M version_info.txt
     M versions/GRIDVERSIONS.md
    ?? .github/
    ?? versions/v2.1.4.md

The code locations that motivated the first two fixes are:

    src/limuzin_grid_manager/app/project.py
    221: def save_project_state(path: str | Path, state: ProjectState) -> Path:
    225:     out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    src/limuzin_grid_manager/ui/points_window.py
    339: def load_excel_path(self, path: Path) -> None:
    345:     result = import_points_from_excel(workbook_path)

## Interfaces and Dependencies

In `src/limuzin_grid_manager/app/project.py`, keep the public function `save_project_state(path: str | Path, state: ProjectState) -> Path`. Add a private helper with a stable name such as `_write_project_text_atomically(out_path: Path, text: str) -> None`. That helper must be the only write path for project JSON.

In `src/limuzin_grid_manager/ui/points_window.py`, define a new `PointsImportWorker(QObject)` alongside the existing `PointsExportWorker`. Use `finished = Signal(object)` so a `PointImportResult` can cross the Qt signal boundary without custom Qt type registration. Add `_import_thread`, `_import_worker`, and a UI-state helper such as `_set_import_running(running: bool) -> None`. The public method `load_excel_path(...)` should remain the entry point that the rest of the UI calls.

In `src/limuzin_grid_manager/app/runtime.py`, define stable startup helpers. The minimum interface should include a logging initializer and an exception-hook installer, for example `configure_runtime_logging() -> Path` and `install_exception_hooks() -> None`. `src/limuzin_grid_manager/__main__.py` must call them before `MainWindow()` is shown.

In `.github/workflows/ci.yml`, the primary job now runs Windows validation with `uv` across Python `3.11` and `3.12`. In `.github/workflows/release-windows.yml`, the primary job now builds the EXE artifact on Windows with Python `3.11` and uploads `dist\LIMUZIN_GRID_MANAGER.exe`. In `build_exe_windows.bat`, the future `v2.2.0` signing stage must still be additive and environment-variable-driven so normal unsigned local builds continue to work.

The tests added for this plan should use stable names so future contributors can find them quickly. Recommended additions are `test_save_project_state_is_atomic_when_replace_fails` in `tests/test_project.py`, `test_points_window_import_running_state_disables_controls` in `tests/test_ui.py`, and a focused runtime logging test in a new `tests/test_runtime.py` if the logging helpers become large enough to deserve direct coverage.

Revision note: this file was created on 2026-04-10 to turn the production-readiness audit into a staged, novice-readable ExecPlan that can be implemented release by release from `v2.1.0` to `v2.2.0`.
Revision note: updated on 2026-04-11 after implementing `v2.1.1` so the plan now records the completed atomic-save milestone, its validation evidence, and the decision to keep the helper local to `app/project.py`.
Revision note: updated on 2026-04-11 after implementing `v2.1.2` so the plan now records the completed responsive Excel import milestone, its UI-smoke coverage, and the decision to keep cancellation out of scope for this patch.
Revision note: updated on 2026-04-11 after implementing `v2.1.3` so the plan now records the completed crash-logging milestone, its runtime/UI diagnostics coverage, and the decision to centralize logging in `app/runtime.py`.
Revision note: updated on 2026-04-11 after implementing `v2.1.4` so the plan now records the completed GitHub Actions milestone, the release-discipline workflow changes, the `uv.lock` version-sync discovery, and the validation evidence for the new automation gate.
