# ~/.codex/AGENTS.md

## Working agreements
- Follow INSTRUCTIONS.md in the repo (it overrides these if conflicting).
- Use a TDD loop: tests first, then code, then refactor.
- After any change, run: `make ci`.
- Keep changes small and focused; avoid unrelated refactors.
- Do not add new production dependencies without asking.
- Never commit secrets. Never print secrets.
- Prefer stdlib + existing deps (FastAPI/Pydantic/pytest/ruff).
