# Agent Context

## Latest session update
- Current objective: prepare the sibling UI repo for sharing by replacing the starter README with a real local-development guide tied to the companion API repo.
- What changed: rewrote `/workspaces/orcasound/ambient-sound-analysis-ui/README.md` to explain that the UI is not standalone and should be used together with `ambient-sound-analysis-api`. The new README documents the recommended workflow through the API repo devcontainer, required local dependencies, how to start the FastAPI backend and Next.js frontend, the current proxy and port model (`/api` through Next to `API_BASE_URL`, default `http://127.0.0.1:8000`), and common troubleshooting steps.
- Next step: review the new UI README before publishing the repo and adjust any repo-URL-specific wording once the final org/visibility decision is made.
- Blockers/risks: the README intentionally reflects the current local/devcontainer workflow, not a polished hosted deployment story. If the architecture later drops the proxy or gains hosted environments, the doc will need a corresponding update.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: keep the broadband daily average on the shared x-axis grid while rendering it as filled daily bars instead of a line.
- What changed: updated `/workspaces/orcasound/ambient-sound-analysis-ui/components/charts/broadband-daily-summary-chart.tsx` to render a Plotly bar trace rather than a scatter line. Each bar is centered at midday for its represented UTC day and given a full-day width so it fills the aligned date column while preserving the explicit shared x-axis range. Verified with `npm run lint` and `npm run build` in `ambient-sound-analysis-ui`.
- Next step: refresh the dashboard and confirm the broadband daily average now renders as one filled bar per day while still lining up vertically with the PSD heatmap and broadband timeseries grid.
- Blockers/risks: for the one-day case, the single bar now occupies the full selected day column by design; if that feels too visually heavy, bar opacity or width can be tuned later without changing the shared-axis approach.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: align the x-axis grid across the PSD heatmap, broadband timeseries, and broadband daily average so dates line up vertically.
- What changed: updated the sibling UI chart components so all three charts now use explicit x-axis ranges instead of Plotly autorange padding. `/workspaces/orcasound/ambient-sound-analysis-ui/components/charts/broadband-timeseries-chart.tsx` now pins `xaxis.range` to `data.start`/`data.end`, `/workspaces/orcasound/ambient-sound-analysis-ui/components/charts/psd-heatmap-chart.tsx` now pins the same range and moves the colorbar to a horizontal legend below the plot so the time axis can span the full chart width, and `/workspaces/orcasound/ambient-sound-analysis-ui/components/charts/broadband-daily-summary-chart.tsx` now derives an explicit date range from `start_date` and `num_days` so the daily chart shares the same left/right axis edges as the other windowed charts. Verified with `npm run lint` and `npm run build` in `ambient-sound-analysis-ui`.
- Next step: refresh the dashboard and visually confirm that the three x-axes now line up for `30d`, `7d`, `24h`, `6h`, and `1h`, with the heatmap colorbar rendered below the plot.
- Blockers/risks: the daily broadband chart now uses the full selected window range, which improves alignment but leaves some empty edge space around the single-point case by design.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: make the broadband daily average respond to the dashboard time-window filter instead of staying fixed at 30 days.
- What changed: updated the sibling UI fetch path so the broadband daily endpoint now uses the same day-count mapping as the PSD daily summary: `30d -> 30`, `7d -> 7`, and `24h`/`6h`/`1h -> 1`. This touched `/workspaces/orcasound/ambient-sound-analysis-ui/lib/api/client.ts`, `/workspaces/orcasound/ambient-sound-analysis-ui/lib/api/server.ts`, `/workspaces/orcasound/ambient-sound-analysis-ui/hooks/use-daily-broadband-summary.ts`, and `/workspaces/orcasound/ambient-sound-analysis-ui/components/dashboard/dashboard-shell.tsx`. The chart card text now refers to a daily broadband average over the selected day window, and sub-day windows intentionally show a single-day result, which may be a single point. Verified with `npm run lint` and `npm run build` in `ambient-sound-analysis-ui`.
- Next step: refresh the dashboard and confirm the broadband daily average switches between `30`, `7`, and `1` day windows along with the filter, with `24h`/`6h`/`1h` showing the expected single-day output.
- Blockers/risks: the chart component still renders a line+marker trace, so the `1`-day case naturally collapses to a single point; that is expected, but if product wants a different presentation for one-point windows, that would be a separate UI refinement.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: fix the PSD heatmap x-axis clipping bug that showed only 26 time buckets regardless of the selected window.
- What changed: traced the chart bug to the sibling UI heatmap component rather than the API data. The API returns PSD values shaped as `[time][frequency]`, but Plotly heatmaps expect `z` to be shaped as `[y][x]`. Because the chart was configured with `x=time` and `y=frequency` while passing the untransposed matrix, Plotly treated the 26 frequency columns as the x-axis length and clipped the time axis accordingly. Updated `/workspaces/orcasound/ambient-sound-analysis-ui/components/charts/psd-heatmap-chart.tsx` to transpose the PSD matrix before rendering. Verified with `npm run lint` and `npm run build` in `ambient-sound-analysis-ui`.
- Next step: refresh the dashboard and confirm the PSD heatmap x-axis now spans the full selected window for `24h`, `7d`, `6h`, and `1h`.
- Blockers/risks: none identified beyond standard browser cache/reload behavior; this was a presentation bug, not an API data bug.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: answer from the upstream repo whether `orcasound_noise` can expose a more efficient coarse PSD read for long windows instead of forcing the API to load near full-resolution PSD and downsample it.
- What changed: inspected the upstream accessor and file-connector code and updated [upstream-notes.md](/workspaces/orcasound/ambient-sound-analysis-api/upstream-notes.md). The current answer is: only in principle, not with the present implementation and `orcasound_lab` archive inventory. `NoiseAccessor.create_df()` and `S3FileConnector.get_files()` both select files by exact `delta_t` and exact band suffix, and the discovered `orcasound_lab` PSD options currently show only `3oct @ 1s`. That means the package cannot currently perform a truly efficient coarse PSD read unless the archive gains precomputed coarser PSD products or the package adds a new lazy/streaming coarse-read path.
- Next step: if we open an upstream discussion, the concrete request should be either additional archived coarse PSD resolutions or a new accessor API that can aggregate finer parquet data more efficiently than today's full-resolution read path.
- Blockers/risks: this conclusion is based on the current archive options and current accessor implementation; it could change if the archive inventory or package API changes.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: document the remaining PSD heatmap performance findings and the conclusion about API-side aggregation versus Plotly-side aggregation.
- What changed: expanded [upstream-notes.md](/workspaces/orcasound/ambient-sound-analysis-api/upstream-notes.md) with the observed PSD heatmap window-switch timings (`24h` about `30.5s` cold / `12.2s` warm, `7d` about `63.3s`, `30d` about `226.1s`, `6h` about `7.2s`, `1h` about `6.4s`) and the inference that raw PSD loading dominates runtime more than final bucket count or browser rendering. Also documented the conclusion that API-side aggregation still appears justified: the current Plotly heatmap path consumes a matrix we precompute, and Plotly’s old `transforms` aggregation path is deprecated, so relying on Plotly for core resampling would not be a stable replacement for server-side downsampling.
- Next step: if we continue the profiling, focus on the upstream PSD load path first, especially whether `orcasound_noise` can expose a more efficient coarse-resolution read for long windows instead of forcing the API to load near full-resolution daily PSD chunks and then resample them.
- Blockers/risks: the Plotly conclusion is based on the current Plotly.js documentation and our present heatmap architecture; if we later switch charting libraries or rendering strategy, that tradeoff should be revisited.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: interpret the remaining time-window switching performance now that the dashboard requests are stable again, especially separating PSD heatmap slowness from daily-summary behavior.
- What changed: reviewed the live `logs/api-timing.log` timings from the dashboard window-switch tests. The pattern is now clear: `/aggregations/daily-summary` stays roughly flat at about `25s` for `1d`, `7d`, and `30d` cold loads, then drops to a few milliseconds on repeats because of the in-process cache. `/aggregations/psd` scales much more strongly with window length: about `12.2s` for a warm `24h` request, about `63.3s` for `7d`, about `226.1s` for `30d`, and about `6.4-7.2s` for `1h`/`6h`. Because the `7d` and `30d` PSD responses return similar final payload sizes (`649` vs `687` time buckets) yet differ massively in runtime, the dominant cost appears to be upstream raw PSD loading per daily chunk rather than our final response bucketing or chart payload size alone.
- Next step: if we want to optimize further, profile the PSD heatmap path in three pieces: upstream `NoiseAccessor.create_df()` load time per chunk, API-side resample/merge time, and browser-side Plotly render time. The likely highest-leverage improvements are upstream-side or cache/persistence changes rather than more frontend tweaking.
- Blockers/risks: the current evidence strongly suggests upstream/raw-read cost dominates, but it does not yet provide a precise percentage breakdown between package I/O, DataFrame resampling, JSON serialization, and browser rendering. We should treat that as a reasoned inference from timings, not a completed profile.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: document the investigation into the PSD daily summary versus broadband daily summary scale mismatch and decide whether it warrants an upstream maintainer conversation.
- What changed: inspected the local API wrapper plus the sibling `ambient-sound-analysis` package implementation and added [upstream-notes.md](/workspaces/orcasound/ambient-sound-analysis-api/upstream-notes.md). The note records that `GET /aggregations/daily-summary` is a PSD-band daily-pattern view that our wrapper reduces with an arithmetic mean across dB-valued bands, while `GET /aggregations/daily-broadband-summary` comes from the package’s separate broadband product. A direct package comparison for `orcasound_lab` on `2021-10-31` showed materially different scales (`~1.40` broadband daily average, `~-11.45` PSD-band arithmetic mean, `~5.00` PSD energy-sum experiment), which supports the conclusion that the mismatch is mainly semantic rather than a transport bug. The note also identifies one upstream question worth raising: whether the package intentionally generates broadband from an amplitude-summed path that is not meant to be directly comparable with PSD-band rollups.
- Next step: if we decide to contact `orcasound_noise` maintainers, use `upstream-notes.md` as the basis for a focused question about broadband/PSD comparability and the intended broadband math. Separately, keep the dashboard wording clear that the PSD daily summary is not a broadband metric.
- Blockers/risks: the upstream note intentionally frames the broadband-math point as a question rather than a confirmed defect; we have enough evidence to justify asking, but not enough to assert the implementation is wrong without maintainer input.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: stop the dashboard’s remaining cold-load `503` responses after the first proxy-timeout fix proved insufficient.
- What changed: the FastAPI timing log still showed successful cold backend responses while the browser proxy produced repeated `503`s, and the failing `/aggregations/daily-summary` requests often never appeared in the FastAPI log at all. That indicated a frontend/proxy overload pattern rather than a backend status-code bug. Updated sibling repo `ambient-sound-analysis-ui` so `DashboardShell` now stages the four hydration-time queries instead of firing them all concurrently: daily broadband summary, then broadband, then PSD daily summary, then PSD heatmap. Also disabled React Query retries in all four dashboard hooks so one proxy failure no longer automatically fans out into duplicate long-running requests. Verified with `npm run lint` and `npm run build` in `ambient-sound-analysis-ui`.
- Next step: restart or refresh the Next dev server and confirm the dashboard now issues the chart requests sequentially and no longer produces duplicate `503` lines during a cold load after API restart.
- Blockers/risks: this favors stability over total cold-load time. The full dashboard may take longer end-to-end because the heavy requests are serialized, but it should stop overwhelming the proxy/dev server. If failures still occur even with serialized loading, the next diagnostic step is capturing the exact `/api/...` `503` body from the browser or reproducing against the live Next dev port while it is running.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: stop the dashboard’s remaining cold-load `503` responses after the container rebuild.
- What changed: traced the failing browser requests to the sibling Next.js proxy route rather than FastAPI itself. Direct backend calls still completed successfully, but cold `/aggregations/psd` and `/aggregations/daily-summary` runs can take longer than 30 seconds, which caused the Next route handler at `/workspaces/orcasound/ambient-sound-analysis-ui/app/api/[...path]/route.ts` to fail before the upstream response arrived. Updated that proxy route to export `maxDuration = 300`, apply an explicit 5-minute fetch timeout, and forward upstream response headers/status directly. Verified with `npm run lint` and `npm run build` in `ambient-sound-analysis-ui`.
- Next step: reload or restart the Next dev server if needed, then retry the dashboard and confirm the previous cold-path `503` responses now complete as `200` responses instead of being cut off around the 30-second mark.
- Blockers/risks: this fixes the synthetic proxy-side `503`s but does not make the underlying cold PSD/daily-summary computations fast; the first request after an API restart can still take tens of seconds. If that remains unacceptable, the next step is backend optimization or persistent caching rather than more proxy changes.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: fix the dashboard time-window behavior so `24h` shows a full day and `6h`/`1h` no longer fail on invalid post-coverage windows.
- What changed: traced the issue in `logs/api-timing.log`. The dashboard had been anchoring chart windows to `2021-11-01T07:00:00Z`, which made `24h` span only `07:00` to the prior `23:55` in practice and caused `6h`/`1h` broadband and PSD requests to land entirely in a no-data gap, returning `400`. Updated sibling repo `ambient-sound-analysis-ui` so `app/page.tsx` normalizes the dashboard anchor with the new `getDashboardAnchorEndIso()` helper in `lib/dashboard/time-windows.ts`, flooring the raw API coverage timestamp to the latest completed UTC day boundary before building chart windows.
- Next step: refresh the browser and confirm the dashboard now issues `24h`, `6h`, and `1h` requests ending at the UTC day boundary rather than the prior `07:00Z` anchor, and that the charts load instead of stalling into errors.
- Blockers/risks: the local dev route timing remains somewhat awkward to test by command line because the Next dev server can hang independently of the backend, so the most reliable validation for this change is the browser plus `logs/api-timing.log`.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: provide a repo-local written summary of the performance enhancements completed so far.
- What changed: added [docs/performance-enhancements.md](/workspaces/orcasound/ambient-sound-analysis-api/docs/performance-enhancements.md), summarizing API-side, UI-side, and dev-environment performance work completed to date, including caching, auto-bucketing, daily-summary aggregation, client-side chart loading, same-origin proxying, default window tuning, and devcontainer/runtime improvements.
- Next step: keep the performance summary updated as additional caching, chart-loading, or aggregation optimizations are made.
- Blockers/risks: the new doc summarizes sibling UI work as well as API repo changes, so it should be maintained alongside both codepaths when behavior changes.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: restore visible PSD daily summary data in the UI after switching the dashboard default window to `24h`.
- What changed: confirmed the PSD daily summary API itself was returning empty arrays for the `1`-day case because the UI helper was using the anchor day (`2021-11-01`) instead of the latest fully completed UTC day (`2021-10-31`). Updated sibling repo `ambient-sound-analysis-ui/lib/dashboard/time-windows.ts` so `getDailySummaryStartDate()` subtracts `numDays` days from the anchor timestamp rather than `numDays - 1`. Verified live via the Next proxy: `num_days=1` now returns populated series (`mean_length=217`) and `num_days=7` returns a full aggregated series (`mean_length=288`). Also verified with `npm run lint` and `npm run build` in the UI repo.
- Next step: refresh the browser and confirm the PSD daily summary now appears for the `24h`, `6h`, and `1h` windows, which all map to a `1`-day summary.
- Blockers/risks: day-summary endpoints now intentionally anchor to the most recent completed UTC day before the latest data timestamp; if the product owner later wants “current partial day” behavior, that would need a different API or helper contract.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: restore browser-side chart loading after moving the dashboard fetches client-side, without depending on a separately forwarded browser API port.
- What changed: in sibling repo `ambient-sound-analysis-ui`, added a catch-all Next route handler at `app/api/[...path]/route.ts` that proxies GET requests to the FastAPI backend using the server-side `API_BASE_URL` default `http://127.0.0.1:8000`. Updated the browser client fetch base in `lib/api/client.ts` from `http://localhost:8001` to same-origin `/api`, while still allowing `NEXT_PUBLIC_API_BASE_URL` override. Verified with `npm run lint`, `npm run build`, and a live `curl http://127.0.0.1:3000/api/health` returning `200`.
- Next step: refresh the browser page and confirm the charts now load through the Next proxy instead of failing with `ERR_CONNECTION_REFUSED`.
- Blockers/risks: the browser no longer needs direct access to the FastAPI host port, but the Next dev server itself still needs to be running for the proxy route to exist.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: remove as much dashboard cold-load penalty as possible and improve the initial PSD heatmap time resolution.
- What changed: in sibling repo `ambient-sound-analysis-ui`, changed the page so it server-loads only hydrophone options/anchor coverage and no longer awaits chart data during server render. Added a client-side query hook for the fixed 30-day broadband daily summary, made all chart queries hydration-gated so they do not run from the server render path, and kept loading placeholders visible until the browser begins fetching. Also changed the dashboard default window from `7d` to `24h` and replaced the PSD heatmap’s `interval=auto` request with an explicit per-window mapping: `1h -> 10s`, `6h/24h -> 1m`, `7d -> 15m`, `30d -> 1h`. Verified with `npm run build` and `npm run lint` in the UI repo. During a direct route hit after this change, the API timing log stayed quiet, confirming the page request itself no longer triggers backend chart fetches from the server side.
- Next step: check the live browser experience after hydration to make sure the chart loading order feels acceptable and that the finer default PSD resolution is actually sufficient.
- Blockers/risks: the dev `localhost:3000` route measurement remained slow/hung even after the API fetches were removed from the server render path, so there may still be an unrelated Next.js dev-server issue. The important confirmed point is that the backend is no longer the blocker for the initial HTML response.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: diagnose why the local dashboard still takes about 1.2 minutes to load on refresh and reduce repeat-refresh latency.
- What changed: measured the live request path using `logs/api-timing.log` and direct `curl` timings. The slow refresh was caused by server-rendered API calls, especially uncached `/aggregations/daily-summary` and `/aggregations/daily-broadband-summary`, with occasional cold `/aggregations/psd` runs after backend reloads. Added `lru_cache` wrappers to both daily summary service functions in `app/services/get_aggregations.py`, matching the existing cache behavior on the other aggregation endpoints. Verified with `python -m unittest discover -s tests -v` and `python -m compileall app tests`. Live timings confirmed the change: `daily-summary` dropped from about `24.67s` to `0.016s` on the second identical request, `daily-broadband-summary` dropped from about `11.67s` to `0.012s`, and a fully warm dashboard request dropped to about `0.265s`.
- Next step: if the user wants to eliminate the remaining cold-start penalty after backend reloads, move the PSD heatmap off the critical server-render path or add a persistent cache outside process memory.
- Blockers/risks: these caches are in-process only, so any FastAPI reload/restart clears them. The first request after a code change or server restart can still be slow, especially for `/aggregations/psd`.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: make the sibling UI’s PSD daily summary follow the dashboard time-window filter instead of staying fixed at a separate day count.
- What changed: in sibling repo `ambient-sound-analysis-ui`, replaced the fixed server-only PSD daily summary fetch with a time-window-aware server/client fetch path and a dedicated React Query hook. The mapping is now `30d -> 30 days`, `7d -> 7 days`, and `24h`/`6h`/`1h -> 1 day`. The initial server-rendered summary now uses `DEFAULT_TIME_WINDOW`, and subsequent filter changes refetch the daily summary in the browser just like the other charts. Verified with `npm run lint` and `npm run build` in the UI repo.
- Next step: exercise the live dashboard and confirm the PSD daily summary transitions feel coherent when switching between sub-day and multi-day windows.
- Blockers/risks: sub-day dashboard windows now intentionally reuse a 1-day daily summary because the endpoint contract is day-based rather than hour-based.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: improve the PSD daily summary chart styling in the sibling Next.js dashboard so min/max read as a range band instead of three competing lines.
- What changed: updated sibling repo `ambient-sound-analysis-ui/components/charts/psd-daily-summary-chart.tsx` so the chart now renders a light shaded min-to-max envelope with the mean plotted as the only foreground line. Verified with `npm run lint` and `npm run build` in the UI repo.
- Next step: review the chart against live data and decide whether the shaded band opacity or mean line weight should be tuned further for readability.
- Blockers/risks: none on the API side; this was a presentation-only UI change.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: reduce `GET /aggregations/daily-summary` payload and load time by aggregating its second-of-day output with the same auto-bucketing rules used by the other aggregation endpoints.
- What changed: added an optional `interval` query param to `GET /aggregations/daily-summary`, defaulting to `auto`. The service now resolves that interval against a fixed 24-hour second-of-day window using the same bucket rules as the other aggregation endpoints (`10s`, `1m`, `5m`, `15m`, `1h`, `1d`, or `auto` targeting about 1000 points). For the daily-summary endpoint that means `auto` now resolves to `5m` instead of returning 86,400 per-second points. The response model now includes the resolved `interval`, the summary series are bucketed before serialization, explicit overly-fine intervals are rejected if they exceed the standard aggregation point cap, and new unit tests cover both the auto-selection and over-limit rejection cases. Updated `README.md` accordingly. Verified with `python -m unittest discover -s tests -v` and `python -m compileall app tests`.
- Next step: run the live UI against the backend and confirm the page load drops materially now that the daily summary returns 5-minute buckets by default.
- Blockers/risks: the current implementation aggregates the `count` series by mean within each bucket, which is consistent with a bucketed summary but may need revisiting if the UI or downstream consumers expect a different count semantic.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: add the existing PSD-derived daily summary endpoint to the sibling Next.js dashboard without changing the API contract.
- What changed: in sibling repo `ambient-sound-analysis-ui`, added `DailySummaryResponse` types, added a server-side fetch helper for `GET /aggregations/daily-summary`, and rendered a new Plotly line chart showing mean/min/max by second-of-day on the home dashboard. The UI keeps this summary fixed to 30 days, independent of the selected dashboard window, and automatically falls back to 7 days only if the 30-day request fails. Verified with `npm run lint` and `npm run build` in the UI repo.
- Next step: run the dashboard against the live backend and confirm the 30-day PSD daily summary is performant enough in practice; if not, either keep the current 7-day fallback behavior or lower the fixed default explicitly.
- Blockers/risks: the chart renders 86,400 time-of-day points per series, so frontend rendering cost may still be noticeable even if the API responds successfully. The fallback currently treats any non-backend-unavailable daily-summary fetch failure as a reason to try 7 days.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: stop the sibling Next.js dashboard from throwing a server-render `fetch failed` 500 when the FastAPI backend is not listening on `127.0.0.1:8000`.
- What changed: in sibling repo `ambient-sound-analysis-ui`, wrapped server-side fetch failures in a dedicated `ServerApiUnavailableError` (`lib/api/server.ts`) and updated `app/page.tsx` to catch that condition and render an explicit API-offline setup state instead of crashing the whole page. Verified with `npm run lint` and `npm run build` in the UI repo. Confirmed separately that the API port was genuinely down from this container (`curl http://127.0.0.1:8000/health` failed with connection refused), so this was not just a misleading frontend error.
- Next step: start the FastAPI app on `0.0.0.0:8000` or set the UI server env `API_BASE_URL` to the correct backend address, then recheck the full dashboard data flow with the live backend.
- Blockers/risks: this change improves failure handling only; it does not start or proxy the backend. Browser-side refetches still depend on `NEXT_PUBLIC_API_BASE_URL` being correct for the forwarded host port.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: fix the timezone mismatch exposed by the new UI’s UTC `Z` timestamps when calling aggregation endpoints.
- What changed: normalized incoming request datetimes to naive UTC inside `app/services/get_timeseries.py` before range validation, coverage checks, cacheable timeseries fetches, and `NoiseAccessor` reads. This resolves the `TypeError: can't compare offset-naive and offset-aware datetimes` that occurred on `/aggregations/broadband` when the UI sent ISO timestamps with `Z`.
- Next step: continue exercising the UI against live endpoints and debug the separate PSD-path failure now showing up as an empty reply; that is distinct from the timezone-comparison bug.
- Blockers/risks: response payload timestamps are still mixed in style because request echo fields may include `+00:00` while aggregated point timestamps remain naive ISO strings from pandas indexes. That is not causing the current crash, but it may be worth standardizing later for UI consistency.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: stand up a simple first-pass `ambient-sound-analysis-ui` dashboard backed by the FastAPI aggregation endpoints, using direct browser calls plus Plotly charts.
- What changed: added permissive CORS middleware in `app/main.py` so the FastAPI app accepts cross-origin browser requests from the UI. In the sibling `ambient-sound-analysis-ui` app, replaced the starter page with an App Router dashboard that server-loads Orcasound Lab options and initial chart payloads, then uses React Query to refetch PSD heatmap and broadband aggregation data when the time-window filter changes. Added Plotly chart wrappers for the PSD heatmap, broadband timeseries, and fixed 30-day broadband daily summary. The UI currently assumes server-side API access at `http://127.0.0.1:8000` and browser-side API access at `http://localhost:8001`, with env overrides available via `API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL`.
- Next step: run the UI in dev mode against the live API, verify the browser can reach the expected forwarded FastAPI port, and then iterate on dashboard polish plus the deferred PSD daily-summary chart.
- Blockers/risks: the client-side API base URL is environment-sensitive because VS Code can assign different forwarded host ports. If the FastAPI forward is not `localhost:8001`, the UI needs `NEXT_PUBLIC_API_BASE_URL` set accordingly. Plotly is client-only and heavier than simpler chart libraries, but it matches the required heatmap use case and the data-science team workflow.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: determine why `ambient-sound-analysis-ui` appears to hang at `localhost:3000`/`3001` when run inside the API repo devcontainer.
- What changed: verified from inside the container that a live `next-server` process is already running for `ambient-sound-analysis-ui` and is serving `200 OK` on `127.0.0.1:3000`. Confirmed `3001` is not serving traffic; that port only appears when a second `npm run dev` instance starts, notices `3000` is busy, and then fails because the existing server already holds `.next/dev/lock`. This narrows the problem to host-to-container port forwarding or a stale duplicate dev process, not a Next.js app startup failure.
- Next step: stop any extra `npm run dev` terminals, keep a single UI dev server running, and either rebuild/reopen the devcontainer so the `forwardPorts` config is applied or manually forward container port `3000` from the VS Code Ports panel before opening the browser.
- Blockers/risks: if the devcontainer was opened before the current `forwardPorts` settings were added, `localhost:3000` on the host will continue to fail until the container is rebuilt/reopened or the port is manually forwarded. A stale background Next.js process can also mislead later runs by occupying `3000` and forcing failed fallback attempts on `3001`.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: improve the API repo devcontainer so ChatGPT/Codex extension state is more likely to survive a rebuild.
- What changed: updated `.devcontainer/devcontainer.json` to keep `/root/.vscode-server` and `/root/.config/Code` on named Docker volumes (`ambient-sound-analysis-api-vscode-server` and `ambient-sound-analysis-api-vscode`). This preserves remote VS Code server data, extension state, and secret/global storage across devcontainer rebuilds instead of recreating them from scratch each time.
- Next step: rebuild the devcontainer and verify the `openai.chatgpt` extension still appears signed in afterward. If it does not, the remaining limitation is on the extension or VS Code auth model rather than repo config.
- Blockers/risks: this improves persistence but still cannot guarantee exact chat-thread recovery; that depends on what the extension syncs remotely versus what it stores locally. Existing Docker volumes with these names may carry forward stale extension state until removed.
- Branch and latest commit: `main` / `87e7e09`
- Current objective: get the new `ambient-sound-analysis-ui` Next.js app reachable from the host browser when running inside the API repo devcontainer.
- What changed: verified the Next.js dev server starts successfully inside the container and serves `200 OK`, updated `.devcontainer/devcontainer.json` to explicitly forward ports `3000` and `3001` with labels, and updated `ambient-sound-analysis-ui/package.json` so `npm run dev` runs `next dev --webpack --hostname 0.0.0.0`. The `--webpack` switch avoids a Turbopack internal panic observed in the container during page compilation.
- Next step: rebuild or reopen the devcontainer so the new forwarded-port settings apply, then rerun `npm run dev` in `ambient-sound-analysis-ui` and open whichever forwarded port VS Code exposes, usually `3000` or `3001`.
- Blockers/risks: if port `3000` is already occupied inside the container, Next.js will still move to `3001`; that is expected, and the forwarded-port config now covers both ports.
- Branch and latest commit: `main` / `bb60eaa`
- Current objective: keep the API repo’s devcontainer usable for both the FastAPI backend and the new Next.js UI repo in the same VS Code workspace.
- What changed: `.devcontainer/Dockerfile` now copies Node.js 20 from the official `node:20-bookworm-slim` image into the Python 3.9 devcontainer image, so `node`, `npm`, and `npx` are available after rebuild without changing the production Cloud Run `Dockerfile`.
- Next step: rebuild the devcontainer, verify `node -v`, `npm -v`, and `npx -v`, then scaffold `ambient-sound-analysis-ui` with `npx create-next-app@latest .`.
- Blockers/risks: this only affects the development container. A rebuild is required before Node tooling is available, and the new UI repo still needs its own git init/remote setup.
- Branch and latest commit: `main` / `bb60eaa`
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
