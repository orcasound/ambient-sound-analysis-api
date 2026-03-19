from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query, Response

from app.models.responses import (
    BroadbandAggregationResponse,
    DailyBroadbandSummaryResponse,
    DailySummaryResponse,
    PSDHeatmapResponse,
)
from app.services.get_options import OptionsDependencyError
from app.services.get_aggregations import (
    AggregationLookupError,
    get_broadband_aggregation,
    get_daily_broadband_summary,
    get_daily_summary,
    get_psd_heatmap,
)


router = APIRouter(prefix="/aggregations", tags=["aggregations"])

# second-of-day average/min/max (86400 data points) for selected frequency range and number of days
@router.get("/daily-summary", response_model=DailySummaryResponse)
def daily_summary(
    hydrophone: str = Query(..., description="Hydrophone slug, e.g. bush_point."),
    start_date: date = Query(..., description="Start date in YYYY-MM-DD."),
    num_days: int = Query(..., description="Number of days to include."),
    band_low: int = Query(63, description="Inclusive low band for averaging."),
    band_high: int = Query(8000, description="Inclusive high band for averaging."),
    interval: str = Query(
        "auto",
        description="Aggregation bucket for the second-of-day summary: 10s, 1m, 5m, 15m, 1h, 1d, or auto.",
    ),
) -> DailySummaryResponse:
    try:
        return get_daily_summary(
            hydrophone,
            start_date,
            num_days,
            band_low,
            band_high,
            interval,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OptionsDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AggregationLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

# daily broadband average for selected number of days
@router.get("/daily-broadband-summary", response_model=DailyBroadbandSummaryResponse)
def daily_broadband_summary(
    hydrophone: str = Query(..., description="Hydrophone slug, e.g. bush_point."),
    start_date: date = Query(..., description="Start date in YYYY-MM-DD."),
    num_days: int = Query(..., description="Number of days to include."),
) -> DailyBroadbandSummaryResponse:
    try:
        return get_daily_broadband_summary(hydrophone, start_date, num_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OptionsDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AggregationLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/broadband", response_model=BroadbandAggregationResponse)
def broadband_aggregation(
    response: Response,
    hydrophone: str = Query(..., description="Hydrophone slug, e.g. bush_point."),
    start: datetime = Query(..., description="Start datetime in ISO 8601 format."),
    end: datetime = Query(..., description="End datetime in ISO 8601 format."),
    interval: str = Query(
        ...,
        description="Aggregation bucket: 10s, 1m, 5m, 15m, 1h, 1d, or auto.",
    ),
    delta_t: int = Query(1, description="Underlying broadband sample spacing in seconds."),
    validate: bool = Query(True, description="Validate coverage before loading data."),
) -> BroadbandAggregationResponse:
    try:
        payload = get_broadband_aggregation(
            raw_hydrophone=hydrophone,
            start=start,
            end=end,
            interval=interval,
            delta_t=delta_t,
            validate=validate,
        )
        response.headers["X-Point-Count"] = str(payload.point_count)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OptionsDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AggregationLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/psd", response_model=PSDHeatmapResponse)
def psd_heatmap(
    response: Response,
    hydrophone: str = Query(..., description="Hydrophone slug, e.g. bush_point."),
    start: datetime = Query(..., description="Start datetime in ISO 8601 format."),
    end: datetime = Query(..., description="End datetime in ISO 8601 format."),
    interval: str = Query(
        ...,
        description="Aggregation bucket: 10s, 1m, 5m, 15m, 1h, 1d, or auto.",
    ),
    delta_f: str = Query(..., description="Archived PSD selector such as 3oct, 12oct, or 500hz."),
    delta_t: int = Query(1, description="Underlying PSD sample spacing in seconds."),
    validate: bool = Query(True, description="Validate coverage before loading data."),
) -> PSDHeatmapResponse:
    try:
        payload = get_psd_heatmap(
            raw_hydrophone=hydrophone,
            start=start,
            end=end,
            interval=interval,
            delta_f=delta_f,
            delta_t=delta_t,
            validate=validate,
        )
        response.headers["X-Time-Count"] = str(payload.time_count)
        response.headers["X-Frequency-Count"] = str(payload.frequency_count)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OptionsDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AggregationLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
