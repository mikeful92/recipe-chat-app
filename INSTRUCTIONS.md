# INSTRUCTIONS.md

Follow these rules on **every** task in this repo.

## 1) Always use the repo virtual environment (REQUIRED)

Before running **any** command (`make`, `pytest`, `python`, etc.), you must be in the repo venv.

### Create venv (only if missing)

```bash
python -m venv .venv
```

### Activate venv (every new terminal / new agent session)

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
. .\.venv\Scripts\Activate.ps1
```

### Install deps (after activation)

```bash
python -m pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Verify venv is active (must show `.venv`)

```bash
python -c "import sys; print(sys.prefix)"
```

If this does not include `.venv`, stop and activate the venv.

## 2) Workflow rules

- Never commit secrets.
- Write tests first (TDD).
- Keep changes small and PR-sized.
- Run `make ci` and ensure it passes before finishing.

## 3) API & persistence notes

- `POST /generate` uses strict Pydantic schemas (`extra="forbid"`).
- Recipe generation is config-driven:
  - `RECIPE_GENERATOR=stub` (default deterministic behavior)
  - `RECIPE_GENERATOR=openai` (OpenAI Responses API with structured outputs)
  - `OPENAI_API_KEY` is required when OpenAI mode is enabled.
- UI generation (`POST /ui/generate`) uses the same generator selection path as `POST /generate`.
- If you change the recipe schema, update all three:
  - `app/schemas/recipe.py`
  - `app/api/generate.py`
  - `tests/test_generate.py`
- If generator behavior changes, also update:
  - `app/api/ui.py`
  - `tests/test_generator_openai.py`
  - `tests/test_generator_factory.py`
- Persistence is SQLite via stdlib `sqlite3` (`app/db/sqlite.py`).
- Saved recipe + notes routes:
  - `app/api/recipes.py`
  - `tests/test_recipes.py`
- If persistence behavior changes, update README API docs and persistence tests.
- Keep test runs deterministic: tests force stub generator mode via `tests/conftest.py`.

## 4) UI change guardrails

- Reuse existing UI primitives and tokens:
  - `app/static/styles.css`
  - `app/templates/components.html`
- Major UI pages and flows are covered by:
  - `tests/test_ui_pages.py`
  - `tests/test_ui.py`
- If UI structure/state behavior changes, update those tests first, then implement.

## 5) Multi-agent workflow (planner -> developer -> reviewer)

- Agent orchestration source of truth is `AGENTS.md` at repo root.
- Feature flow:
  - Planner writes `docs/plan-<feature-slug>.md`.
  - Developer implements against that plan and updates it if deviations are needed.
  - Reviewer writes `docs/review-<feature-slug>.md` and validates implementation vs plan.
- Each role must still comply with all rules in this file (venv, TDD, `make ci`, security).
