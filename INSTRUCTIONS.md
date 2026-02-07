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
