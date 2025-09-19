/**
 * @fileoverview
 * Express REST API for batch processing HLS streams into WAV, FLAC, and PSD data for acoustic data visualization and AI training.
 * Exposes endpoints for generating audio/text pairs and retrieving batch results.
 *
 * Endpoints:
 *   POST /clip   - Generate a single clip and return file paths and metadata.
 *   POST /batch  - Generate multiple clips from an array of jobs.
 *   GET  /pairs  - Retrieve pairs.json for a given feed/date.
 *
 * Usage:
 *   npx ts-node src/api.ts
 *
 * Dependencies:
 *   express, fs, path, ./worker
 */

import express from 'express';
import { processJob, ClipJob } from './worker';
import fs from 'fs';
import path from 'path';

const app = express();
app.use(express.json());

// POST /clip - generate a single clip and return file paths and metadata
app.post('/clip', async (req, res) => {
  try {
    const job: ClipJob = req.body;
    const result = await processJob(job);
    res.json(result);
  } catch (err: any) {
    res.status(400).json({ error: err.message });
  }
});

// POST /batch - generate multiple clips from an array of jobs
app.post('/batch', async (req, res) => {
  const jobs: ClipJob[] = req.body.jobs;
  if (!Array.isArray(jobs)) {
    return res.status(400).json({ error: 'jobs must be an array of ClipJob objects' });
  }
  const results: any[] = [];
  for (const job of jobs) {
    try {
      const result = await processJob(job);
      results.push({ ...job, ...result });
    } catch (err: any) {
      results.push({ ...job, error: err.message });
    }
  }
  res.json({ results });
});

// GET /pairs - list all pairs.json files for a given feedSlug/date
app.get('/pairs', (req, res) => {
  const { feedSlug, date } = req.query;
  if (!feedSlug || !date) {
    return res.status(400).json({ error: 'feedSlug and date (YYYY-MM-DD) are required' });
  }
  const [yyyy, mm, dd] = (date as string).split('-');
  const dir = path.join(process.cwd(), 'output', 'clips', feedSlug as string, yyyy, mm, dd);
  const pairsPath = path.join(dir, 'pairs.json');
  if (!fs.existsSync(pairsPath)) {
    return res.status(404).json({ error: 'pairs.json not found for this feed/date' });
  }
  const data = fs.readFileSync(pairsPath, 'utf8');
  res.type('json').send(data);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`REST API listening on port ${PORT}`);
});
