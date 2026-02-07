# Development Instructions

Follow these on every task:

- Never commit secrets.
- Always add tests first (TDD).
- `make ci` must pass before finishing.
- Prefer small PR-sized changes.

## API Notes

- `POST /generate` uses strict Pydantic schemas (`extra="forbid"`).
- Current generator is deterministic stub logic (no OpenAI call yet).
- Keep schema updates in sync across:
  - `app/schemas/recipe.py`
  - `app/api/generate.py`
  - `tests/test_generate.py`
- Persistence is SQLite via stdlib `sqlite3` (`app/db/sqlite.py`).
- Saved recipe + notes routes live in:
  - `app/api/recipes.py`
  - `tests/test_recipes.py`
- If you change persistence behavior, update README API docs and recipe persistence tests.
