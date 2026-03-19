# Performance Enhancements

This document summarizes the performance-oriented changes made so far across the FastAPI backend and the sibling `ambient-sound-analysis-ui` dashboard.

## API-side improvements

- Added request timing middleware in [app/main.py](/workspaces/orcasound/ambient-sound-analysis-api/app/main.py) to log endpoint latency and response size to `logs/api-timing.log`.
- Filtered out browser `/.well-known/...` probe noise from the timing log so it reflects real API traffic more clearly.
- Added lightweight response headers for aggregation/timeseries endpoints so timing logs can include `point_count`, `expected_point_count`, `time_count`, and `frequency_count` without parsing JSON bodies.
- Added `interval=auto` support for browser-oriented aggregation endpoints so they choose the finest allowed bucket that stays near the target point count.
- Chunked broadband aggregation reads month-by-month instead of attempting a single large raw read.
- Chunked PSD aggregation reads day-by-day instead of larger raw spans, reducing some of the worst long-window load behavior.
- Added in-process caching for repeated broadband and PSD aggregation requests in [app/services/get_aggregations.py](/workspaces/orcasound/ambient-sound-analysis-api/app/services/get_aggregations.py).
- Added in-process caching for repeated daily summary and daily broadband summary requests in [app/services/get_aggregations.py](/workspaces/orcasound/ambient-sound-analysis-api/app/services/get_aggregations.py).
- Aggregated the daily summary endpoint by time-of-day bucket instead of always returning 86,400 per-second points.
- Added an `interval` field to the daily summary response so callers can see which bucket size was used.
- Added validation to reject explicit daily-summary intervals that exceed the aggregation point cap.
- Normalized incoming request datetimes to naive UTC in [app/services/get_timeseries.py](/workspaces/orcasound/ambient-sound-analysis-api/app/services/get_timeseries.py), avoiding timezone-related failures that caused wasted retries and broken UI requests.

## Measured API wins

- Repeated `GET /aggregations/daily-summary` requests dropped from roughly `24.67s` to `0.016s` after caching.
- Repeated `GET /aggregations/daily-broadband-summary` requests dropped from roughly `11.67s` to `0.012s` after caching.
- Warm full-dashboard refreshes dropped to roughly `0.265s` once the expensive repeated summary calls were cached and the chart-fetch path was stabilized.

## UI-side improvements

- Replaced hard page failure on missing backend connectivity with an explicit API-offline state in the sibling `ambient-sound-analysis-ui` app.
- Added a Next.js same-origin proxy route at `ambient-sound-analysis-ui/app/api/[...path]/route.ts` so browser chart requests no longer depend on a separately forwarded host API port.
- Switched browser-side chart fetches from `http://localhost:8001` fallback to same-origin `/api`, while preserving env override support.
- Moved chart loading out of the critical server-render path so the page shell can render before expensive chart data finishes loading.
- Added client-side React Query hooks for chart loading, including the daily PSD summary and daily broadband summary.
- Hydration-gated the client queries so the server-render path no longer blocks on backend chart fetches.
- Changed the dashboard default window from `7d` to `24h` to reduce cold-start load and improve the initial PSD heatmap readability.
- Replaced PSD heatmap `interval=auto` requests in the UI with an explicit per-window mapping:
  - `1h -> 10s`
  - `6h -> 1m`
  - `24h -> 1m`
  - `7d -> 15m`
  - `30d -> 1h`
- Hooked the PSD daily summary day-count to the dashboard time-window filter instead of keeping it fixed.
- Fixed the PSD daily summary date helper so day-based summaries use the latest fully completed UTC day before the anchor timestamp, preventing empty one-day summaries.

## Dev environment improvements

- Added Node.js 20 into the API repo devcontainer so the sibling Next.js UI can run in the same containerized workspace.
- Updated the UI dev command to bind on `0.0.0.0` and use webpack in container development, avoiding the earlier Turbopack crash.
- Added explicit port-forwarding support for UI dev ports `3000` and `3001` in the devcontainer configuration.
- Persisted VS Code server and VS Code config directories on named volumes in the devcontainer to reduce rebuild/setup overhead.

## Remaining limits

- First-hit latency is still expensive after a FastAPI reload or restart because the aggregation caches are in-process only.
- Long-window PSD aggregation remains the dominant cold-path cost.
- The current timing log is request-level only; it does not yet break time down by internal aggregation step.
