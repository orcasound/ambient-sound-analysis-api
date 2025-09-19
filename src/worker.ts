import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { spawn } from 'child_process';
import axios from 'axios';
import HLS from 'hls-parser';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { computeMetrics } from './analytics';
import ffmpegBin from 'ffmpeg-static'; // Use ESM import for ffmpeg-static

/**
 * Represents a job to extract and process an audio clip.
 * @property feedSlug - The identifier for the audio feed.
 * @property start - The ISO8601 start time for the clip.
 * @property end - The ISO8601 end time for the clip.
 * @property formats - The output formats to generate.
 * @property s3Bucket - The S3 bucket to upload results to.
 * @property s3Prefix - The S3 key prefix for uploads.
 * @property m3u8Url - The HLS playlist URL.
 */
export interface ClipJob {
  feedSlug: string;
  start: string;           // ISO8601
  end: string;             // ISO8601
  formats: Array<'wav' | 'flac' | 'psd'>;
  s3Bucket: string;
  s3Prefix: string;        // e.g. 'clips/'
  m3u8Url: string;
}

/**
 * The result of a processed audio clip job.
 * @property urls - Map of format to S3 URL.
 * @property hash - Deterministic hash for idempotency.
 */
export interface ClipResult {
  urls: Record<string, string>;  // { wav: s3Url, flac: s3Url, psd: s3Url }
  hash: string;
}

// S3 client for uploading results.
const s3 = new S3Client({});

/**
 * Processes a ClipJob: downloads segments, extracts audio, computes analytics, uploads to S3.
 *
 * @param job The job configuration.
 * @returns The result containing S3 URLs and hash.
 * @throws If the time window is invalid or no segments are found.
 */
export async function processJob(job: ClipJob): Promise<ClipResult> {
  // 1. Validate time window
  const startTs = Date.parse(job.start);
  const endTs = Date.parse(job.end);
  if (isNaN(startTs) || isNaN(endTs) || endTs <= startTs) {
    throw new Error(`Invalid time window: ${job.start} → ${job.end}`);
  }

  // 2. Fetch playlist & filter by programDateTime
  const playlistText = (await axios.get(job.m3u8Url)).data as string;
  const playlist = HLS.parse(playlistText);

  if (playlist.isMasterPlaylist) {
    throw new Error('Provided playlist is a MasterPlaylist, expected a MediaPlaylist');
  }

  const mediaPlaylist = playlist as HLS.types.MediaPlaylist;
  const segments = mediaPlaylist.segments.filter(seg => {
    if (!seg.programDateTime) return false;
    const ts = seg.programDateTime instanceof Date
      ? seg.programDateTime.getTime()
      : Date.parse(seg.programDateTime);
    return ts >= startTs && ts < endTs;
  });
  if (segments.length === 0) {
    throw new Error(`No segments in range [${job.start} → ${job.end}]`);
  }

  // 3. Deterministic hash for idempotency
  const hash = crypto
    .createHash('sha256')
    .update(`${job.feedSlug}|${job.start}|${job.end}|${job.formats.join(',')}`)
    .digest('hex')
    .slice(0, 8);

  // 4. Build local temp directory for intermediate files
  const dt = new Date(startTs).toISOString().replace(/[:.]/g, '');
  const durSec = Math.round((endTs - startTs) / 1000);
  const base = `${job.feedSlug}_${dt}_${durSec}s_${hash}`;
  const tmpDir = path.join(process.cwd(), 'tmp', base);
  fs.mkdirSync(tmpDir, { recursive: true });

  // 5. Write ffmpeg concat list for segment download
  const listTxt = segments
    .map(seg => {
      const uri = seg.uri.startsWith('http')
        ? seg.uri
        : new URL(seg.uri, job.m3u8Url).toString();
      return `file '${uri.replace(/'/g, "\\'")}'`;
    })
    .join('\n');
  const listFile = path.join(tmpDir, 'segments.txt');
  fs.writeFileSync(listFile, listTxt);

  // 6. Decode via ffmpeg to PCM containerized as WAV/FLAC
  // ffmpegBin is now imported as an ES module above
  const outputs: Record<string, string> = {};

  for (const fmt of job.formats) {
    const outFile = path.join(tmpDir, `${base}.${fmt}`);
    const args = [
      '-protocol_whitelist', 'file,http,https,tcp,tls',
      '-f', 'concat', '-safe', '0', '-i', listFile,
      '-ac', '1', '-ar', '48000'
    ];

    if (fmt === 'wav') {
      args.push('-c:a', 'pcm_s16le', outFile);
    } else if (fmt === 'flac') {
      args.push('-c:a', 'flac', outFile);
    }

    // Run ffmpeg as a child process and await completion.
    await new Promise<void>((resolve, reject) => {
      const proc = spawn(ffmpegBin as string, args, { stdio: 'inherit' });
      proc.on('error', reject);
      proc.on('exit', code =>
        code === 0
          ? resolve()
          : reject(new Error(`ffmpeg ${fmt} exited ${code}`))
      );
    });
    outputs[fmt] = outFile;
  }

  // 7. Compute analytics if requested (psd)
  let metrics: Awaited<ReturnType<typeof computeMetrics>> | undefined;
  if (job.formats.includes('psd')) {
    // Read the WAV file and compute metrics
    const wavBuf = fs.readFileSync(outputs['wav']);
    metrics = await computeMetrics(wavBuf);
    // Write local metrics JSON
    const metricsPath = path.join(tmpDir, `${base}.psd.json`);
    fs.writeFileSync(metricsPath, JSON.stringify(metrics, null, 2));
    outputs['psd'] = metricsPath;
  }

  // 8. Upload to S3 (or swap out with local copy logic)
  const urls: Record<string, string> = {};
  for (const [fmt, localPath] of Object.entries(outputs)) {
    const key = `${job.s3Prefix}${job.feedSlug}/${dt.slice(0, 4)}/${dt.slice(4, 6)}/${dt.slice(6, 8)}/${base}.${fmt}`;
    const body = fs.readFileSync(localPath);

    // Upload file to S3
    await s3.send(new PutObjectCommand({
      Bucket: job.s3Bucket,
      Key: key,
      Body: body,
      ContentType: fmt === 'psd' ? 'application/json' : `audio/${fmt}`
    }));
    urls[fmt] = `s3://${job.s3Bucket}/${key}`;
  }

  // 9. Clean up temp files if desired (uncomment to enable)
  // fs.rmSync(tmpDir, { recursive: true, force: true });

  return { urls, hash };
}