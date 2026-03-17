from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Response

from app.models.responses import BroadbandTimeseriesResponse, PSDTimeseriesResponse
from app.services.get_options import OptionsDependencyError
from app.services.get_timeseries import (
    TimeseriesLookupError,
    get_broadband_timeseries,
    get_psd_timeseries,
)


router = APIRouter(prefix="/timeseries", tags=["timeseries"])


@router.get("/broadband", response_model=BroadbandTimeseriesResponse)
def get_broadband(
    response: Response,
    hydrophone: str = Query(..., description="Hydrophone slug, e.g. bush_point."),
    start: datetime = Query(..., description="Inclusive start datetime in ISO 8601."),
    end: datetime = Query(..., description="Exclusive end datetime in ISO 8601."),
    delta_t: int = Query(1, description="Seconds per sample."),
    validate: bool = Query(
        True, description="Whether to validate the requested combination and time window first."
    ),
) -> BroadbandTimeseriesResponse:
    try:
        payload = get_broadband_timeseries(hydrophone, start, end, delta_t, validate)
        response.headers["X-Point-Count"] = str(payload.point_count)
        response.headers["X-Expected-Point-Count"] = str(payload.expected_point_count)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OptionsDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TimeseriesLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/psd", response_model=PSDTimeseriesResponse)
def get_psd(
    response: Response,
    hydrophone: str = Query(..., description="Hydrophone slug, e.g. bush_point."),
    start: datetime = Query(..., description="Inclusive start datetime in ISO 8601."),
    end: datetime = Query(..., description="Exclusive end datetime in ISO 8601."),
    delta_t: int = Query(1, description="Seconds per sample."),
    delta_f: str = Query(..., description='Frequency option, e.g. "3oct" or "50hz".'),
    validate: bool = Query(
        True, description="Whether to validate the requested combination and time window first."
    ),
) -> PSDTimeseriesResponse:
    try:
        payload = get_psd_timeseries(hydrophone, start, end, delta_t, delta_f, validate)
        response.headers["X-Point-Count"] = str(payload.point_count)
        response.headers["X-Expected-Point-Count"] = str(payload.expected_point_count)
        response.headers["X-Frequency-Count"] = str(len(payload.columns))
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OptionsDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TimeseriesLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
