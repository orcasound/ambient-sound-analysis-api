# Agent Context

## Latest session update
- Current objective: keep the browser-oriented aggregation API stable while tightening diagnostics and docs for real frontend testing.
- What changed: request timing logs in `app/main.py` now ignore browser `.well-known/...` probe requests so `logs/api-timing.log` focuses on actual API traffic, `README.md` now uses the current `GET /aggregations/psd` route name instead of the stale `/aggregations/psd-heatmap` label, and timeseries/aggregation routes now set lightweight response headers so the timing log can include `point_count`, `expected_point_count`, `time_count`, and `frequency_count` without parsing JSON bodies. Aggregation endpoints now also support `interval=auto`, which picks the finest allowed bucket (`10s`, `1m`, `5m`, `15m`, `1h`, `1d`) that keeps the estimated point count at or below roughly 1000. Broadband and PSD aggregation responses are now cached in-process by request parameters so repeated identical long-window requests return quickly instead of rerunning the full chunked aggregation.
- Next step: continue frontend-oriented aggregation experiments, especially longer-window PSD tests and any additional logging or limits needed to understand cost/latency tradeoffs.
- Blockers/risks: long-window PSD aggregation remains expensive even with daily chunking, and the timing log is still total-request only rather than per-step breakdown.
- Branch and latest commit: `main` / `bb60eaa`

## Current objective
Stand up `ambient-sound-analysis-api` as a thin FastAPI layer around the `orcasound_noise` package from `ambient-sound-analysis`, with browser-friendly read-only GET endpoints over precomputed parquet-backed data.

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
- Do not expose raw audio / `ffmpeg` pipeline operations through the API.

## Current implemented direction
- Discovery and validation endpoints exist, including `/health`, `/hydrophones`, and `/options`.
- Raw timeseries endpoints exist for broadband and PSD.
- Browser-oriented aggregation endpoints exist for broadband and PSD, with fixed bucket choices and validation intended for frontend plotting.
- Request-timing middleware logs request cost to stdout and `logs/api-timing.log`.

## Important implementation notes
- `/options` archive scanning was tightened to count only parquet keys that match the requested hydrophone layout.
- `orcasound_lab` inventory is now accurate under that stricter scan.
- `sandbox` currently has no safely attributable partitioned parquet inventory under the present archive layout, so `/options?hydrophone=sandbox` returns an empty result.
- Raw `/timeseries/*` endpoints still enforce a 31-day limit.
- Aggregation endpoints bypass that raw-window cap so longer-window experiments are possible, but this does not make them cheap.
- Broadband aggregation now chunks raw reads month-by-month before merging aggregated buckets.
- PSD aggregation now uses smaller daily raw-data chunks than the earlier monthly version, but long-window PSD remains expensive.

## Devcontainer notes
- Reliable workflow:
  1. open `ambient-sound-analysis-api`
  2. reopen in container
  3. add sibling `ambient-sound-analysis` folder to the workspace from inside the container
- The devcontainer mount is intended to expose sibling repos under `/workspaces/...`.
- The devcontainer extension list includes `openai.chatgpt`, `ms-python.python`, `ms-python.vscode-pylance`, `ms-azuretools.vscode-docker`, and `charliermarsh.ruff`.

## Risks / blockers
- `ambient-sound-analysis` uses older scientific Python dependencies and is not compatible with Python `3.12`.
- The package may include code paths that require `ffmpeg`, but the API plan is to avoid those paths.
- Multi-root workspace + child-repo devcontainer behavior in VS Code is fragile; using the child repo as the container entrypoint is the stable path.
- Long-window aggregation still pays first-hit latency because it reads underlying timeseries before resampling.
- The archive layout is inconsistent across hydrophones, so validation and discovery behavior can vary by hydrophone.

## Clarifications
- Installing `orcasound_noise` from Git should also install its declared Python dependencies automatically.
- Git must be available in the container for pip Git URL installs.
- `ffmpeg` is a system dependency, not a Python dependency. It is only needed if the API actually exercises raw-audio conversion paths.
- `postCreateCommand` runs after container creation; it does not rebuild the image.

## Note on persistence
Repo files can preserve instructions and handoff context for future Codex sessions. They cannot force:
- previous chat thread history to persist across rebuilds
- VS Code extensions to persist unless the devcontainer config explicitly reinstalls them
