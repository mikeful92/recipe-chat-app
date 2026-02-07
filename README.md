# Recipe Chat App

Small FastAPI service for recipe generation.

## Endpoints

- `GET /health` -> `{"status": "ok"}`
- `POST /generate` -> returns a strict `Recipe` payload generated from request inputs

## Generate Request

```json
{
  "theme": "Mediterranean",
  "ingredients": ["chickpeas", "tomato", "olive oil"],
  "healthy": true,
  "quick_easy": true,
  "notes": "extra lemon"
}
```

All fields are optional except payload must be valid types. Unknown fields are rejected.

## Generate Response Shape

Top-level keys:
- `id` (uuid string)
- `title`
- `servings`
- `time_minutes`
- `difficulty`
- `ingredients` (`[{name, amount, unit, optional}]`)
- `steps` (`[{step, text, timer_minutes}]`)
- `substitutions` (`string[]`)
- `cook_mode` (`{ingredients_checklist: string[], step_cards: string[]}`)

## Run

```bash
make install
make dev
```

## Test

```bash
make test
make ci
```
