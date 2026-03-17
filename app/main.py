from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.options import router as options_router
from app.api.timeseries import router as timeseries_router


app = FastAPI(
    title="Ambient Sound Analysis API",
    version="0.1.0",
    description="Thin FastAPI wrapper around orcasound_noise.",
)

app.include_router(health_router)
app.include_router(options_router)
app.include_router(timeseries_router)
