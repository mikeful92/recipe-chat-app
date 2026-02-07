# Recipe Chat App

A private, single-user recipe generator you can use like ChatGPT: provide a theme + optional constraints (ingredients, healthy, quick/easy), get a structured recipe back, and save the ones you like with notes. Built to be mobile-friendly (laptop + iPad/iPhone) and designed to sit behind a private access layer (e.g., Cloudflare Access) so you do not have to build auth in-app.

> Status: MVP in progress  
> Implemented: `/health`, `/generate` (stubbed deterministic recipe output)  
> Next: persistence (save recipes + notes) + cook mode UI

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
- **DB (next):** SQLite
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

### 3. Run the app

```bash
make dev
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

Deterministic stub generator (no OpenAI calls yet). Produces a recipe that matches the strict schema.

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

## Persistence (next milestone)

We will add SQLite-backed endpoints:

- `POST /recipes` save a recipe
- `GET /recipes` list saved recipes
- `GET /recipes/{id}` fetch a recipe
- `POST /recipes/{id}/notes` add a note/comment
- `GET /recipes/{id}/notes` list notes

Database path will be configurable via:

- `RECIPE_DB_PATH` (default: `data/recipes.db`)

---

## Security Model (planned deployment)

This app is intended to be reachable only through a private access layer (VPN-ish), e.g.:

- Cloudflare Tunnel + Cloudflare Access (SSO + MFA + allowlist only your identity)

The app itself will not store passwords. Secrets (OpenAI key, etc.) are server-side env vars only.

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

## Contributing (you + Codex)

We use a TDD-first workflow:

- Add/extend tests
- Implement minimal code to pass
- Refactor with tests green
- `make ci` must pass before committing

Codex instructions live in `.codex/` and/or `INSTRUCTIONS.md`.

---

## License

Private project (no license defined yet).
