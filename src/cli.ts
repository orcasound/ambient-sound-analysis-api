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
 *   --out        Output destination: local or s3 (default: local)
 *   --s3Bucket   S3 bucket for uploads (string, required if --out s3)
 *   --s3Prefix   S3 key prefix (string, default: 'clips/')
 *   --feedId     Optional feedId (not the same as feedSlug)
 */
async function main() {
  const argv = yargs
    .option('feedSlug',  { type: 'string', describe: 'Audio feed identifier' })
    .option('feedId',    { type: 'string', describe: 'Optional feedId (not the same as feedSlug)' })
    .option('start',     { type: 'string', describe: 'Clip start time (ISO8601)' })
    .option('end',       { type: 'string', describe: 'Clip end time (ISO8601)' })
    .option('manifest',  { type: 'string', describe: 'CSV manifest for batch jobs' })
    .option('formats',   { type: 'array', choices: ['wav','flac','psd'], default: ['wav'], describe: 'Output formats' })
    .option('out',       { type: 'string', choices: ['local', 's3'], default: 'local', describe: 'Output destination: local or s3' })
    .option('s3Bucket',  { type: 'string', describe: 'S3 bucket for uploads' })
    .option('s3Prefix',  { type: 'string', default: 'clips/', describe: 'S3 key prefix' })
    .demandOption(argv => argv.manifest ? [] : ['feedSlug','start','end'])
    .help()
    .argv as any;

  const summary: any[] = [];

  if (argv.manifest) {
    /**
     * Batch mode: process jobs from CSV manifest file.
     * Each row should have feedSlug, start, end columns.
     * If a 'comment' column is present, it will be included in the summary.
     * Results are written to clips/<feedSlug>/<YYYY>/<MM>/<DD>/pairs.json.
     */
    const rows = parse(fs.readFileSync(argv.manifest, 'utf8'), { columns: true }) as Array<{ feedSlug: string; start: string; end: string; comment?: string; feedId?: string }>;
    for (const { feedSlug, start, end, comment, feedId } of rows) {
      const job: ClipJob = {
        feedId,
        feedSlug, start, end,
        formats: argv.formats,
        s3Bucket: argv.s3Bucket,
        s3Prefix: argv.s3Prefix,
        m3u8Url: `https://live.orcasound.net/${feedSlug}/playlist.m3u8`,
        out: argv.out
      };
      try {
        const res = await processJob(job);
        summary.push({ feedSlug, start, end, comment, ...res.urls });
      } catch (err: any) {
        console.error(`❌ ${feedSlug} ${start}→${end}: ${err.message}`);
        summary.push({ feedSlug, start, end, comment, error: err.message });
      }
    }
    // Write summary to correct output directory
    if (rows.length > 0) {
      const first = rows[0];
      const yyyy = new Date(first.start).getFullYear();
      const mm = String(new Date(first.start).getMonth() + 1).padStart(2, '0');
      const dd = String(new Date(first.start).getDate()).padStart(2, '0');
      const outDir = path.join(process.cwd(), 'output', 'clips', first.feedSlug, String(yyyy), mm, dd);
      if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
      const outPath = path.join(outDir, 'pairs.json');
      fs.writeFileSync(outPath, JSON.stringify(summary, null, 2));
      console.log(`✅ Batch complete, summary → ${outPath}`);
    }
  } else {
    /**
     * Single job mode: process a single audio clip job from CLI arguments.
     * Optionally accepts a --comment argument.
     */
    const job: ClipJob = {
      feedId: argv.feedId,
      feedSlug: argv.feedSlug,
      start:    argv.start,
      end:      argv.end,
      formats:  argv.formats,
      s3Bucket: argv.s3Bucket,
      s3Prefix: argv.s3Prefix,
      m3u8Url:  `https://live.orcasound.net/${argv.feedSlug}/playlist.m3u8`,
      out: argv.out
    };
    const { urls } = await processJob(job);
    const singleSummary = {
      feedSlug: argv.feedSlug,
      start: argv.start,
      end: argv.end,
      comment: argv.comment,
      ...urls
    };
    console.log('✅ Uploaded files:', singleSummary);
  }
}

/**
 * Entry point for CLI. Handles errors and exits with code 1 on failure.
 */
main().catch(err => {
  console.error(err);
  process.exit(1);
});
