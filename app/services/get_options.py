from functools import lru_cache
from typing import Any, Iterable, Optional, Tuple

from app.models.responses import (
    FrequencyBandOptions,
    HydrophoneOptions,
    OptionsResponse,
    TimeResolutionOptions,
)


# *** ERROR HANDLING ***

class OptionsDependencyError(RuntimeError):
    pass


class OptionsLookupError(RuntimeError):
    pass

# make sure the input string looks like 'ORCASOUND_LAB' etc)
def _normalize_hydrophone_name(raw_hydrophone: str) -> str:
    normalized = raw_hydrophone.strip().upper().replace(" ", "_").replace("-", "_")
    if not normalized:
        raise ValueError("hydrophone is required")
    return normalized

# this supplies an error message if requirements.txt hasn't been installed
def _import_orcasound_noise() -> Tuple[Any, Any, Any]:
    try:
        from orcasound_noise.analysis.accessor import NoiseAccessor
        from orcasound_noise.utils import Hydrophone, S3FileConnector
    except ImportError as exc:
        raise OptionsDependencyError(
            "orcasound_noise is not installed or not importable in this environment"
        ) from exc

    return NoiseAccessor, Hydrophone, S3FileConnector


def _sort_unique(values: Iterable[Any]) -> list[Any]:
    return sorted(set(values))


def get_available_hydrophones() -> list[str]:
    _, Hydrophone, _ = _import_orcasound_noise()
    return sorted(
        member.name.lower()
        for member in Hydrophone
        if member.name.upper() == member.name
    )


@lru_cache(maxsize=16)
def _cached_available_hydrophones() -> tuple[str, ...]:
    return tuple(get_available_hydrophones())


def _default_option_hydrophones() -> tuple[str, ...]:
    return tuple(
        hydrophone
        for hydrophone in _cached_available_hydrophones()
        if hydrophone != "sandbox"
    )


def _empty_coverage_summary() -> dict[str, Any]:
    return {
        "starts": [],
        "ends": [],
        "file_count": 0,
    }


def _key_matches_hydrophone(key: str, hydrophone_name: str, save_folder: str) -> bool:
    hydrophone_segment = f"/{hydrophone_name}/"
    partition_segment = f"hydrophone={hydrophone_name}"
    normalized_prefix = save_folder.rstrip("/")

    if normalized_prefix.endswith(f"/{hydrophone_name}"):
        return key.startswith(f"{normalized_prefix}/")

    return partition_segment in key or hydrophone_segment in key


def _scan_hydrophone_archive(hydrophone: Any) -> dict[str, Any]:
    _, _, S3FileConnector = _import_orcasound_noise()

    try:
        connector = S3FileConnector(hydrophone, no_sign=True)
    except Exception as exc:
        raise OptionsLookupError(
            f"failed to initialize archive lookup for hydrophone '{hydrophone.name.lower()}'"
        ) from exc

    summary = {
        "broadband": {},
        "octave_bands": {},
        "delta_hz": {},
    }

    try:
        for item in connector.archive_resource.objects.filter(Prefix=connector.save_folder):
            if not _key_matches_hydrophone(
                item.key,
                hydrophone.name.lower(),
                connector.save_folder,
            ):
                continue

            filename = item.key.split("/")[-1]
            if not filename.endswith(".parquet") or filename.startswith("ancient"):
                continue

            try:
                start, end, secs, freq_value, freq_type = connector.parse_filename(
                    filename
                )
            except (IndexError, TypeError, ValueError):
                continue

            if freq_type not in summary:
                continue

            if freq_type == "broadband":
                group = summary["broadband"].setdefault(secs, _empty_coverage_summary())
            else:
                group = summary[freq_type].setdefault(
                    (freq_value, secs), _empty_coverage_summary()
                )

            group["starts"].append(start)
            group["ends"].append(end)
            group["file_count"] += 1
    except Exception as exc:
        raise OptionsLookupError(
            f"failed to load archive summary for hydrophone '{hydrophone.name.lower()}'"
        ) from exc

    return summary


def _build_time_resolution_options(
    summary_by_delta_t: dict[int, dict[str, Any]]
) -> list[TimeResolutionOptions]:
    options = []
    for delta_t, summary in sorted(summary_by_delta_t.items()):
        starts = summary["starts"]
        ends = summary["ends"]
        options.append(
            TimeResolutionOptions(
                delta_t=delta_t,
                first_start=min(starts).isoformat() if starts else None,
                last_end=max(ends).isoformat() if ends else None,
                file_count=summary["file_count"],
            )
        )
    return options


def _build_frequency_band_options(
    summary_by_key: dict[tuple[int, int], dict[str, Any]]
) -> list[FrequencyBandOptions]:
    options = []
    for (delta_f, delta_t), summary in sorted(summary_by_key.items()):
        starts = summary["starts"]
        ends = summary["ends"]
        options.append(
            FrequencyBandOptions(
                delta_f=delta_f,
                delta_t=delta_t,
                first_start=min(starts).isoformat() if starts else None,
                last_end=max(ends).isoformat() if ends else None,
                file_count=summary["file_count"],
            )
        )
    return options


# GET OPTIONS
# Each hydrophone record looks like:
# hydrophone='orcasound_lab' delta_ts=[1] delta_fs=[3] freq_types=['broadband', 'octave_bands']
# - `delta_ts` -- available time resolutions, i.e. 1 second, maps to delta_t in pipeline
# - `delta_fs` -- available linear or octave band intervals, i.e. 1/3 octave or 1 Hz linear
# - `freq_types` -- broadband is always available, the other types are `octave_band` or `delta_hz` (linear)
# call this in NoiseAccessor as delta_t={delta_ts} and delta_f={freq_type}
# freq_type: 'broadband' = 'broadband'; 'octave_bands / 3' = '3oct'; 'delta_hz / 1' = '1hz'

def _get_options_for_hydrophone(raw_hydrophone: str) -> HydrophoneOptions:
    normalized_name = _normalize_hydrophone_name(raw_hydrophone)
    return _get_options_for_normalized_hydrophone(normalized_name)


@lru_cache(maxsize=16)
def _get_options_for_normalized_hydrophone(normalized_name: str) -> HydrophoneOptions:
    _, Hydrophone, _ = _import_orcasound_noise()

    try:
        hydrophone = Hydrophone[normalized_name]
    except KeyError as exc:
        valid_names = ", ".join(_cached_available_hydrophones())
        raise ValueError(
            f"invalid hydrophone '{normalized_name.lower()}'. Valid values: {valid_names}"
        ) from exc

    summary = _scan_hydrophone_archive(hydrophone)

    return HydrophoneOptions(
        hydrophone=hydrophone.name.lower(),
        broadband=_build_time_resolution_options(summary["broadband"]),
        octave_bands=_build_frequency_band_options(summary["octave_bands"]),
        delta_hz=_build_frequency_band_options(summary["delta_hz"]),
    )


def get_options(raw_hydrophone: Optional[str] = None) -> OptionsResponse:
    if raw_hydrophone:
        hydrophone_options = [_get_options_for_hydrophone(raw_hydrophone)]
    else:
        hydrophone_options = [
            _get_options_for_normalized_hydrophone(hydrophone.upper())
            for hydrophone in _default_option_hydrophones()
        ]
    return OptionsResponse(hydrophones=hydrophone_options)

if __name__ == "__main__": 
    print(get_options().model_dump())
