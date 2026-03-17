# AGENTS.md

## Purpose
Repo-level instructions for coding agents working in `ambient-sound-analysis-api`.

## Session Start
- At the start of each new session, read `AGENTS.md` and `docs/agent-context.md` before making changes.
- If `docs/agent-context.md` is missing, create it before proceeding.

## Continuity
- Update `docs/agent-context.md` at each milestone and at the end of every task.
- Include:
  - current objective
  - what changed
  - next step
  - blockers/risks
  - branch and latest commit

## Working Assumptions
- This repo is a FastAPI app intended to wrap the `orcasound_noise` package from `ambient-sound-analysis`.
- Target Python runtime is `3.9.x` for compatibility with `ambient-sound-analysis`.
- In the devcontainer, do not create a separate `venv`; install dependencies into the container Python.
- Keep API dependencies minimal. Add only direct app dependencies plus the `orcasound_noise` package dependency when needed.
- Prefer starting with thin GET endpoints over already-processed parquet accessors, not raw audio / ffmpeg processing.

## Current Direction
- Use the child-repo `.devcontainer` in `ambient-sound-analysis-api`.
- Open `ambient-sound-analysis-api` first, reopen in container, then add sibling `ambient-sound-analysis` to the workspace after the container is running.
- Near-term endpoint plan:
  1. `/health`
  2. `/options` via `NoiseAccessor.get_options()`
  3. bounded timeseries endpoints built on `NoiseAccessor`

## Note
- Repo files can preserve instructions and handoff context, but cannot preserve chat thread state or VS Code extension state across container rebuilds by themselves.
