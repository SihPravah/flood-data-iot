from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from .provenance import DataStatus, DataQuality

class Location(BaseModel):
    latitude: float
    longitude: float

class Measurement(BaseModel):
    value: Optional[float]
    status: DataStatus
    
class CanonicalObservation(BaseModel):
    observation_id: str
    source_id: str
    source_type: str
    observed_at: datetime
    location: Location
    measurements: Dict[str, Measurement]
