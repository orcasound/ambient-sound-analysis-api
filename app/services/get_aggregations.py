from datetime import date
import math
from typing import Any, Tuple

from app.models.responses import (
    DailyBroadbandPoint,
    DailyBroadbandSummaryResponse,
    DailySummaryPoint,
    DailySummaryResponse,
)
from app.services.get_options import _import_orcasound_noise, _normalize_hydrophone_name


class AggregationLookupError(RuntimeError):
    pass


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
