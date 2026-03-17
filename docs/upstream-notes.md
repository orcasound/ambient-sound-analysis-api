# Upstream Notes

Notes for possible issues or documentation improvements to report to `ambient-sound-analysis` / `orcasound_noise` maintainers.

## Confirmed runtime issue

### `NoiseAccessor.get_options()` can fail on malformed S3 object names

- Observed behavior: `NoiseAccessor.get_options()` iterates all objects under the archive prefix and assumes each filename matches the expected parquet naming convention.
- Failure seen in practice: `ValueError: time data 'bush' does not match format '%Y%m%dT%H%M%S'`
- Likely cause: at least one object under the prefix does not follow the expected `{start}_{end}_{secs}_{freq}.parquet` pattern.
- Impact: one malformed key can cause `/options` or any other `get_options()` consumer to fail completely.
- Suggested upstream fix: make `get_options()` skip invalid keys rather than failing the whole scan.

### Some archived parquet filenames do not match the timestamps inside the parquet index

- Observed behavior: the API and accessor discover availability by filename metadata, but at least one archived parquet file has an index range that does not match the filename date range.
- Confirmed example:
  - filename: `20230210T050000_20230210T150000_10s_500hz.parquet`
  - parsed filename range: `2023-02-10T05:00:00` to `2023-02-10T15:00:00`
  - actual parquet index range: `2023-02-20 12:08:21.337768` to `2023-02-20 12:18:21.337768`
- Impact:
  - `/options` can report a valid-looking combination like `sandbox + 500hz + delta_t=10`
  - `NoiseAccessor.create_df(...)` can still return zero rows for requests inside the advertised filename window
  - callers cannot trust filename-derived coverage as true queryable coverage
- Suggested upstream fix:
  - audit the pipeline/file-writing path to ensure parquet index timestamps match the filename date range
  - consider validating parquet index bounds before upload
  - consider surfacing a warning or rejecting files whose internal timestamps disagree with the filename

## Documentation / API clarity gaps

### `get_options()` is not documented clearly enough

- The Noise Accessor docs describe `create_df()` inputs well enough to use the accessor once the caller already knows the valid `delta_t` / `delta_f` combinations.
- But they do not explain `get_options()` clearly, and they do not map its return values back to valid `create_df()` arguments.
- The main missing explanation is: `get_options()` is telling the caller which archived parquet products already exist in S3 for a given hydrophone.

Example interpretation:

- `delta_ts=[1]`
- `delta_fs=[3]`
- `freq_types=['broadband', 'octave_bands']`

This means the archive currently appears to have:

- 1-second time resolution products
- broadband products
- 1/3-octave band products, which correspond to `delta_f="3oct"` when calling `create_df()`

### `delta_fs` is overloaded and therefore confusing

- For files with `freq_type='delta_hz'`, the parsed numeric value represents Hz per band, e.g. `50` from `50hz`.
- For files with `freq_type='octave_bands'`, the parsed numeric value represents octave subdivision count, e.g. `3` from `3oct`, meaning 1/3-octave bands.
- Because both are returned in one list named `delta_fs`, the name can be misleading. It suggests all values are literal Hz resolutions, which is not true.

Possible upstream improvements:

- document this explicitly and give examples
- rename the field in a future version
- or return a more structured shape, e.g. frequency options paired with their type

### The docs should explain how filename suffixes map to accessor arguments

Current code path:

- pipeline with `bands=3` produces filenames ending in `3oct`
- `parse_filename()` maps `3oct` to `freq_value=3`, `freq_type='octave_bands'`
- accessor callers then request those files using `delta_f="3oct"`

This mapping is not obvious from the docs alone.

Useful additions upstream would be:

- examples of `get_options()` output
- explicit mapping from output to valid `create_df()` calls
- a short note that:
  - `broadband` corresponds to `is_broadband=True`
  - `3oct` corresponds to 1/3-octave products
  - `50hz` corresponds to 50 Hz linear bins

Example `get_options()` output:
```json
{
  "hydrophone":"orcasound_lab","delta_ts":[1],"delta_fs":[3],"freq_types":["broadband","octave_bands"]
  }
```

For the orcasound_lab hydrophone, PSDs are available in 1-second time deltas for "broadband" and "octave_bands", but not "delta_hz" (linear bands). 

The delta_fs of 3 means that the octave_bands were specified at 1/3 octave bands, not some other fraction like 1/5. So to create a dataframe for them use delta_f="3oct"

The confusing part is how the examples are written vs what is actually saved to S3.
- Here, `delta_f=1` refers to "1 Hz frequency resolution" which means calculate linear bands at 1 Hz intervals
- `delta_fs` in get_options maps to `bands`

- To access linear frequency bands, use the "hz" suffix. For example, a "50hz" would return frequency bounds in columns like [0, 50, 100, 150...]
- To access (fractions of) octave bands, use the "oct" suffix. "3oct" will return the 1/3 octave bands, starting with [63, 80, 100, 125, 160...]
- To access broadband noise, use the "broadband" suffix. This returns a single column representing the total noise level across all frequencies sensed by the hydrophone recording system.

### About octaves

An octave is a doubling in frequency. For example:

125 Hz to 250 Hz is one octave
250 Hz to 500 Hz is one octave

A 1/3-octave scheme splits each octave into 3 logarithmically spaced bands. That is why the sequence is not linear:
63, 80, 100, 125, 160, 200, 250, 315, ...

Those are standard nominal center frequencies from the ISO R-series tables hardcoded in `acoustic_util.py`. 

### What's the upper limit for the frequencies?

For linear bins:
- the practical upper limit is the Nyquist frequency, which is half the sample rate
- the exact max therefore depends on the audio sample rate of the source recordings

For octave bands in this repo:
- there is still a Nyquist limit underneath
- but the available octave-band centers are also hardcoded
- for 1/3-octave (bands=3), the hardcoded list goes up to 20000
- for 1/6 and finer lists, some go to 22400

One subtle point: the code does not appear to dynamically trim the band list to Nyquist before labeling columns. It applies filter gains against the actual FFT frequency array. So very high bands may become meaningless or near-empty if the recording sample rate cannot support them.


### Example 1: Raw linear bands

In example 1, they are producing both a broadband output and a linear frequency bins at 1 Hz intervals. This is always the case, there is always a broadband output, and a starting frequency resolution for the PSDs. bands=None means it is raw, not aggregated into bands. This produces:
- PSD file ending in `..._60s_1hz.parquet`
- broadband file ending in `...60s_broadband.parquet`

```python
#Example 1: Port Townsend, 1 Hz Frequency, 60-second samples
if __name__ == '__main__':
    pipeline = NoiseAnalysisPipeline(Hydrophone.PORT_TOWNSEND,
                                     delta_f=1, bands=None,
                                     delta_t=60, mode='safe')
```


If this linear-band pipeline were run, you would see it in `get_options` like this:
```json
{
  "hydrophone":"port_townsend","delta_ts":[60],"delta_fs":[1],"freq_types":["broadband","delta_hz"]
  }
```

And you would request it in the NoiseAccessor like this:
Broadband (_Note: there is an `is_broadband` boolean parameter to create_df but it duplicates the delta_f="broadband" param so ignore it._)
```python
ac = NoiseAccessor(Hydrophone.PORT_TOWNSEND)
df = ac.create_df(dt.datetime(2023, 2, 1), dt.datetime(2023, 2, 2), delta_t=60, delta_f="broadband")
```

PSD frequency bands:
```python
ac = NoiseAccessor(Hydrophone.PORT_TOWNSEND)
df = ac.create_df(dt.datetime(2023, 2, 1), dt.datetime(2023, 2, 2), delta_t=60, delta_f="1hz")
```

### Example 2: octave-band aggregation

In example 2, they are producing both a broadband output and octave frequency bins at 1/3 intervals. Changing bands from None to 3 means it first gets the frequencies in 1 Hz intervals, then computes the octave bands as an aggregation. This produces:
- PSD file ending in `..._60s_3oct.parquet`
- broadband file ending in `...60s_broadband.parquet`

```python
#Example 2: Port Townsend, 1 Hz Frequency, 60-second samples, 
# 1/3rd octave bands, and saving wav+pqt files
if __name__ == '__main__':
    pipeline2 = NoiseAnalysisPipeline(Hydrophone.PORT_TOWNSEND,
                                     delta_f=1, bands=3,
                                     delta_t=60, wav_folder = 'wav',
                                     pqt_folder = 'pqt'
                                     mode='safe')
```


If this octave-band pipeline were run, you would see it in `get_options` like this:
```json
{
  "hydrophone":"port_townsend","delta_ts":[60],"delta_fs":[3],"freq_types":["broadband","octave_bands"]
  }
```

And call it in NoiseAccessor like this:
Broadband:
```python
ac = NoiseAccessor(Hydrophone.PORT_TOWNSEND)
df = ac.create_df(dt.datetime(2023, 2, 1), dt.datetime(2023, 2, 2), delta_t=60, delta_f="broadband")
```

PSD frequency bands:
```python
ac = NoiseAccessor(Hydrophone.PORT_TOWNSEND)
df = ac.create_df(dt.datetime(2023, 2, 1), dt.datetime(2023, 2, 2), delta_t=60, delta_f="3oct")
```

### Example 3: What they actually did in storing the S3

This produces:
- PSD file ending in `..._1s_3oct.parquet`
- broadband file ending in `..._1s_broadband.parquet`

```python
#Example 3: Port Townsend, 1 Hz Frequency, 1-second samples, 1/3rd octave bands, and saving wav+pqt files
if __name__ == '__main__':
    pipeline2 = NoiseAnalysisPipeline(Hydrophone.PORT_TOWNSEND,
                                     delta_f=1, # assumption
                                     bands=3, # known 
                                     delta_t=1, # known 
                                     mode='safe')
```


We see it in `get_options` like this:
```json
{
  "hydrophone":"port_townsend","delta_ts":[1],"delta_fs":[3],"freq_types":["broadband","octave_bands"]
  }
```

And call it in NoiseAccessor like this:
Broadband:
```python
ac = NoiseAccessor(Hydrophone.PORT_TOWNSEND)
df = ac.create_df(dt.datetime(2023, 2, 1), dt.datetime(2023, 2, 2), delta_t=1, delta_f="broadband")
```

PSD frequency bands:
```python
ac = NoiseAccessor(Hydrophone.PORT_TOWNSEND)
df = ac.create_df(dt.datetime(2023, 2, 1), dt.datetime(2023, 2, 2), delta_t=1, delta_f="3oct")
```






### The docs should explain what octave bands mean in this repo

- The top-level README mentions fractional octave bands, but the accessor docs could be more explicit.
- A short example would help:
  - `3oct` means 1/3-octave bands
  - output columns are logarithmically spaced band-edge or band-label frequencies such as `63`, `80`, `100`, `125`, `160`, etc.

## Recommendation on reporting

Worth reporting upstream:

- the `get_options()` crash on malformed S3 keys
- the missing or unclear documentation for `get_options()`
- the weak mapping between `get_options()` output and `create_df()` inputs

Probably not a bug, but still worth a documentation issue:

- `delta_fs` being overloaded

That one may be acceptable as an internal implementation detail, but it is confusing enough that a doc issue or small API clarification would be reasonable.

### Python version warning

/usr/local/lib/python3.9/site-packages/boto3/compat.py:89: PythonDeprecationWarning: Boto3 will no longer support Python 3.9 starting April 29, 2026. To continue receiving service updates, bug fixes, and security updates please upgrade to Python 3.10 or later. More information can be found here: https://aws.amazon.com/blogs/developer/python-support-policy-updates-for-aws-sdks-and-tools/
  warnings.warn(warning, PythonDeprecationWarning)


### more options

Is there a way to find out what hydrophones are available?

How about the time ranges that are available?
