from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from pravaha_data.models.provenance import DataStatus, DataQuality


SourceCategory = Literal["IOT_SENSOR", "WEATHER_API", "STATIC_GIS", "DEMO_FIXTURE"]
SourceHealthStatus = Literal[
    "HEALTHY",
    "DEGRADED",
    "UNAVAILABLE",
    "STATIC",
    "SIMULATED",
]


class SourceHealth(BaseModel):
    source_id: str
    name: str
    category: SourceCategory
    status: SourceHealthStatus
    last_success_at: datetime | None = None
    last_observation_at: datetime | None = None
    age_seconds: int | None = Field(default=None, ge=0)
    expected_interval_seconds: int | None = Field(default=None, ge=0)
    freshness: DataQuality
    provenance: DataStatus
    message: str
