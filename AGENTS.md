# AGENTS.md

Canonical agent-orchestration policy for this repo.

## Source of truth and sync

- `AGENTS.md` (this file) is the source of truth for multi-agent workflow.
- `INSTRUCTIONS.md` is the source of truth for engineering/runtime guardrails.
- `.codex/AGENTS.md` must stay byte-for-byte synced with this file for tool compatibility.

## Role pipeline

Use this strict handoff sequence for feature work:

1. Planner
2. Developer
3. Reviewer

Do not skip a role unless the user explicitly asks to.

## Planner contract

When user gives a feature, planner must create `docs/plan-<feature-slug>.md` with:

- Problem statement and constraints
- In-scope / out-of-scope
- Design approach and tradeoffs
- File-level change map
- Test plan (tests to add/update first)
- Step-by-step implementation tasks
- Risks and rollback notes
- Definition of done

Planner output is implementation-ready and should avoid vague tasks.

## Developer contract

Developer must implement from `docs/plan-<feature-slug>.md`:

- Follow TDD and repo guardrails in `INSTRUCTIONS.md`
- If deviating from plan, update the plan in the same commit with rationale
- Keep changes scoped to plan tasks
- Run `make ci` before finishing
- Summarize plan coverage in PR/hand-off notes

## Reviewer contract

Reviewer must create `docs/review-<feature-slug>.md` and verify:

- Implementation matches plan tasks and acceptance criteria
- Any deviations are documented and justified
- Tests cover changed behavior and failure paths
- Security, secrets handling, and API/schema impacts are addressed
- Code quality and maintainability meet repo standards

Reviewer output format:

- Findings by severity with file references
- Test and risk assessment
- Explicit pass/fail recommendation

## Minimal handoff checklist

- Planner done: `docs/plan-<feature-slug>.md` exists and is actionable
- Developer done: code + tests merged with plan updates if needed
- Reviewer done: `docs/review-<feature-slug>.md` recorded with verdict
