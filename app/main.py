import logging
from pathlib import Path
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.aggregations import router as aggregations_router
from app.api.health import router as health_router
from app.api.options import router as options_router
from app.api.timeseries import router as timeseries_router


app = FastAPI(
    title="Ambient Sound Analysis API",
    version="0.1.0",
    description="Thin FastAPI wrapper around orcasound_noise.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("ambient_sound_api")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "api-timing.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    if request.url.path.startswith("/.well-known/"):
        return response
    duration_ms = (time.perf_counter() - start) * 1000
    query = request.url.query or "-"
    response_size = response.headers.get("content-length", "-")
    point_count = response.headers.get("x-point-count")
    expected_point_count = response.headers.get("x-expected-point-count")
    time_count = response.headers.get("x-time-count")
    frequency_count = response.headers.get("x-frequency-count")
    data_summary = []
    if point_count is not None:
        data_summary.append(f"points={point_count}")
    if expected_point_count is not None:
        data_summary.append(f"expected_points={expected_point_count}")
    if time_count is not None:
        data_summary.append(f"time_count={time_count}")
    if frequency_count is not None:
        data_summary.append(f"frequency_count={frequency_count}")
    data_summary_text = " ".join(data_summary) if data_summary else "-"
    logger.info(
        "%s %s query=%s -> %s in %.1fms size=%s data=%s",
        request.method,
        request.url.path,
        query,
        response.status_code,
        duration_ms,
        response_size,
        data_summary_text,
    )
    return response

app.include_router(health_router)
app.include_router(options_router)
app.include_router(timeseries_router)
app.include_router(aggregations_router)
