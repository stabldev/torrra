# AGENTS.md

## Setup and commands

- This project uses `uv` and a `src/` layout. Run `uv sync` to install runtime + dev deps, then `uv run torrra` (or `uv run python -m torrra`).
- Full test suite: `uv run pytest` (~330 tests). CI runs this on Python 3.10–3.14, so all code must stay 3.10-compatible.
- Focused test: `uv run pytest tests/test_core_config.py -k config_get`.
- CI (`.github/workflows/ci.yml`) only runs pytest on Linux. Lint/format are not in CI.
- Ruff is not in the `dev` dependency group; the pinned version is in `.pre-commit-config.yaml`. Use `uvx ruff@0.17.2 check --fix .` and `uvx ruff@0.17.2 format .` (no Ruff config exists, so defaults apply).
- Snapshots: `uv run pytest tests/snapshots --snapshot-update`, then review `.raw` diffs under `tests/snapshots/__snapshots__/`. Never hand-edit snapshots.
- `uv.lock` and `requirements.txt` are generated. After editing `pyproject.toml`, run `uv lock`; regenerate `requirements.txt` with `uv export --frozen --output-file=requirements.txt`.
- No runnable typecheck step is configured; `[tool.ty]` exists in `pyproject.toml` but `ty` is not a dev dependency.
- Version bumps use `uv run bump-my-version bump <part>`; it updates `pyproject.toml` and `flake.nix` and refreshes snapshots/lock. Do not hand-edit versions.

## Architecture

- CLI entrypoint is `torrra.__main__:cli`. Heavy TUI/libtorrent imports are intentionally deferred inside command handlers; preserve this so `--version` and `config` commands stay fast.
- `utils/indexer.py` validates config, healthchecks the indexer, and constructs `TorrraApp`. `app.py` routes to `WelcomeScreen` or `HomeScreen`; `screens/` holds full-screen flows, `widgets/` holds embedded UI, and `app.tcss` is loaded via `utils/fs.get_resource_path`.
- `core/` holds non-UI logic: `config.py` (TOML + schema migrations), `db.py`/`torrent.py` (SQLite), `download.py` (libtorrent), `cache.py` (diskcache), `results.py` (client-side sort/filter), `updater.py` (release notifications). `indexers/` contains Jackett/Prowlarr adapters.
- Update checks are notification-only and run on every TUI mount; they must never install packages or modify package-manager-owned files. Tests stub `TorrraApp._check_for_updates`.
- New indexers subclass `BaseIndexer` and also require wiring in `_types.IndexerName`, `utils/indexer.py`/`__main__.py`, and `torrra.spec` `hiddenimports`.
- New runtime data files must be added to `torrra.spec` `datas` for the standalone PyInstaller binary.
- `get_config()`, `get_torrent_manager()`, and `get_download_manager()` are process-wide `@lru_cache` singletons. Tests must call `.cache_clear()` after monkeypatching path globals.
- Add persisted torrent fields as both a `CREATE TABLE` column and an `ALTER TABLE` migration in `core/db.py`. Config schema changes go through `MIGRATIONS`/`CURRENT_SCHEMA_VERSION` in `core/config.py`.

## Testing

- Pytest uses `asyncio_mode=auto` and `pythonpath=src`; async tests need no decorator.
- The autouse `isolated_db` fixture redirects config, DB, and download dirs into `tmp_path` and clears singletons. Don't touch the real user config/DB in tests.
- `libtorrent` is imported at module load. Mock handles/session state; tests don't use a real swarm. HTTP is mocked with `respx`; tests make no network calls.
- Textual tests use `app.run_test()`. Snapshot tests use `snap_compare` and deterministic `SessionStats`; UI/layout/shortcut changes usually require snapshot updates.
- For cache tests, construct a `Cache(tmp_path)` as in `tests/test_core_cache.py`; the module-level cache points at the real user cache directory.

## Gotchas

- Python 3.10 support: use `torrra.utils.helpers.get_tomllib()` instead of importing `tomllib` directly; avoid 3.11+-only APIs.
- Download paths must be absolute. Use `core.paths.normalize_download_path`/`prepare_download_path`; don't accept or create relative paths.
- Configuration writes go through `Config.set` so booleans, numbers, and speed limits are coerced and saved; reading a path key expands `~` and environment variables.
