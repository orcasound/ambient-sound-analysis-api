# ambient-sound-analysis-api
Thin FastAPI wrapper around `orcasound_noise` for querying archived Orcasound ambient sound products from S3.

```
ambient-sound-analysis-api/
  app/
    main.py
    api/
      aggregations.py
      health.py
      options.py
      timeseries.py
    services/
      get_aggregations.py
      get_options.py
      get_timeseries.py
    models/
      responses.py
  tests/
    test_get_options.py
    test_get_timeseries.py
  docs/
    agent-context.md
    upstream-notes.md
  requirements.txt
  README.md
  .env.example
```

## Endpoints

### `GET /health`

Basic liveness check.

Example:

```bash
curl "http://localhost:8000/health"
```

### `GET /options`

Returns archived availability for one hydrophone or all hydrophones.

Query params:

- `hydrophone` optional, for example `sandbox`

Example:

```bash
curl "http://localhost:8000/options?hydrophone=sandbox"
```

The response is organized by actual stored combinations:

- `broadband`: one record per `delta_t`
- `octave_bands`: one record per `delta_f` + `delta_t`
- `delta_hz`: one record per `delta_f` + `delta_t`

Note:

- the default all-hydrophones `/options` scan skips `sandbox`
- `sandbox` can still be requested explicitly with `?hydrophone=sandbox`
- this is intentional because `sandbox` uses a mixed archive prefix that is slower to scan and not currently trustworthy for default inventory reporting

### `GET /timeseries/broadband`

Returns broadband timeseries points for a hydrophone and time window.

Query params:

- `hydrophone` required
- `start` required, ISO 8601 datetime
- `end` required, ISO 8601 datetime
- `delta_t` optional, default `1`
- `validate` optional, default `true`

Example:

```bash
curl "http://localhost:8000/timeseries/broadband?hydrophone=sandbox&start=2026-01-27T00:00:00&end=2026-01-27T00:10:00&delta_t=1&validate=true"
```

### `GET /timeseries/psd`

Returns PSD timeseries data as `columns` plus row-aligned `values`.

Query params:

- `hydrophone` required
- `start` required, ISO 8601 datetime
- `end` required, ISO 8601 datetime
- `delta_t` required in practice, though it defaults to `1`
- `delta_f` required, for example `12oct` or `500hz`
- `validate` optional, default `true`

Example:

```bash
curl "http://localhost:8000/timeseries/psd?hydrophone=sandbox&start=2026-01-27T00:00:00&end=2026-01-27T00:10:00&delta_t=1&delta_f=12oct&validate=true"
```

### `GET /aggregations/daily-summary`

Returns a daily-pattern summary rather than a raw chronological timeseries.

Query params:

- `hydrophone` required
- `start_date` required, `YYYY-MM-DD`
- `num_days` required
- `band_low` optional, default `63`
- `band_high` optional, default `8000`
- `interval` optional, default `auto`; one of `10s`, `1m`, `5m`, `15m`, `1h`, `1d`, or `auto`
- `interval=auto` picks the finest allowed bucket that keeps the second-of-day summary at or below about 1000 points

Example:

```bash
curl "http://localhost:8000/aggregations/daily-summary?hydrophone=orcasound_lab&start_date=2020-01-01&num_days=2&band_low=63&band_high=8000&interval=auto"
```

Response notes:

- `summary_purpose` explains why this endpoint exists: it shows a typical daily pattern rather than a raw timeline
- `time_of_day` is a clock time within the day, not a full timestamp
- `mean`, `min`, `max`, and `count` are separate series, each with a `*_length` field near the top of the response
- `interval` reports the actual time-of-day aggregation bucket used in the response
- `mean`, `min`, and `max` summarize the selected days bucket-by-bucket across the day
- these values are averaged across all PSD bands between `band_low` and `band_high`, so this is not the same as a true broadband summary
- `count` is the mean contributing day-observation count within each returned time-of-day bucket
- non-finite upstream values are dropped so the JSON remains valid

### `GET /aggregations/daily-broadband-summary`

Returns one true broadband average per day across the requested date window.

Query params:

- `hydrophone` required
- `start_date` required, `YYYY-MM-DD`
- `num_days` required

Example:

```bash
curl "http://localhost:8000/aggregations/daily-broadband-summary?hydrophone=orcasound_lab&start_date=2020-01-01&num_days=2"
```

Response notes:

- this is a true broadband summary from the upstream broadband product
- each point represents one day, not one second-of-day
- this is the better choice when you want a small browser-friendly daily series

### `GET /aggregations/broadband`

Returns a chronologically aggregated broadband series for browser plotting.

Query params:

- `hydrophone` required
- `start` required, ISO 8601 datetime
- `end` required, ISO 8601 datetime
- `interval` required, one of `10s`, `1m`, `5m`, `15m`, `1h`, `1d`, or `auto`
- `interval=auto` picks the finest allowed bucket that keeps the estimated point count at or below about 1000
- `delta_t` optional, default `1`
- `validate` optional, default `true`

Example:

```bash
curl "http://localhost:8000/aggregations/broadband?hydrophone=sandbox&start=2026-01-27T00:00:00&end=2026-01-27T06:00:00&interval=auto&delta_t=1&validate=true"
```

Response notes:

- this starts from the true broadband timeseries, then groups it into the requested bucket
- use this for browser plotting instead of raw per-second broadband over long windows
- the endpoint rejects requests that would return more than 2000 aggregated points

### `GET /aggregations/psd`

Returns a compact time-frequency matrix for browser plotting.

Query params:

- `hydrophone` required
- `start` required, ISO 8601 datetime
- `end` required, ISO 8601 datetime
- `interval` required, one of `10s`, `1m`, `5m`, `15m`, `1h`, `1d`, or `auto`
- `interval=auto` picks the finest allowed bucket that keeps the estimated time-bucket count at or below about 1000
- `delta_f` required, for example `12oct` or `500hz`
- `delta_t` optional, default `1`
- `validate` optional, default `true`

Example:

```bash
curl "http://localhost:8000/aggregations/psd?hydrophone=sandbox&start=2026-01-27T00:00:00&end=2026-01-27T06:00:00&interval=auto&delta_t=1&delta_f=12oct&validate=true"
```

Response notes:

- `times` contains aggregated time buckets
- `frequencies` contains the archived PSD band labels
- `values` is a row-aligned matrix where each row matches one `times` entry
- this is the browser-friendly companion to raw `/timeseries/psd`
- the endpoint rejects requests that would return more than 2000 time buckets

## Notes

- `validate=true` performs a preflight check against the cached `/options` inventory and returns clearer `400` errors for unsupported combinations or out-of-coverage windows.
- `validate=false` skips that preflight and goes straight to `NoiseAccessor`, which can be faster for known-good requests.
- Repeated identical `/options` and timeseries requests are cached in-process. First-hit latency is still dominated by upstream S3/parquet reads.
- `/aggregations/daily-summary` is not broadband. It summarizes PSD data over a selected frequency range.

## Tests

Run the unit tests with:

```bash
python -m unittest discover -s tests -v
```
