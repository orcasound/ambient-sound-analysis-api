# ambient-sound-analysis-api
REST API for batch processing HLS streams into WAV and Power Spectral Density (PSD) data for acoustic data visualization and AI training, based on the ambient-sound-analysis repo. Built during the 2025 Microsoft Hackathon.

Project team:
Darron
Imani
Adrian
Scott
Paul

---

## Prerequisites / Dependencies
```
npm install \
  @aws-sdk/client-s3 \
  axios \
  hls-parser \
  fluent-ffmpeg \
  ffmpeg-static \
  wav-decoder \
  fft-js \
  csv-parse \
  yargs \
  @types/node --save-dev
```

---

## How to Use

### Single Clip Extraction

You can extract and upload a single audio clip to S3 using the CLI:

```sh
npx ts-node src/cli.ts \
  --feedSlug orcasound_lab \
  --start 2025-09-18T12:00:00Z \
  --end 2025-09-18T12:05:00Z \
  --formats wav psd \
  --s3Bucket your-bucket-name \
  --s3Prefix clips/
```

- `feedSlug`: The audio feed identifier (e.g., `orcasound_lab`)
- `start`/`end`: ISO8601 timestamps for the clip window
- `formats`: Output formats (`wav`, `flac`, `psd`)
- `s3Bucket`: Your AWS S3 bucket name
- `s3Prefix`: (Optional) S3 key prefix for uploads

### Batch Processing from CSV

Prepare a CSV manifest with columns: `feedSlug,start,end`.
Example:

```csv
feedSlug,start,end
orcasound_lab,2025-09-18T12:00:00Z,2025-09-18T12:05:00Z
orcasound_lab,2025-09-18T13:00:00Z,2025-09-18T13:05:00Z
```

Run batch processing:

```sh
npx ts-node src/cli.ts \
  --manifest jobs.csv \
  --formats wav psd \
  --s3Bucket your-bucket-name \
  --s3Prefix clips/
```

A summary file will be written to the `output/` directory, named as `MMDDYYYY_timestamp_pairs.json` (e.g., `output/09162025_1714060000_pairs.json`).

---

## Output

- Audio files and analytics are uploaded to your specified S3 bucket.
- Output S3 URLs are printed to the console and/or written to the summary JSON in the `output/` directory in batch mode.

---

## Components

### cli.ts
- Provides a command-line interface for both single and batch audio extraction jobs.
- Accepts arguments for feed, time window, formats, S3 bucket, and manifest CSV.
- In batch mode, reads a CSV manifest and processes each row as a job, writing a summary JSON to the `output/` directory.
- In single mode, processes one job and prints the S3 URLs to the console.
- Internally calls `processJob` from `worker.ts` for all processing.

### worker.ts
- Exports the main `processJob` function, which orchestrates the end-to-end workflow:
  1. Validates the requested time window.
  2. Downloads and parses the HLS playlist, filtering segments by time.
  3. Downloads and concatenates audio segments using ffmpeg.
  4. Converts audio to the requested formats (WAV, FLAC).
  5. Computes analytics (PSD) if requested, using `analytics.ts`.
  6. Uploads all outputs to S3.
  7. Returns a summary object with S3 URLs and a deterministic hash.
- Used by the CLI and can be imported in other scripts for programmatic batch processing.

### analytics.ts
- Provides the `computeMetrics` function, which takes a WAV audio buffer and computes audio analytics such as RMS, power spectral density (PSD), band powers, SNR, crest factor, and transience rate.
- Used internally by `worker.ts` when the `psd` format is requested.
- You can import and use `computeMetrics` in your own scripts for standalone audio analytics on WAV buffers.

---

## Notes

- Ensure your AWS credentials are configured for S3 access.
- Temporary files are stored in `tmp/` and can be cleaned up as needed.
- The CLI and codebase use ES module imports and require Node.js 16+ and TypeScript 4.5+.
- If you see errors about missing Node.js types (e.g., `process`, `Buffer`), ensure you have installed `@types/node` as shown above.
- For CSV parsing, the code uses `csv-parse/sync` with named import: `import { parse } from 'csv-parse/sync';`.
- The batch mode expects the CSV columns to be named exactly: `feedSlug`, `start`, `end`.
