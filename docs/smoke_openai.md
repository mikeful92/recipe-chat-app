# OpenAI Manual Smoke Test (Not in CI)

This smoke test is manual only. Do not add it to `pytest` or CI workflows.

## Preconditions

1. Real key available in shell as `OPENAI_API_KEY`.
2. Run outside automated test flow.

## Commands

```bash
source .venv/bin/activate
export RECIPE_GENERATOR=openai
export OPENAI_API_KEY=YOUR_REAL_KEY
export OPENAI_FALLBACK_TO_STUB=0
make dev
```

```bash
curl -sS -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"theme":"Cozy winter pasta","ingredients":["mushroom","garlic","cream"],"quick_easy":false,"healthy":false}' | jq
```

## Expected Results

1. HTTP 200.
2. JSON includes `dish_summary`.
3. `dish_summary` is concise and reads like 1-3 sentences.
4. Save via UI flow (`/ui/generate` -> Save), then confirm summary appears above ingredients on `/recipes/ui/{id}` and `/cook/{id}`.
5. No part of this smoke test is added to `pytest` or CI workflow.
