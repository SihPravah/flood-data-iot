from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .provenance import DataStatus, DataQuality

class IntensityFeatures(BaseModel):
    value: Optional[float] = None
    status: DataStatus
    confidence: Optional[float] = None
    age_minutes: Optional[float] = None

class RainWindowFeatures(BaseModel):
    value_mm: Optional[float] = None
    status: DataStatus
    coverage_fraction: float = 0.0
    largest_gap_minutes: Optional[float] = None
    latest_observation_age_minutes: Optional[float] = None
    observation_count: int = 0
    quality: DataQuality

class RainfallFeatures(BaseModel):
    intensity: IntensityFeatures
    rain_15m: RainWindowFeatures
    rain_30m: RainWindowFeatures
    rain_1h: RainWindowFeatures
    rain_3h: RainWindowFeatures
    rain_6h: RainWindowFeatures
    rain_24h: RainWindowFeatures

class SoilFeatures(BaseModel):
    saturation: Optional[float] = None
    status: DataStatus
    confidence: Optional[float] = None
    age_minutes: Optional[float] = None

class DataQualityState(BaseModel):
    overall_score: float
    missing_sources: List[str]
    temporal_freshness: DataQuality = DataQuality.GOOD

class FusedCatchmentState(BaseModel):
    catchment_id: str
    state_time: datetime
    rainfall: RainfallFeatures
    soil: SoilFeatures
    data_quality: DataQualityState
