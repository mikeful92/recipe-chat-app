# Recipe Chat App

A private, single-user recipe generator you can use like ChatGPT: provide a theme + optional constraints (ingredients, healthy, quick/easy), get a structured recipe back, and save the ones you like with notes. Built to be mobile-friendly (laptop + iPad/iPhone) and designed to sit behind a private access layer (e.g., Cloudflare Access) so you do not have to build auth in-app.

> Status: MVP in progress  
> Implemented: `/health`, `/`, `/ui/generate`, `/recipes/ui`, `/recipes/ui/{id}`, `/cook/{id}`, `/generate`, `/recipes`, `/recipes/{id}`, `/recipes/{id}/notes`

---

## Features (planned)

### Required

- Generate recipe from optional parameters (theme, ingredients on-hand, healthy, quick/easy)
- Strict JSON recipe schema (predictable output)
- Save recipes you like
- Add notes/comments to saved recipes
- Cook Mode view (only the info you need while cooking)
- Responsive web UI (works on laptop + iPad/iPhone)

### Nice-to-have

- "Remix" a saved recipe (start a new generation using an existing recipe as context)
- Grocery list aggregation for selected recipes
- Offline-ish cook mode via caching
- Dish image generation (de-prioritized due to cost)

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **Validation:** Pydantic (strict recipe schema)
- **Testing:** pytest (TDD workflow)
- **Lint/Format:** Ruff
- **Type checking:** mypy or pyright (depending on repo config)
- **DB:** SQLite (`sqlite3` stdlib)
- **CI:** GitHub Actions (runs lint + type checks + full test suite)

---

## Local Development (WSL/Linux/macOS)

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2. Install dependencies

```bash
pip install -r requirements-dev.txt
```

This step is required before running `make ci` or `make dev`.

### Environment variables

- `RECIPE_GENERATOR`:
  - `stub` (default): deterministic local generator
  - `openai`: OpenAI-backed generator
- `OPENAI_MODEL`:
  - Optional model name for OpenAI generation
  - Default: `gpt-4.1-mini`
- `OPENAI_API_KEY`:
  - Required when `RECIPE_GENERATOR=openai`
  - App startup fails if missing in OpenAI mode
- `RECIPE_DB_PATH`:
  - Optional SQLite DB path
  - Default: `data/recipes.db`

### 3. Run the app

```bash
make dev
```

If you want a custom port (for example `8080`):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Open:

- Health: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>

### 4. Run the full quality gate

```bash
make ci
```

---

## API Overview (current)

### `GET /health`

Returns:

```json
{"status":"ok"}
```

### `POST /generate`

Generator backend is selected by `RECIPE_GENERATOR`:

- `stub` (default): deterministic local generator
- `openai`: OpenAI Responses API with structured outputs

Both return a strict `Recipe` schema response.

Runtime behavior:

- OpenAI mode applies request timeout + retry/backoff for transient API failures.
- OpenAI responses are validated against `Recipe` and retried once if schema validation fails.
- `id` is generated server-side.
- Non-retryable generator failures currently return HTTP `500`.

Example:

```bash
curl -sS -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"theme":"Italian","ingredients":["chicken","spinach"],"healthy":true,"quick_easy":true}'
```

### Recipe schema (high level)

The API returns a `Recipe` JSON object containing:

- `id`, `title`, `servings`, `time_minutes`, `difficulty`
- `ingredients[]` (`name`, `amount`, `unit`, optional)
- `steps[]` (`step`, `text`, `timer_minutes?`)
- `substitutions[]`
- `cook_mode` (`ingredients_checklist[]`, `step_cards[]`)

Full schema lives in: `app/schemas/recipe.py`

---

## Persistence API

SQLite-backed endpoints are implemented:

- `POST /recipes` save a recipe body (`Recipe`), returns `{"id":"..."}`
- `GET /recipes` list saved recipes (`id`, `title`, `created_at`) newest first
- `GET /recipes/{id}` fetch full saved recipe
- `POST /recipes/{id}/notes` save note body `{"note_text":"..."}`, returns `{"note_id":"..."}`
- `GET /recipes/{id}/notes` list notes (`note_id`, `note_text`, `created_at`) newest first

Behavior:

- Duplicate recipe `id` on save returns `409`
- Unknown recipe id returns `404` for recipe fetch and note endpoints

Database path is configurable via:

- `RECIPE_DB_PATH` (default: `data/recipes.db`)

Initialization:

- DB schema is initialized at app startup
- Recipes are stored as JSON strings in `recipes.recipe_json`

---

## Security Model (planned deployment)

This app is intended to be reachable only through a private access layer (VPN-ish), e.g.:

- Cloudflare Tunnel + Cloudflare Access (SSO + MFA + allowlist only your identity)

The app itself will not store passwords. Secrets (OpenAI key, etc.) are server-side env vars only.

Local secret handling:

- `.env` is ignored by git.
- `.env.example` is safe to commit and should not contain secrets.
- If a key is ever exposed in logs/chat/screenshot history, rotate it immediately.

---

## Repo Commands

```bash
make install   # install dev deps
make dev       # run local server
make test      # run pytest
make lint      # ruff check
make fmt       # ruff format
make type      # type check (mypy/pyright)
make ci        # lint + type + tests
```

---

## UI System Notes

The UI is server-rendered (Jinja templates) with a small tokenized CSS system.

- Global tokens and primitives: `app/static/styles.css`
- Shared template macro(s): `app/templates/components.html`
- Form submit loading affordance: `app/static/ui.js`
- Cook mode interactions (step nav + checklist persistence): `app/static/cook.js`

When updating UI, keep class usage aligned with the shared primitives (`btn`, `input`, `textarea`, `card`, `panel`, `page-header`) instead of creating one-off styles.

---

## Contributing (you + Codex)

We use a TDD-first workflow:

- Add/extend tests
- Implement minimal code to pass
- Refactor with tests green
- `make ci` must pass before committing

Codex instructions live in `.codex/` and/or `INSTRUCTIONS.md`.

Test note:

- Test suite forces `RECIPE_GENERATOR=stub` for determinism, so CI does not depend on external APIs.

---

## Future Improvements

- Add explicit API error contract for generation failures (e.g., typed `502/503` responses instead of generic `500`).
- Add request tracing IDs and structured logging fields for easier production debugging.
- Support `.env` loading via app config to reduce shell setup friction in local dev.
- Add optional fallback mode: if OpenAI fails, return stub output with a warning banner.
- Add model guardrails for cost controls (request budgets, per-day caps, and model allowlist).
- Add end-to-end integration test (mock server) for OpenAI path with realistic Responses API payloads.

---

## License

Private project (no license defined yet).
