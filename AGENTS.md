# Repository Guidelines

## Project Structure & Module Organization

- `front/`: current user-facing static site. HTML pages live at the top level, shared scripts in `front/js/`, styles in `front/css/`, and product/branding assets in `front/images/`.
- `backend/`: FastAPI backend skeleton. App entrypoint is `backend/app/main.py`; API routers live under `backend/app/api/`; tests live in `backend/tests/`.
- `tests/e2e/`: reserved for browser and smoke tests.
- `docs/`: implementation artifacts such as `current_state.md`, `page_api_matrix.md`, and `testing.md`.
- `memory-bank/`: persistent project context. Read `design.md`, `implementation_plan.md`, `progress.md`, and `architecture.md` before major changes.

## Build, Test, and Development Commands

- Install/update project-local deps:
  `UV_CACHE_DIR=.uv-cache uv pip install --python .venv/bin/python -r backend/requirements-dev.txt`
- Collect tests:
  `UV_CACHE_DIR=.uv-cache uv run --with pytest pytest --collect-only`
- Run backend tests:
  `.venv/bin/python -m pytest backend/tests -q`
- Start the API locally:
  `.venv/bin/python -m uvicorn backend.app.main:app --reload`
- Validate Compose config:
  `docker compose config --quiet`

Use the project-local `.venv` and `.uv-cache`; do not rely on global Python tooling.

## Coding Style & Naming Conventions

- Python targets `py311`; keep code compatible with the current `ruff.toml`.
- Use 4-space indentation and ASCII by default.
- Prefer clear module names: `health.py`, `router.py`, `test_health.py`.
- Keep routers, services, and future models separated by responsibility; avoid page-specific hacks in shared modules.
- Run linting with `ruff check .` before handoff.

## Testing Guidelines

- Frameworks: `pytest`, `pytest-asyncio`, `httpx`.
- Test files must match `test_*.py`; async API tests should use `httpx.ASGITransport`.
- Add or update tests with every backend change. For frontend changes, include at least a smoke-level validation path or manual verification note.

## Commit & Pull Request Guidelines

- Git history is currently minimal (`前端`), so there is no strong existing convention. Prefer short imperative commits with scope, for example: `backend: add health route` or `docs: update page API matrix`.
- PRs should include:
  - a concise summary,
  - linked task/step from `memory-bank/implementation_plan.md`,
  - validation commands run,
  - screenshots for visible frontend changes.

## Security & Workflow Notes

- Do not hardcode secrets; use env-based configuration once `backend/app/core/` exists.
- Do not reintroduce `localStorage` as the source of truth for orders, cart, membership, or auth.
- Update `memory-bank/progress.md` and `memory-bank/architecture.md` after meaningful structural changes.

每一步验证通过后，打开 progress.md 记录你做了什么供后续开发者参考，再把新的架构洞察添加到 architecture.md 中解释每个文件的作用。并且进行git提交，禁止使用rm相关的任何命令，只允许通过git回滚，所以要及时提交git