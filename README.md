# ambient-sound-analysis-api
Serverless API for batch processing HLS streams into WAV and Power Spectral Density (PSD) data for acoustic data visualization, AIS pairing, and AI training, based on the ambient-sound-analysis repo. 

Proposed subpackages:
- api/ (FastAPI routes + OpenAPI)
- workers/ (Lambda or container jobs for HLS→WAV/PSD)
- lib/ (shared transforms, ffmpeg wrappers, PSD, bandpass utils)
- cli/ (batch jobs for backfills)
- infra/ (Infrastructure as Code for Lambda / Elastic Container Registry (ECR), e.g., Terraform)

### Overview

Skills needed: React/TypeScript, Node, audio analysis, data visualization

We want to build a production-ready noise analytics layer for the [live.orcasound.net](http://live.orcasound.net/) application so moderators and community scientists can easily contextualize and interpret the noises heard in audio feeds, identify candidates for different sound types, and track noise pollution for conservation purposes. We would also expose endpoints so that metrics can be consumed for other projects. 

The proposed way to implement this is to create a backend Node worker that performs 4 functions:
1. converts a sequence of HLS segments into a WAV file
2. batch converts a series of HLS sequences into WAV files 
3. computes Power Spectral Density (PSD) and noise metrics for each HLS sequence
4. computes and persists PSD/metrics from the HLS live stream in 10s chunks 

The worker will be useful for multiple purposes, including ship noise analysis, comparative 'false negative' analysis for different detection sources, and generating training audio for the CLAP AI model.

Alternative approaches to the Node worker include using the in-browser Web Audio API, which features a built-in FFT AnalyserNode and streamlined AudioWorklet interface, or the Web Worker API for computationally intensive tasks in the browser like calculating PSD. These could be useful for immediate gratification. RMS loudness and SNR come basically for 'free' from AnalyserNode.

This project builds on the work of several previous contributors. Reference repositories include:
- [ambient-sound-analysis](https://github.com/orcasound/ambient-sound-analysis)
- [seastats-dashboard](https://github.com/orcasound/seastats-dashboard)
- [orcanode-monitor](https://github.com/orcasound/orcanode-monitor)
- [orca-shipnoise](https://github.com/orcasound/orca-shipnoise)
- [bioacoustic-dashboard](https://github.com/orcasound/bioacoustic-dashboard)

How this project differs from and complements other efforts:
1. ambient-sound-analysis -- borrows analytics such as RMS broadband, PSD grids, signal to noise, transience, and applies them for production on the live stream app
2. seastats-dashboard -- borrows analytics like sound level and exceedance, and adds a production data engine, action-oriented UI, and API endpoints
3. orcanode-monitor -- system monitoring is complementary to this project for determining if 'quiet' means system down, or 'loud' means clipping
4. orca-shipnoise -- produces standardized acoustic measures that can be paired with AIS data when available to define the identity, speed, and noise impact of specific vessels
5. bioacoustic-dashboard -- provides the metrics data needed for this or similar dashboards

Below are a series of standard noise analysis metrics that we can calculate, building from basic to most advanced.

### 1. Loudness
How loud is the current noise environment relative to ambient noise floor, max threshold, or long term averages? 

Root-mean-square (RMS) amplitude is a fast/cheap proxy for loudness over the full frequency (broadband) spectrum, and can be calculated quickly using the Web Audio API AnalyserNode. 

Power Spectral Density (PSD) is a more computationally intensive measure of loudness, with high resolution over isolated frequency bands. This should be calculated in the Node worker, or optionally in a Web Worker.

_Chart: average loudness over time_
Calculate RMS or PSD for 1-second time increments. Visualize as a line chart from the last 5-10 minutes on the live streams. Calculate in the browser using the AnalyserNode FFT analyser of the Web Audio API, or by using an AudioWorklet for more resolution and performance.

### 2. Signal-to-noise ratio (SNR) 
How difficult is it to pick out a vocalization from background noise? How hard is it for orcas to hunt or communicate right now? 

_Chart 1: average SNR over time_
The formula for calculating SNR from PSD is: 
SNR (dB) = 20·log10( signal level / noise floor ), with noise floor = P10 (or SPD-derived baseline) for that band/site

Visualize as a line chart from the last 5-10 minutes on the live streams.

_Chart 2: masking index_
For a given time window, calculate the percentage of audio frames where the loudness exceeds the masking threshold. Visualize as a single percentage value.

To define the masking threshold, make an empirical judgement of the minimum loudness where orcas are audible against background noise.


### 4. Rolling noise floor

_Chart: multi-percentile ribbon plot _
Instead of calculating a simple average, which can be easily skewed by spikes, calculate 10%/50%/90% percentiles, e.g. “within X time window, the sound level exceeded a threshold of Y dB, Z% of the time”

- 10th percentile: true background or ambient noise floor, less affected by transient spikes.
- 50th percentile / median: a more stable measure of the central tendency of the noise than the average.
- 90th percentile: upper boundary of the typical noise, useful for identifying the onset of an event.

_Defaults_
- Start with a 60-second rolling window; compute P10/P50/P90. 
- Set the “exceedance threshold” to 90% of the last 24 hours. 
- Optional user controls for time window and level threshold.


### 5. Bandpower bins
What frequency ranges generate the most noise?

To characterize various elements of the sound signal, we need to filter it to certain bands in the frequency spectrum. Standardized bins such as 1/3 octave (LF/MF/HF - low/mid/high frequency) are helpful for comparing results with other references, but many common sounds have documented frequencies. 

_Research_ 
Using documented standards or by analyzing Orcasound archived audio (e.g. by using a CLAP AI assistant to find audio clips - see [#915](https://github.com/orgs/orcasound/projects/52/views/1?pane=issue&itemId=127128531&issue=orcasound%7Corcasite%7C915)), identify frequency bands for:

- Orcas and other animals
- Vessels
- Geophonic sources (rain/wind/current)
- Strikes (objects hitting the hydrophone)

_The 63 and 125 Hz LF vessel-band indicators are standard frequency-band measurements used internationally to monitor underwater noise from large commercial ships. They measure the annual average sound level in one-third octave bands centered at 63 Hz and 125 Hz, which is the low-frequency range where most propeller cavitation noise from large vessels occurs. Source: [Google](https://www.google.com/search?q=Vessel-band+indicators+%2863+%26+125+Hz%29%0D%0A%0D%0AWhat+it+is%3A+Standard+indicators+for+shipping+noise+%28IMO+metrics%29.&sca_esv=9dbcedb0407ac63c&ei=j3vEaKe7Mfak0PEP_aqvuA0&ved=0ahUKEwjnvpyzgdSPAxV2EjQIHX3VC9cQ4dUDCBA&uact=5&oq=Vessel-band+indicators+%2863+%26+125+Hz%29%0D%0A%0D%0AWhat+it+is%3A+Standard+indicators+for+shipping+noise+%28IMO+metrics%29.&gs_lp=Egxnd3Mtd2l6LXNlcnAiZ1Zlc3NlbC1iYW5kIGluZGljYXRvcnMgKDYzICYgMTI1IEh6KQoKV2hhdCBpdCBpczogU3RhbmRhcmQgaW5kaWNhdG9ycyBmb3Igc2hpcHBpbmcgbm9pc2UgKElNTyBtZXRyaWNzKS4yDhAAGIAEGLADGIYDGIoFMg4QABiABBiwAxiGAxiKBTILEAAYgAQYsAMYogQyCxAAGIAEGLADGKIEMggQABiwAxjvBTILEAAYgAQYsAMYogRIpAlQiQdYiQdwA3gAkAEAmAEAoAEAqgEAuAEDyAEA-AEC-AEBmAIDoAILmAMAiAYBkAYGkgcBM6AHALIHALgHAMIHBTAuMi4xyAcI&sclient=gws-wiz-serp)_


### 6. Transience
What are the sources of the loudness, based on typical frequencies and transient characteristics for orcas, vessels, wind/rain/current, or other objects striking the hydrophone? 

To characterize a sound source it would be useful to understand its transience – how sustained or brief the noise is. Orca calls and objects striking the hydrophone are short duration peaks. Vessels and geophonic sources tend to be long, sustained patterns with a slow onset. 

_Chart 1: crest factor_
Crest factor = peak level / average level
A higher ratio means a spikier event. Visualize as a time series or tooltip on each bandpower bin.

_Chart 2: transient rate_
Transient rate = count of short high-crest windows (impulsive transients) per minute

A higher rate suggests either orca calls (what rate, typically?), or object strikes. Visualize as a time series or tooltip on each bandpower bin.


### 7. Sources
What are the sources of the noise on the signal? 

Combining frequency ranges with transient characteristics, estimate what percentage of the broadband level comes from the following sources:

- Vessels: sustained LF (63/125 Hz) rise
- Rain/current: broadband HF hiss increase
- Strikes: high crest, very short impulses
- Orcas: elevated mid/high bands with tonal structure 

Visualize as a bar chart (preferred over pie chart) analyzed from a static WAV file and/or live HLS stream. 

_Extra credit:_
How good is this kind of heuristic audio analysis at picking up whale calls, compared with community scientists, Orcahello AI, or CLAP AI? What is its false positive rate? Do its measurements correlate with other sources, does it detect any ‘false negatives’?


### 8. Trends and seasonality (advanced)
Are the noise levels and distributions we’re seeing today typical, or unusual?

Long term context tells you if today is typical/quiet/extreme, and supports forecasting noise levels into the future.

_Project_
Calculate spectral probability density (SPD) & long-term spectral average (LTSA) from PSD parquet grids.

SeaStats references spd-1m and ltsa-1d uploads in its API examples.

_Visuals_
- LTSA: daily heatmap (time × freq).
- SPD: weekly violin/histogram per band.
- Percent of day above threshold

### 9. Calibration (advanced)
Are our calculations off because of ‘site-specific drift’? Is a period of quiet due to the hydrophone being down? 

[This section represents preliminary research and needs review by @scottveirs @veirs @dbainj1 @dthaler @paulcretu ]

**Why might a simple band-limited transience detector not be effective for detecting calls?**
One reason is “site-specific drift.”
Even if the source (an orca) is the same, the received waveform isn’t, across time or across hydrophones:
- Propagation + room effects: depth, bottom type, multipath/reverberation smear and ring the signal
- A sharp transient at the source can arrive “blurred,” lowering crest factor and spreading energy into nearby bands.
- Local noise texture: wind/rain, current, biotic choruses, mooring creaks differ by site/season → your adaptive thresholds drift.
- Hardware chain: hydrophone sensitivity, preamp/ADC gain, limiter/clipping behavior vary between nodes and over time.
- Stream handling: HLS/encoding settings (bitrate, codec) change dynamic range.

As a result, a simple “repeated short spike in frequency band = orca” rule would tends to either miss calls at some sites/times or over-fire at others. 

However, we can still use it as a fast candidate generator, and it is worth comparing this approach with Orcahello, which also suffers from site-specific drift but is more difficult and expensive to calibrate. 

**Site-specific calibration — what’s needed?** 
Convert dBFS proxies to absolute dB re 1 µPa, we need:

- Instrument sensitivity (S): hydrophone V/µPa (e.g., −170 dB re 1 V/µPa).
- Electronics gain (G): preamp/ADC path gain (dB).
- ADC full-scale (FS): volts at 0 dBFS, bitrate, etc.

Given loudness in digital counts, convert to volts, then to µPa using S and G. Without (S, G, FS), you can still report relative dB with clear caveats.

**Does calculating Long Term Spectral Average (LTSA) / Spectral Probability Density (SPD) help?**
Yes it could.
- LTSA shows long-term typical spectral levels → helps choose site-specific thresholds and detect drifts in gain/noise.
- SPD gives distributions (percentiles) → you can anchor “exceedance” and “masking” to robust, site-specific baselines.

**Do we have all the measurements we need between the live stream FFT metrics and orcanode-monitor?**
Good question for @dthaler 

**How often should we calibrate / indicators?**
When hardware changes, periodically (e.g., quarterly), or when drift indicators are apparent.

_Indicators of drift:_
- LTSA baseline shifts with no environmental cause
- sudden increase in clipping %,
- site floor (p10) jumps across all bands,
- mismatch between known reference events and measured level. 


Is quiet actually downtime?
Query orcanode-monitor by start/end and hydrophone id.

<img width="1185" height="667" alt="Image" src="https://github.com/user-attachments/assets/213f4497-1e73-4b93-be74-574a06d3ecfe" />
