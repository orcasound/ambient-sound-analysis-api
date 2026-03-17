# Agent Context

## Latest session update
- Current objective: round out aggregation support with a true daily broadband endpoint and keep the daily-summary responses understandable.
- What changed: added `GET /aggregations/daily-broadband-summary` as a thin wrapper around `DailyNoiseAnalysis.create_broadband_daily_noise(...)`, with a small per-day response model and README documentation. The existing `/aggregations/daily-summary` remains the PSD-band daily-pattern endpoint with clearer explanatory fields. Verified the new broadband summary returns two points for `orcasound_lab` on `2020-01-01` through `2020-01-02`, and `python -m compileall app` still passes.
- Next step: commit the aggregation work, then choose whether the next feature is more aggregation surfaces, a browser-oriented visualization/downsampling endpoint, or both.
- Blockers/risks: `/aggregations/daily-summary` is still a very large payload for browser use and contains upstream gaps/NaNs, while the new broadband daily endpoint is much lighter but answers a different question.
- Branch and latest commit: `main` / `21452fa`

## Current objective
Stand up `ambient-sound-analysis-api` as a thin FastAPI layer around the `orcasound_noise` package from `ambient-sound-analysis`, starting with simple read-only GET endpoints over precomputed parquet-backed data.

## Current architecture decisions
- Use Python `3.9.x` for compatibility with `ambient-sound-analysis` package dependencies.
- Use a dedicated devcontainer for this repo.
- Keep a separate production `Dockerfile` in the repo root and a separate development Dockerfile under `.devcontainer/`.
- In the devcontainer, install packages directly into the container Python; do not create a `venv` inside the container.
- Keep API dependencies minimal:
  - `fastapi`
  - `uvicorn[standard]`
  - `orcasound_noise @ git+https://github.com/orcasound/ambient-sound-analysis.git`
- Prefer using `NoiseAccessor` and already-processed S3 parquet files first.
- Do not start by exposing raw audio / ffmpeg pipeline operations through the API.

## Devcontainer notes
- The reliable workflow is:
  1. open `ambient-sound-analysis-api`
  2. reopen in container
  3. add sibling `ambient-sound-analysis` folder to the workspace from inside the container
- The devcontainer mount is intended to expose sibling repos under `/workspaces/...`.
- The devcontainer extension list now includes `openai.chatgpt`, `ms-python.python`, `ms-python.vscode-pylance`, `ms-azuretools.vscode-docker`, and `charliermarsh.ruff`.

## What changed so far
- Created a production `Dockerfile` in repo root.
- Created a development Dockerfile in `.devcontainer/`.
- Added `.devcontainer/devcontainer.json`.
- Added a minimal `requirements.txt`.
- Implemented `app/main.py` with FastAPI app wiring.
- Added `/health` and `/options` endpoints.
- Added an options service that validates hydrophone names and falls back around malformed S3 object names.
- Added `openai.chatgpt` to the devcontainer extension list.
- Documented the setup process and architectural reasoning in the blog draft in `adrmac.github.io`.

## Immediate next steps
1. Run the API:
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
2. Verify:
   - `GET /health`
   - `GET /options?hydrophone=bush_point`
3. Confirm whether `/options` should return non-empty values for the target hydrophones.
4. Add bounded timeseries endpoints for broadband / PSD access.

## Risks / blockers
- `ambient-sound-analysis` uses older scientific Python dependencies and is not compatible with Python `3.12`.
- The package may include code paths that require `ffmpeg`, but the initial API plan is to avoid those paths.
- Multi-root workspace + child-repo devcontainer behavior in VS Code is fragile; using the child repo as the container entrypoint is the stable path.
- `NoiseAccessor.get_options()` can fail on malformed S3 object names; the API currently works around this by skipping invalid keys.

## Clarifications from prior reasoning
- Installing `orcasound_noise` from Git should also install its declared Python dependencies automatically.
- Git must be available in the container for pip Git URL installs.
- `ffmpeg` is a system dependency, not a Python dependency. It is only needed if the API actually exercises raw-audio conversion paths.
- `NoiseAccessor` appears to use S3/parquet access paths and is the preferred starting integration point.
- `postCreateCommand` runs after container creation; it does not rebuild the image. It is a convenience for early development, not an image-layer dependency mechanism.

## Branch / commit
- Branch: `move-stuff`
- Latest commit at handoff: `49d1c5a`

## Note on persistence
Repo files can preserve instructions and handoff context for future Codex sessions. They cannot force:
- previous chat thread history to persist across rebuilds
- VS Code extensions to persist unless the devcontainer config explicitly reinstalls them
