# ambient-sound-analysis-api
Thin FastAPI wrapper around `orcasound_noise` for querying archived Orcasound ambient sound products from S3.

```
ambient-sound-analysis-api/
  app/
    main.py
    api/
      health.py
      options.py
      timeseries.py
    services/
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

## Notes

- `validate=true` performs a preflight check against the cached `/options` inventory and returns clearer `400` errors for unsupported combinations or out-of-coverage windows.
- `validate=false` skips that preflight and goes straight to `NoiseAccessor`, which can be faster for known-good requests.
- Repeated identical `/options` and timeseries requests are cached in-process. First-hit latency is still dominated by upstream S3/parquet reads.

## Tests

Run the unit tests with:

```bash
python -m unittest discover -s tests -v
```
