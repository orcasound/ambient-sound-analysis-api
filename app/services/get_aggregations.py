from datetime import date, datetime, timedelta
from functools import lru_cache
import math
from typing import Any, Tuple

from app.models.responses import (
    BroadbandAggregationPoint,
    BroadbandAggregationResponse,
    DailyBroadbandPoint,
    DailyBroadbandSummaryResponse,
    PSDHeatmapResponse,
    DailySummaryPoint,
    DailySummaryResponse,
)
from app.services.get_options import _import_orcasound_noise, _normalize_hydrophone_name


class AggregationLookupError(RuntimeError):
    pass


AGGREGATION_RULES = {
    "10s": "10S",
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1H",
    "1d": "1D",
}
AGGREGATION_INTERVALS = {
    "10s": timedelta(seconds=10),
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}
MAX_AGGREGATION_POINTS = 2000
AUTO_INTERVAL_TARGET_POINTS = 1000


def _import_daily_noise_analysis() -> Tuple[Any, Any]:
    try:
        _, Hydrophone, _ = _import_orcasound_noise()
        from orcasound_noise.analysis import DailyNoiseAnalysis
    except ImportError as exc:
        raise AggregationLookupError(
            "DailyNoiseAnalysis is not installed or not importable in this environment"
        ) from exc
    return DailyNoiseAnalysis, Hydrophone


def _mean_band_range(
    df: Any,
    band_low: int,
    band_high: int,
) -> Any:
    numeric_columns = [
        column for column in df.columns if _is_in_band(column, band_low, band_high)
    ]
    if not numeric_columns:
        raise ValueError(f"no columns available in band range {band_low}-{band_high}")
    return df.loc[:, numeric_columns].mean(axis=1, skipna=True)


def _is_in_band(column: Any, band_low: int, band_high: int) -> bool:
    try:
        value = float(column)
    except (TypeError, ValueError):
        return False
    return band_low <= value <= band_high


def _series_to_points(series: Any) -> list[DailySummaryPoint]:
    points: list[DailySummaryPoint] = []
    for index, value in series.items():
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            continue
        points.append(DailySummaryPoint(time_of_day=str(index), value=numeric_value))
    return points


def _broadband_series_to_points(series: Any) -> list[DailyBroadbandPoint]:
    points: list[DailyBroadbandPoint] = []
    for index, value in series.items():
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            continue
        points.append(DailyBroadbandPoint(date=str(index), value=numeric_value))
    return points


def _resolve_hydrophone(raw_hydrophone: str) -> tuple[str, Any, Any]:
    normalized_name = _normalize_hydrophone_name(raw_hydrophone)
    DailyNoiseAnalysis, Hydrophone = _import_daily_noise_analysis()

    try:
        hydrophone = Hydrophone[normalized_name]
    except KeyError as exc:
        valid_names = ", ".join(sorted(member.name.lower() for member in Hydrophone))
        raise ValueError(
            f"invalid hydrophone '{raw_hydrophone}'. Valid values: {valid_names}"
        ) from exc

    return normalized_name, DailyNoiseAnalysis, hydrophone


def _normalize_interval(interval: str) -> tuple[str, str]:
    normalized_interval = interval.strip().lower()
    if normalized_interval not in AGGREGATION_RULES:
        valid_values = ", ".join([*AGGREGATION_RULES.keys(), "auto"])
        raise ValueError(
            f"invalid interval '{interval}'. Valid values for this time range: {valid_values}"
        )
    return normalized_interval, AGGREGATION_RULES[normalized_interval]


def _resolve_interval(interval: str, start: datetime, end: datetime) -> tuple[str, str]:
    normalized_interval = interval.strip().lower()
    if normalized_interval != "auto":
        return _normalize_interval(interval)

    if end <= start:
        raise ValueError("end must be after start")

    window = end - start
    candidates = [
        (label, delta)
        for label, delta in AGGREGATION_INTERVALS.items()
        if window >= delta
    ]
    if not candidates:
        raise ValueError(
            "requested time window is shorter than the smallest supported aggregation interval '10s'"
        )

    for label, delta in candidates:
        estimated_points = math.ceil(window / delta)
        if estimated_points <= AUTO_INTERVAL_TARGET_POINTS:
            return label, AGGREGATION_RULES[label]

    coarsest_label = candidates[-1][0]
    return coarsest_label, AGGREGATION_RULES[coarsest_label]


def _validate_aggregation_window(
    start: datetime,
    end: datetime,
    interval: str,
) -> None:
    if end <= start:
        raise ValueError("end must be after start")

    window = end - start
    interval_size = AGGREGATION_INTERVALS[interval]
    if window < interval_size:
        raise ValueError(
            f"requested time window ({window}) is shorter than the aggregation interval "
            f"'{interval}'"
        )


def _aggregated_broadband_points(df: Any, rule: str) -> list[BroadbandAggregationPoint]:
    if df is None or df.empty:
        return []

    aggregated = df.iloc[:, 0].resample(rule).mean()
    points: list[BroadbandAggregationPoint] = []
    for index, value in aggregated.items():
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            continue
        points.append(
            BroadbandAggregationPoint(
                timestamp=index.isoformat(),
                value=numeric_value,
            )
        )
    return points


def _next_month_start(value: datetime) -> datetime:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return value.replace(month=value.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _iter_monthly_chunks(
    start: datetime,
    end: datetime,
) -> list[tuple[datetime, datetime]]:
    chunks: list[tuple[datetime, datetime]] = []
    chunk_start = start

    while chunk_start < end:
        next_month = _next_month_start(chunk_start)
        chunk_end = min(end, next_month)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end

    return chunks


def _iter_fixed_chunks(
    start: datetime,
    end: datetime,
    chunk_size: timedelta,
) -> list[tuple[datetime, datetime]]:
    chunks: list[tuple[datetime, datetime]] = []
    chunk_start = start

    while chunk_start < end:
        chunk_end = min(end, chunk_start + chunk_size)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end

    return chunks


def _merge_broadband_points(
    chunks: list[list[BroadbandAggregationPoint]],
) -> list[BroadbandAggregationPoint]:
    merged: dict[str, BroadbandAggregationPoint] = {}
    for points in chunks:
        for point in points:
            merged[point.timestamp] = point
    return [merged[timestamp] for timestamp in sorted(merged.keys())]


def _aggregate_psd_matrix(df: Any, rule: str) -> tuple[list[str], list[str], list[list[float]]]:
    if df is None or df.empty:
        return [], [], []

    aggregated = df.resample(rule).mean()
    aggregated = aggregated.dropna(how="all")
    if aggregated.empty:
        return [], [], []

    times = [index.isoformat() for index in aggregated.index]
    frequencies = [str(column) for column in aggregated.columns]
    values: list[list[float]] = []
    for row in aggregated.to_numpy():
        values.append([float(value) for value in row])
    return times, frequencies, values


def _merge_psd_chunks(
    chunks: list[tuple[list[str], list[str], list[list[float]]]],
) -> tuple[list[str], list[str], list[list[float]]]:
    frequencies: list[str] = []
    merged_rows: dict[str, list[float]] = {}

    for chunk_times, chunk_frequencies, chunk_values in chunks:
        if not chunk_times:
            continue
        if not frequencies:
            frequencies = chunk_frequencies
        elif chunk_frequencies != frequencies:
            raise AggregationLookupError(
                "PSD aggregation encountered inconsistent frequency columns across chunks"
            )

        for timestamp, row in zip(chunk_times, chunk_values):
            merged_rows[timestamp] = row

    times = sorted(merged_rows.keys())
    values = [merged_rows[timestamp] for timestamp in times]
    return times, frequencies, values


def get_daily_summary(
    raw_hydrophone: str,
    start_date: date,
    num_days: int,
    band_low: int,
    band_high: int,
) -> DailySummaryResponse:
    if num_days <= 0:
        raise ValueError("num_days must be greater than 0")
    if band_low > band_high:
        raise ValueError("band_low must be less than or equal to band_high")

    _, DailyNoiseAnalysis, hydrophone = _resolve_hydrophone(raw_hydrophone)

    try:
        summary = DailyNoiseAnalysis(hydrophone).create_daily_noise_summary_df(
            start_date, num_days
        )
    except Exception as exc:
        raise AggregationLookupError(
            f"failed to load daily summary for hydrophone '{hydrophone.name.lower()}'"
        ) from exc

    try:
        mean_series = _mean_band_range(summary["mean"], band_low, band_high)
        min_series = _mean_band_range(summary["min"], band_low, band_high)
        max_series = _mean_band_range(summary["max"], band_low, band_high)
        count_series = summary["count"].mean(axis=1, skipna=True)
    except Exception as exc:
        raise AggregationLookupError(
            f"failed to shape daily summary for hydrophone '{hydrophone.name.lower()}'"
        ) from exc

    mean_points = _series_to_points(mean_series)
    min_points = _series_to_points(min_series)
    max_points = _series_to_points(max_series)
    count_points = _series_to_points(count_series)

    return DailySummaryResponse(
        hydrophone=hydrophone.name.lower(),
        start_date=start_date.isoformat(),
        num_days=num_days,
        band_low=band_low,
        band_high=band_high,
        description=(
            "This summary shows the typical daily sound pattern for a hydrophone within a specified frequency range. The four series mean, min, max, and count show data points for each second of the day."
        ),
        mean_length=len(mean_points),
        min_length=len(min_points),
        max_length=len(max_points),
        count_length=len(count_points),
        mean=mean_points,
        min=min_points,
        max=max_points,
        count=count_points,
    )


def get_daily_broadband_summary(
    raw_hydrophone: str,
    start_date: date,
    num_days: int,
) -> DailyBroadbandSummaryResponse:
    if num_days <= 0:
        raise ValueError("num_days must be greater than 0")

    _, DailyNoiseAnalysis, hydrophone = _resolve_hydrophone(raw_hydrophone)

    try:
        summary = DailyNoiseAnalysis(hydrophone).create_broadband_daily_noise(
            start_date, num_days
        )
        broadband_series = summary.iloc[:, 0]
    except Exception as exc:
        raise AggregationLookupError(
            f"failed to load broadband daily summary for hydrophone '{hydrophone.name.lower()}'"
        ) from exc

    points = _broadband_series_to_points(broadband_series)

    return DailyBroadbandSummaryResponse(
        hydrophone=hydrophone.name.lower(),
        start_date=start_date.isoformat(),
        num_days=num_days,
        summary_purpose=(
            "This endpoint shows one true broadband average per day across the "
            "requested date window. Unlike the PSD-band daily summary, it uses the "
            "upstream broadband product rather than averaging selected PSD bands."
        ),
        point_count=len(points),
        points=points,
    )


def get_broadband_aggregation(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    interval: str,
    delta_t: int = 1,
    validate: bool = True,
) -> BroadbandAggregationResponse:
    normalized_hydrophone = _normalize_hydrophone_name(raw_hydrophone)
    return _get_broadband_aggregation_cached(
        normalized_hydrophone,
        start,
        end,
        interval,
        delta_t,
        validate,
    )


@lru_cache(maxsize=64)
def _get_broadband_aggregation_cached(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    interval: str,
    delta_t: int = 1,
    validate: bool = True,
) -> BroadbandAggregationResponse:
    from app.services.get_timeseries import _load_timeseries_df, _validate_broadband_request

    normalized_interval, rule = _resolve_interval(interval, start, end)
    if delta_t <= 0:
        raise ValueError("delta_t must be greater than 0")
    _validate_aggregation_window(start, end, normalized_interval)

    if validate:
        _validate_broadband_request(raw_hydrophone, start, end, delta_t)

    chunked_points: list[list[BroadbandAggregationPoint]] = []
    hydrophone = None
    for chunk_start, chunk_end in _iter_monthly_chunks(start, end):
        hydrophone, df = _load_timeseries_df(
            raw_hydrophone,
            chunk_start,
            chunk_end,
            delta_t,
            "broadband",
            detect_data_integrity=False,
        )
        chunked_points.append(_aggregated_broadband_points(df, rule))

    if hydrophone is None:
        raise AggregationLookupError(
            f"failed to resolve hydrophone '{raw_hydrophone}' for broadband aggregation"
        )

    points = _merge_broadband_points(chunked_points)
    if len(points) > MAX_AGGREGATION_POINTS:
        raise ValueError(
            f"requested aggregation produced {len(points)} points, which exceeds the limit of "
            f"{MAX_AGGREGATION_POINTS}. Choose a coarser interval or shorter time window."
        )

    return BroadbandAggregationResponse(
        hydrophone=hydrophone.name.lower(),
        start=start.isoformat(),
        end=end.isoformat(),
        interval=normalized_interval,
        summary_purpose=(
            "This endpoint returns a chronologically aggregated broadband series for browser "
            "plotting. It starts from true broadband timeseries data and groups it into the "
            "requested time bucket."
        ),
        point_count=len(points),
        points=points,
    )


def get_psd_heatmap(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    interval: str,
    delta_f: str,
    delta_t: int = 1,
    validate: bool = True,
) -> PSDHeatmapResponse:
    normalized_hydrophone = _normalize_hydrophone_name(raw_hydrophone)
    return _get_psd_heatmap_cached(
        normalized_hydrophone,
        start,
        end,
        interval,
        delta_f,
        delta_t,
        validate,
    )


@lru_cache(maxsize=64)
def _get_psd_heatmap_cached(
    raw_hydrophone: str,
    start: datetime,
    end: datetime,
    interval: str,
    delta_f: str,
    delta_t: int = 1,
    validate: bool = True,
) -> PSDHeatmapResponse:
    from app.services.get_timeseries import _load_timeseries_df, _validate_psd_request

    normalized_interval, rule = _resolve_interval(interval, start, end)
    normalized_delta_f = delta_f.strip().lower()
    if not normalized_delta_f:
        raise ValueError("delta_f is required")
    if normalized_delta_f == "broadband":
        raise ValueError("use /aggregations/broadband for broadband data")
    if delta_t <= 0:
        raise ValueError("delta_t must be greater than 0")
    _validate_aggregation_window(start, end, normalized_interval)

    if validate:
        _validate_psd_request(raw_hydrophone, start, end, delta_t, normalized_delta_f)

    hydrophone = None
    chunked_matrices: list[tuple[list[str], list[str], list[list[float]]]] = []
    for chunk_start, chunk_end in _iter_fixed_chunks(
        start,
        end,
        timedelta(days=1),
    ):
        hydrophone, df = _load_timeseries_df(
            raw_hydrophone,
            chunk_start,
            chunk_end,
            delta_t,
            normalized_delta_f,
            detect_data_integrity=False,
        )
        chunked_matrices.append(_aggregate_psd_matrix(df, rule))

    if hydrophone is None:
        raise AggregationLookupError(
            f"failed to resolve hydrophone '{raw_hydrophone}' for PSD aggregation"
        )

    times, frequencies, values = _merge_psd_chunks(chunked_matrices)
    if len(times) > MAX_AGGREGATION_POINTS:
        raise ValueError(
            f"requested aggregation produced {len(times)} time buckets, which exceeds the limit of "
            f"{MAX_AGGREGATION_POINTS}. Choose a coarser interval or shorter time window."
        )

    return PSDHeatmapResponse(
        hydrophone=hydrophone.name.lower(),
        start=start.isoformat(),
        end=end.isoformat(),
        delta_t=delta_t,
        delta_f=normalized_delta_f,
        interval=normalized_interval,
        summary_purpose=(
            "This endpoint returns a time-frequency matrix for browser plotting. "
            "Each row is one aggregated time bucket, each column is one archived PSD band, "
            "and each cell is the mean PSD value for that bucket."
        ),
        time_count=len(times),
        frequency_count=len(frequencies),
        times=times,
        frequencies=frequencies,
        values=values,
    )
