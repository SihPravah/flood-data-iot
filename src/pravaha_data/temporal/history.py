from datetime import datetime, timedelta, timezone
from typing import List, Optional
from ..models.observation import CanonicalObservation
from ..models.provenance import DataStatus

class TemporalHistory:
    def __init__(self):
        self.observations: List[CanonicalObservation] = []

    def add_observation(self, obs: CanonicalObservation):
        self.observations.append(obs)
        # Keep only the last 2 hours of data to save memory
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        self.observations = [o for o in self.observations if o.observed_at >= cutoff]

    def get_rain_1h_mm(self) -> tuple[Optional[float], DataStatus]:
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        
        recent_obs = [o for o in self.observations if o.observed_at >= one_hour_ago 
                      and o.source_id == "OPEN_METEO" 
                      and o.measurements.get("rainfall_intensity_mm_per_hr") is not None
                      and o.measurements["rainfall_intensity_mm_per_hr"].status == DataStatus.OBSERVED]

        if not recent_obs:
            return None, DataStatus.MISSING
            
        # In a real system we would integrate intensity over time.
        # For this SIH prototype, if we have enough recent data, we'll return a simple sum 
        # (assuming 1 observation per hour or converting intensity properly).
        # We'll just take the average intensity over the hour as a simplified 1h accumulation.
        avg_intensity = sum(o.measurements["rainfall_intensity_mm_per_hr"].value for o in recent_obs) / len(recent_obs)
        
        return avg_intensity, DataStatus.DERIVED
