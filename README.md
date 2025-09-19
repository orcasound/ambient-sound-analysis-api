# ambient-sound-analysis-api
REST API for batch processing HLS streams into WAV and Power Spectral Density (PSD) data for acoustic data visualization and AI training, based on the ambient-sound-analysis repo. Built during the 2025 Microsoft Hackathon.

Project team:
Darron
Imani
Adrian
Scott
Paul

---

## Prerequisites

```
npm install \
  @aws-sdk/client-s3 \
  axios \
  hls-parser \
  ffmpeg-static \
  wav-decoder \
  fft-js \
  csv-parse \
  yargs \
  express \
  @types/express \
  @types/node --save-dev
```

---

## Design

```mermaid
flowchart TD
    Start([Start])
    CLI[CLI (cli.ts)]
    API[REST API (api.ts)]
    ParseArgs[Parse CLI Args / Parse API Request]
    BatchCheck{Batch Mode?}
    ReadCSV[Read CSV Manifest]
    ForEachJob[For Each Job]
    SingleJob[Single Job]
    ProcessJob[processJob (worker.ts)]
    Download[Download HLS Segments]
    FFMPEG[Run ffmpeg (WAV/FLAC)]
    PSD[Compute PSD (analytics.ts)]
    Meta[Write .meta.json]
    Output[Write Output Files]
    Summary[Write pairs.json (batch)]
    End([End])

    Start --> CLI
    Start --> API
    CLI --> ParseArgs
    API --> ParseArgs
    ParseArgs --> BatchCheck
    BatchCheck -- Yes --> ReadCSV --> ForEachJob
    ForEachJob --> ProcessJob
    BatchCheck -- No --> SingleJob --> ProcessJob
    ProcessJob --> Download --> FFMPEG
    FFMPEG --> PSD
    PSD --> Meta
    Meta --> Output
    Output --> Summary
    Summary --> End
    Output --> End 
```

---

## How to Use

### Single Clip Extraction

You can extract and save a single audio clip using the CLI:

```sh
npx ts-node src/cli.ts \
  --feedSlug orcasound_lab \
  --start 2025-09-17T12:00:00Z \
  --end 2025-09-17T12:05:00Z \
  --formats wav flac psd \
  --out local
```

- To use S3 output (Disabled):

```sh
npm run clip -- \
  --feedSlug orcasound_lab \
  --start 2025-09-12T10:00:00Z \
  --end   2025-09-12T10:05:00Z \
  --formats wav flac psd \
  --out   s3   # or local
  # --s3Bucket your-bucket-name \
  # --s3Prefix clips/
```

- `feedSlug`: The audio feed identifier (e.g., `orcasound_lab`)
- `start`/`end`: ISO8601 timestamps for the clip window
- `formats`: Output formats (`wav`, `flac`, `psd`)
- `out`: Output destination, either `local` (default) or `s3` (S3 logic is a placeholder)
- `s3Bucket`: Your AWS S3 bucket name (required if using `--out s3`)
- `s3Prefix`: (Optional) S3 key prefix for uploads

### Batch Processing from CSV

Prepare a CSV manifest with columns: `feedSlug,start,end`.
Example:

```csv
feedSlug,start,end
orcasound_lab,2025-09-17T12:00:00Z,2025-09-17T12:05:00Z
orcasound_lab,2025-09-17T13:00:00Z,2025-09-17T13:05:00Z
```

Run batch processing:

```sh
npx ts-node src/cli.ts \
  --manifest jobs.csv \
  --formats wav flac psd
```

A summary file will be written to the `clips/<feedSlug>/<YYYY>/<MM>/<DD>/` directory, named as `pairs.json` (e.g., `clips/orcasound_lab/2025/09/18/pairs.json`).

---

## Output

- Audio files and analytics are written to the local `clips/<feedSlug>/<YYYY>/<MM>/<DD>/` directory.
- Each clip includes a `.wav` (and/or `.flac`), `.psd.json` (if requested), and `.meta.json` sidecar file with metadata.
- Output file paths are printed to the console and/or written to the summary JSON in the `clips/<feedSlug>/<YYYY>/<MM>/<DD>/` directory in batch mode. If a job fails, the error is included in the summary JSON and does not block other jobs.

---

## Components

### cli.ts
- Provides a command-line interface for both single and batch audio extraction jobs.
- Accepts arguments for feed, time window, formats, output directory, manifest CSV, and optional detection comment.
- In batch mode, reads a CSV manifest and processes each row as a job, writing a summary JSON to the `output/` directory. If a `comment` column is present in the CSV, it is included in the summary.
- In single mode, processes one job and prints the output file paths and comment to the console.
- Internally calls `processJob` from `worker.ts` for all processing.

### worker.ts
- Exports the main `processJob` function, which orchestrates the end-to-end workflow:
  1. Validates the requested time window.
  2. Downloads and parses the HLS playlist, filtering segments by time.
  3. Downloads and concatenates audio segments using ffmpeg.
  4. Converts audio to the requested formats (WAV, FLAC).
  5. Computes analytics (PSD) if requested, using `analytics.ts`.
  6. Writes all outputs to a local shared folder (`output/clips/`).
  7. Writes a `.meta.json` file for each clip with metadata.
  8. Returns a summary object with output file paths and a deterministic hash.
- Used by the CLI and can be imported in other scripts for programmatic batch processing.

### analytics.ts
- Provides the `computeMetrics` function, which takes a WAV audio buffer and computes audio analytics such as RMS, power spectral density (PSD), band powers, SNR, crest factor, and transience rate.
- Used internally by `worker.ts` when the `psd` format is requested.
- You can import and use `computeMetrics` in your own scripts for standalone audio analytics on WAV buffers.

---

## Running in Docker

A `Dockerfile` is provided for reproducible, containerized runs. No global ffmpeg is required.

### Build the Docker image

```sh
docker build -t ambient-sound-api .
```

### Run a batch job (mount output to host)

```sh
docker run -v $(pwd)/output:/app/output ambient-sound-api --manifest jobs.csv --formats wav psd
```

### Run a single job

```sh
docker run -v $(pwd)/output:/app/output ambient-sound-api --feedSlug orcasound_lab --start 2025-09-17T12:00:00Z --end 2025-09-17T12:05:00Z --formats wav
```

- The `-v $(pwd)/output:/app/output` mounts your local output folder to the container so results are accessible on your host.
- All output and temp files are written to local directories inside the container by default.
- No global ffmpeg or special system setup is required.

---

## Notes

- Ensure your AWS credentials are configured for S3 access.
- Temporary files are stored in `tmp/` and can be cleaned up as needed.
- The CLI and codebase use ES module imports and require Node.js 16+ and TypeScript 4.5+.
- If you see errors about missing Node.js types (e.g., `process`, `Buffer`), ensure you have installed `@types/node` as shown above.
- For CSV parsing, the code uses `csv-parse/sync` with named import: `import { parse } from 'csv-parse/sync';`.
- The batch mode expects the CSV columns to be named exactly: `feedSlug`, `start`, `end`.

---

## REST API Usage (Optional)

A REST API is provided for programmatic access to clip and batch generation.

### Start the API server

```sh
npx ts-node src/api.ts
```

### Endpoints

- `POST /clip` — Generate a single clip and return file paths and metadata.
  - Request body: JSON matching the ClipJob interface (see below).
  - Response: JSON with output file paths and hash.

- `POST /batch` — Generate multiple clips from an array of jobs.
  - Request body: `{ "jobs": [ ClipJob, ... ] }`
  - Response: `{ "results": [ ... ] }` (each result includes job info, output, or error)

- `GET /pairs?feedSlug=...&date=YYYY-MM-DD` — Retrieve pairs.json for a given feed/date.
  - Returns the summary JSON for that day and feed.

### Example: Generate a single clip

```sh
curl -X POST http://localhost:3000/clip \
  -H 'Content-Type: application/json' \
  -d '{
    "feedSlug": "orcasound_lab",
    "start": "2025-09-17T12:00:00Z",
    "end": "2025-09-17T12:05:00Z",
    "formats": ["wav", "flac", "psd"],
    "out": "local"
  }'
```
**Example response:**
```json
{
  "urls": {
    "wav": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.wav",
    "flac": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.flac",
    "psd": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.psd.json",
    "meta": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.meta.json"
  },
  "hash": "xxxxxxxx"
}
```

### Example: Batch job

```sh
curl -X POST http://localhost:3000/batch \
  -H 'Content-Type: application/json' \
  -d '{ "jobs": [ { "feedSlug": "orcasound_lab", "start": "2025-09-17T12:00:00Z", "end": "2025-09-17T12:05:00Z", "formats": ["wav", "flac", "psd"] } ] }'
```
**Example response:**
```json
{
  "results": [
    {
      "feedSlug": "orcasound_lab",
      "start": "2025-09-17T12:00:00Z",
      "end": "2025-09-17T12:05:00Z",
      "formats": ["wav", "flac", "psd"],
      "urls": {
        "wav": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.wav",
        "flac": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.flac",
        "psd": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.psd.json",
        "meta": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.meta.json"
      },
      "hash": "xxxxxxxx"
    }
  ]
}
```

### Example: Retrieve pairs.json

```sh
curl "http://localhost:3000/pairs?feedSlug=orcasound_lab&date=2025-09-18"
```
**Example response:**
```json
[
  {
    "feedSlug": "orcasound_lab",
    "start": "2025-09-17T12:00:00Z",
    "end": "2025-09-17T12:05:00Z",
    "wav": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.wav",
    "flac": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.flac",
    "psd": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.psd.json",
    "meta": "output/clips/orcasound_lab/2025/09/18/orcasound_lab_20250918..._300s_xxxxxxxx.meta.json"
  }
]
```
