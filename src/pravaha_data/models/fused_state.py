from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .provenance import DataStatus, DataQuality

class RainfallFeatures(BaseModel):
    rainfall_intensity_mm_per_hr: Optional[float] = None
    rain_1h_mm: Optional[float] = None
    status: DataStatus
    confidence: Optional[float] = None

class SoilFeatures(BaseModel):
    saturation: Optional[float] = None
    status: DataStatus
    confidence: Optional[float] = None
    age_minutes: Optional[int] = None

class DataQualityState(BaseModel):
    overall_score: float
    missing_sources: List[str]

class FusedCatchmentState(BaseModel):
    catchment_id: str
    state_time: datetime
    rainfall: RainfallFeatures
    soil: SoilFeatures
    data_quality: DataQualityState
