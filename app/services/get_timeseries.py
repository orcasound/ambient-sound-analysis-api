from datetime import datetime, timedelta
from functools import lru_cache
import math
from typing import Optional

from app.models.responses import (
    BroadbandTimeseriesResponse,
    PSDTimeseriesPoint,
    PSDTimeseriesResponse,
    TimeseriesPoint,
)
from app.services.get_options import (
    _get_options_for_hydrophone,
    _import_orcasound_noise,
    _normalize_hydrophone_name,
)


MAX_WINDOW_DAYS = 31


class TimeseriesLookupError(RuntimeError):
    pass


class TimeseriesDataIntegrityError(TimeseriesLookupError):
    pass


def _expected_point_count(start: datetime, end: datetime, delta_t: int) -> int:
    duration_seconds = (end - start).total_seconds()
    if duration_seconds <= 0:
        return 0
    return math.ceil(duration_seconds / delta_t)


def _validate_range(
    start: datetime,
    end: datetime,
    max_window_days: Optional[int] = MAX_WINDOW_DAYS,
) -> None:
    if end <= start:
        raise ValueError("end must be after start")
    if max_window_days is not None and end - start > timedelta(days=max_window_days):
        raise ValueError(f"date range must be {max_window_days} days or less")


def _get_hydrophone(raw_hydrophone: str):
    normalized_name = _normalize_hydrophone_name(raw_hydrophone)
    NoiseAccessor, Hydrophone, _ = _import_orcasound_noise()

    try:
        hydrophone = Hydrophone[normalized_name]
    except KeyError as exc:
        valid_names = ", ".join(sorted(member.name.lower() for member in Hydrophone))
        raise ValueError(
            f"invalid hydrophone '{raw_hydrophone}'. Valid values: {valid_names}"
        ) from exc

    return NoiseAccessor, hydrophone


def _matching_file_count(hydrophone: object, start: datetime, end: datetime, delta_t: int, delta_f: str) -> int:
    _, _, S3FileConnector = _import_orcasound_noise()
    connector = S3FileConnector(hydrophone, no_sign=True)
    filepaths = connector.get_files(
        start=start,
        end=end,
        secs_per_sample=delta_t,
        hz_bands=None if delta_f == "broadband" else delta_f,
        is_broadband=delta_f == "broadband",
    )
    return len(filepaths)


def _parse_psd_delta_f(delta_f: str) -> tuple[str, int]:
    normalized_delta_f = delta_f.strip().lower()
    if normalized_delta_f.endswith("oct"):
        try:
            return "octave_bands", int(normalized_delta_f.removesuffix("oct"))
        except ValueError as exc:
            raise ValueError(f"invalid octave-band delta_f '{delta_f}'") from exc
    if normalized_delta_f.endswith("hz"):
        try:
            return "delta_hz", int(normalized_delta_f.removesuffix("hz"))
        except ValueError as exc:
            raise ValueError(f"invalid linear-band delta_f '{delta_f}'") from exc
    raise ValueError(
        "delta_f must use the archived accessor format such as '3oct' or '500hz'"
    )


def _validate_psd_request(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    delta_t: int,
    delta_f: str,
) -> None:
    hydrophone_options = _get_options_for_hydrophone(raw_hydrophone)
    freq_type, freq_value = _parse_psd_delta_f(delta_f)
    available_options = getattr(hydrophone_options, freq_type)

    matching_option = next(
        (
            option
            for option in available_options
            if option.delta_f == freq_value and option.delta_t == delta_t
        ),
        None,
    )

    if matching_option is None:
        available_pairs = ", ".join(
            f"{option.delta_f}{'oct' if freq_type == 'octave_bands' else 'hz'} @ {option.delta_t}s"
            for option in available_options
        )
        if not available_pairs:
            available_pairs = "none"
        raise ValueError(
            f"No PSD combination for hydrophone '{raw_hydrophone}': "
            f"delta_f={delta_f}, delta_t={delta_t}. Available {freq_type} combinations: {available_pairs}"
        )

    if matching_option.first_start and matching_option.last_end:
        coverage_start = datetime.fromisoformat(matching_option.first_start)
        coverage_end = datetime.fromisoformat(matching_option.last_end)
        if end < coverage_start or start > coverage_end:
            raise ValueError(
                f"requested time window is outside the coverage area for "
                f"{delta_f} @ {delta_t}s on hydrophone '{raw_hydrophone}'. "
                f"Coverage spans {matching_option.first_start} to {matching_option.last_end}"
            )


def _validate_broadband_request(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    delta_t: int,
) -> None:
    hydrophone_options = _get_options_for_hydrophone(raw_hydrophone)

    matching_option = next(
        (
            option
            for option in hydrophone_options.broadband
            if option.delta_t == delta_t
        ),
        None,
    )

    if matching_option is None:
        available_delta_ts = ", ".join(
            f"{option.delta_t}s" for option in hydrophone_options.broadband
        )
        if not available_delta_ts:
            available_delta_ts = "none"
        raise ValueError(
            f"No broadband combination for hydrophone '{raw_hydrophone}': "
            f"delta_t={delta_t}. Available broadband combinations: {available_delta_ts}"
        )

    if matching_option.first_start and matching_option.last_end:
        coverage_start = datetime.fromisoformat(matching_option.first_start)
        coverage_end = datetime.fromisoformat(matching_option.last_end)
        if end < coverage_start or start > coverage_end:
            raise ValueError(
                f"requested time window is outside the coverage area for "
                f"broadband @ {delta_t}s on hydrophone '{raw_hydrophone}'. "
                f"Coverage spans {matching_option.first_start} to {matching_option.last_end}"
            )


def _load_timeseries_df(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    delta_t: int,
    delta_f: str,
    detect_data_integrity: bool = False,
    max_window_days: Optional[int] = MAX_WINDOW_DAYS,
):
    if delta_t <= 0:
        raise ValueError("delta_t must be greater than 0")

    _validate_range(start, end, max_window_days=max_window_days)
    NoiseAccessor, hydrophone = _get_hydrophone(raw_hydrophone)

    try:
        df = NoiseAccessor(hydrophone).create_df(
            start=start,
            end=end,
            delta_t=delta_t,
            delta_f=delta_f,
        )
    except ValueError as exc:
        if str(exc) == "No objects to concatenate":
            df = None
        else:
            raise TimeseriesLookupError(
                f"failed to load timeseries for hydrophone '{hydrophone.name.lower()}'"
            ) from exc
    except Exception as exc:
        raise TimeseriesLookupError(
            f"failed to load timeseries for hydrophone '{hydrophone.name.lower()}'"
        ) from exc

    if detect_data_integrity:
        matching_files = _matching_file_count(hydrophone, start, end, delta_t, delta_f)
        if matching_files > 0 and (df is None or df.empty):
            raise TimeseriesDataIntegrityError(
                "Archived parquet file(s) were found matching this time window by file name, but no rows in the file matched the time window"
            )

    return hydrophone, df


@lru_cache(maxsize=128)
def _get_broadband_timeseries_cached(
    normalized_hydrophone: str,
    start: datetime,
    end: datetime,
    delta_t: int,
    validate: bool = True,
) -> BroadbandTimeseriesResponse:
    if validate:
        _validate_broadband_request(normalized_hydrophone, start, end, delta_t)

    hydrophone, df = _load_timeseries_df(
        normalized_hydrophone,
        start,
        end,
        delta_t,
        "broadband",
        detect_data_integrity=False,
    )

    points: list[TimeseriesPoint] = []
    if df is not None and not df.empty:
        value_column = df.columns[0]
        points = [
            TimeseriesPoint(timestamp=index.isoformat(), value=float(value))
            for index, value in df[value_column].items()
        ]

    return BroadbandTimeseriesResponse(
        hydrophone=hydrophone.name.lower(),
        delta_t=delta_t,
        start=start.isoformat(),
        end=end.isoformat(),
        expected_point_count=_expected_point_count(start, end, delta_t),
        point_count=len(points),
        points=points,
    )


def get_broadband_timeseries(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    delta_t: int,
    validate: bool = True,
) -> BroadbandTimeseriesResponse:
    normalized_hydrophone = raw_hydrophone.strip().lower()
    return _get_broadband_timeseries_cached(
        normalized_hydrophone, start, end, delta_t, validate
    )


@lru_cache(maxsize=128)
def _get_psd_timeseries_cached(
    normalized_hydrophone: str,
    start: datetime,
    end: datetime,
    delta_t: int,
    delta_f: str,
    validate: bool = True,
) -> PSDTimeseriesResponse:
    normalized_delta_f = delta_f.strip().lower()
    if not normalized_delta_f:
        raise ValueError("delta_f is required")
    if normalized_delta_f == "broadband":
        raise ValueError("use /timeseries/broadband for broadband data")

    if validate:
        _validate_psd_request(
            normalized_hydrophone, start, end, delta_t, normalized_delta_f
        )

    hydrophone, df = _load_timeseries_df(
        normalized_hydrophone,
        start,
        end,
        delta_t,
        normalized_delta_f,
        detect_data_integrity=False,
    )

    columns: list[str] = []
    points: list[PSDTimeseriesPoint] = []
    if df is not None and not df.empty:
        columns = [str(column) for column in df.columns]
        points = [
            PSDTimeseriesPoint(
                timestamp=index.isoformat(),
                values=[float(value) for value in row],
            )
            for index, row in zip(df.index, df.to_numpy())
        ]

    return PSDTimeseriesResponse(
        hydrophone=hydrophone.name.lower(),
        delta_t=delta_t,
        delta_f=normalized_delta_f,
        start=start.isoformat(),
        end=end.isoformat(),
        expected_point_count=_expected_point_count(start, end, delta_t),
        point_count=len(points),
        columns=columns,
        points=points,
    )


def get_psd_timeseries(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    delta_t: int,
    delta_f: str,
    validate: bool = True,
) -> PSDTimeseriesResponse:
    normalized_hydrophone = raw_hydrophone.strip().lower()
    return _get_psd_timeseries_cached(
        normalized_hydrophone, start, end, delta_t, delta_f, validate
    )
