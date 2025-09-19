import { decode } from 'wav-decoder';
import { fft, util } from 'fft-js';

/**
 * Metrics computed from an audio buffer.
 * @property rms Root mean square loudness.
 * @property psd Power spectral density windows.
 * @property bandPowers Bandpower bins (e.g., 63Hz, 125Hz).
 * @property snr_db Signal-to-noise ratio in decibels.
 * @property crestFactor Crest factor of the signal.
 * @property transienceRate Rate of transient events per minute.
 */
export interface Metrics {
  rms: number;
  psd: number[][];
  bandPowers: Record<string, number>;
  snr_db: number;
  crestFactor: number;
  transienceRate: number;
}

/**
 * Compute audio metrics from a WAV buffer.
 * @param wavBuffer Buffer containing WAV audio data.
 * @returns Promise resolving to computed Metrics.
 */
export async function computeMetrics(wavBuffer: Buffer): Promise<Metrics> {
  // 1. Decode WAV → PCM samples
  const audio = await decode(wavBuffer);
  const samples = audio.channelData[0]; // mono

  // 2. RMS Loudness
  const rms = Math.sqrt(samples.reduce((sum,v) => sum + v*v, 0) / samples.length);

  // 3. PSD per window
  const fftSize = 1024;
  const psd: number[][] = [];
  for (let i = 0; i + fftSize <= samples.length; i += fftSize) {
    const slice = samples.slice(i, i + fftSize);
    const phasors = fft(slice);
    const mags = util.fftMag(phasors);
    psd.push(mags);
  }

  // 4. Bandpower bins (e.g. 63 Hz, 125 Hz) – placeholder logic
  const bandPowers: Record<string, number> = {
    '63Hz': averageBin(psd, 1, 2),   // TODO refine bin indices
    '125Hz': averageBin(psd, 2, 4)
  };

  // 5. SNR (dB) – placeholder: signal=peak bandpower, noise=rms
  const signal = Math.max(...Object.values(bandPowers));
  const snr_db = 20 * Math.log10(signal / (rms + 1e-12));

  // 6. Crest factor & transience
  const peak = Math.max(...samples.map(Math.abs));
  const crestFactor = peak / (rms + 1e-12);
  const transientWindows = psd.filter(win => util.fftMag(fft(win)).some(m => m > crestFactor * 0.8));
  const transienceRate = transientWindows.length / (samples.length / fftSize) * 60; // per minute

  return { rms, psd, bandPowers, snr_db, crestFactor, transienceRate };
}

/**
 * Compute the average value of a frequency bin range across all PSD windows.
 * @param psd Array of PSD windows.
 * @param startBin Start index of bin range (inclusive).
 * @param endBin End index of bin range (exclusive).
 * @returns Average value in the specified bin range.
 */
function averageBin(psd: number[][], startBin: number, endBin: number): number {
  const sums = psd.flatMap(win => win.slice(startBin, endBin));
  return sums.reduce((a,b) => a + b, 0) / (sums.length || 1);
}
