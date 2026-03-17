from typing import List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class OptionsResponse(BaseModel):
    hydrophones: List["HydrophoneOptions"]


class TimeResolutionOptions(BaseModel):
    delta_t: int
    first_start: Optional[str]
    last_end: Optional[str]
    file_count: int


class FrequencyBandOptions(TimeResolutionOptions):
    delta_f: int


class HydrophoneOptions(BaseModel):
    hydrophone: str
    broadband: List[TimeResolutionOptions]
    octave_bands: List[FrequencyBandOptions]
    delta_hz: List[FrequencyBandOptions]


class TimeseriesPoint(BaseModel):
    timestamp: str
    value: float


class BroadbandTimeseriesResponse(BaseModel):
    hydrophone: str
    delta_t: int
    start: str
    end: str
    points: List[TimeseriesPoint]


class PSDTimeseriesPoint(BaseModel):
    timestamp: str
    values: List[float]


class PSDTimeseriesResponse(BaseModel):
    hydrophone: str
    delta_t: int
    delta_f: str
    start: str
    end: str
    columns: List[str]
    points: List[PSDTimeseriesPoint]
