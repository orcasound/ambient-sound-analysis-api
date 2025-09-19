import fs from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';
import yargs from 'yargs';
import { processJob, ClipJob } from './worker';

/**
 * Command-line interface for processing audio clips.
 * Supports single job or batch mode via CSV manifest.
 *
 * CLI Options:
 *   --feedSlug   Audio feed identifier (string)
 *   --start      Clip start time (ISO8601 string)
 *   --end        Clip end time (ISO8601 string)
 *   --manifest   CSV manifest for batch jobs (string)
 *   --formats    Output formats (array: wav, flac, psd)
 *   --s3Bucket   S3 bucket for uploads (string, required)
 *   --s3Prefix   S3 key prefix (string, default: 'clips/')
 */
async function main() {
  const argv = yargs
    .option('feedSlug',  { type: 'string', describe: 'Audio feed identifier' })
    .option('start',     { type: 'string', describe: 'Clip start time (ISO8601)' })
    .option('end',       { type: 'string', describe: 'Clip end time (ISO8601)' })
    .option('manifest',  { type: 'string', describe: 'CSV manifest for batch jobs' })
    .option('formats',   { type: 'array', choices: ['wav','flac','psd'], default: ['wav'], describe: 'Output formats' })
    .option('s3Bucket',  { type: 'string', demandOption: true, describe: 'S3 bucket for uploads' })
    .option('s3Prefix',  { type: 'string', default: 'clips/', describe: 'S3 key prefix' })
    .demandOption(argv => argv.manifest ? [] : ['feedSlug','start','end'])
    .help()
    .argv as any;

  const summary: any[] = [];

  if (argv.manifest) {
    /**
     * Batch mode: process jobs from CSV manifest file.
     * Each row should have feedSlug, start, end columns.
     * Results are written to output/MMDDYYYY_timestamp_pairs.json.
     */
    const rows = parse(fs.readFileSync(argv.manifest, 'utf8'), { columns: true }) as Array<{ feedSlug: string; start: string; end: string }>;
    for (const { feedSlug, start, end } of rows) {
      const job: ClipJob = {
        feedSlug, start, end,
        formats: argv.formats,
        s3Bucket: argv.s3Bucket,
        s3Prefix: argv.s3Prefix,
        m3u8Url: `https://live.orcasound.net/${feedSlug}/playlist.m3u8`
      };
      try {
        const res = await processJob(job);
        summary.push({ feedSlug, start, end, ...res.urls });
      } catch (err: any) {
        console.error(`❌ ${feedSlug} ${start}→${end}: ${err.message}`);
      }
    }
    // Create output directory if it doesn't exist
    const outputDir = path.join(process.cwd(), 'output');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    // Generate filename: MMDDYYYY_timestamp_pairs.json
    const now = new Date();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const yyyy = now.getFullYear();
    const timestamp = String(Math.floor(now.getTime() / 1000));
    const outFile = `${mm}${dd}${yyyy}_${timestamp}_pairs.json`;
    const outPath = path.join(outputDir, outFile);
    fs.writeFileSync(outPath, JSON.stringify(summary, null, 2));
    console.log(`✅ Batch complete, summary → ${outPath}`);
  } else {
    /**
     * Single job mode: process a single audio clip job from CLI arguments.
     */
    const job: ClipJob = {
      feedSlug: argv.feedSlug,
      start:    argv.start,
      end:      argv.end,
      formats:  argv.formats,
      s3Bucket: argv.s3Bucket,
      s3Prefix: argv.s3Prefix,
      m3u8Url:  `https://live.orcasound.net/${argv.feedSlug}/playlist.m3u8`
    };
    const { urls } = await processJob(job);
    console.log('✅ Uploaded files:', urls);
  }
}

/**
 * Entry point for CLI. Handles errors and exits with code 1 on failure.
 */
main().catch(err => {
  console.error(err);
  process.exit(1);
});
