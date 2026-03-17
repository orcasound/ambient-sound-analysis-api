from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.models.responses import (
    DailyBroadbandSummaryResponse,
    DailySummaryResponse,
)
from app.services.get_options import OptionsDependencyError
from app.services.get_aggregations import (
    AggregationLookupError,
    get_daily_broadband_summary,
    get_daily_summary,
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
) -> DailySummaryResponse:
    try:
        return get_daily_summary(hydrophone, start_date, num_days, band_low, band_high)
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
