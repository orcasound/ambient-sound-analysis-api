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
    expected_point_count: int
    point_count: int
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
    expected_point_count: int
    point_count: int
    columns: List[str]
    points: List[PSDTimeseriesPoint]


class DailySummaryPoint(BaseModel):
    time_of_day: str
    value: float


class DailySummaryResponse(BaseModel):
    hydrophone: str
    start_date: str
    num_days: int
    band_low: int
    band_high: int
    description: str
    mean_length: int
    min_length: int
    max_length: int
    count_length: int
    mean: List[DailySummaryPoint]
    min: List[DailySummaryPoint]
    max: List[DailySummaryPoint]
    count: List[DailySummaryPoint]


class DailyBroadbandPoint(BaseModel):
    date: str
    value: float


class DailyBroadbandSummaryResponse(BaseModel):
    hydrophone: str
    start_date: str
    num_days: int
    summary_purpose: str
    point_count: int
    points: List[DailyBroadbandPoint]


class BroadbandAggregationPoint(BaseModel):
    timestamp: str
    value: float


class BroadbandAggregationResponse(BaseModel):
    hydrophone: str
    start: str
    end: str
    interval: str
    summary_purpose: str
    point_count: int
    points: List[BroadbandAggregationPoint]


class PSDHeatmapResponse(BaseModel):
    hydrophone: str
    start: str
    end: str
    delta_t: int
    delta_f: str
    interval: str
    summary_purpose: str
    time_count: int
    frequency_count: int
    times: List[str]
    frequencies: List[str]
    values: List[List[float]]
