from datetime import datetime, timezone
from typing import List
from ..models.observation import CanonicalObservation
from ..models.fused_state import FusedCatchmentState, RainfallFeatures, SoilFeatures, DataQualityState
from ..models.provenance import DataStatus
from ..temporal.history import TemporalHistory

def fuse_catchment_state(
    catchment_id: str, 
    observations: List[CanonicalObservation], 
    history: TemporalHistory
) -> FusedCatchmentState:
    
    # 1. Initialize empty features
    rainfall_intensity = None
    rain_status = DataStatus.MISSING
    soil_saturation = None
    soil_status = DataStatus.MISSING
    
    # 2. Extract most recent valid observations
    for obs in observations:
        if "rainfall_intensity_mm_per_hr" in obs.measurements:
            m = obs.measurements["rainfall_intensity_mm_per_hr"]
            if m.status in [DataStatus.OBSERVED, DataStatus.DERIVED]:
                rainfall_intensity = m.value
                rain_status = m.status
                
        if "soil_moisture_percentage" in obs.measurements:
            m = obs.measurements["soil_moisture_percentage"]
            if m.status in [DataStatus.OBSERVED, DataStatus.SIMULATED]:
                # Normalize IoT percentage (0-100) to saturation (0-1)
                soil_saturation = m.value / 100.0 if m.value is not None else None
                soil_status = m.status
                
        elif "soil_moisture_volumetric" in obs.measurements and soil_saturation is None:
            # Fallback to OpenMeteo derived value if IoT is missing
            m = obs.measurements["soil_moisture_volumetric"]
            if m.status == DataStatus.DERIVED:
                soil_saturation = min(m.value / 0.5, 1.0) if m.value is not None else None
                soil_status = DataStatus.DERIVED
                
    # 3. Calculate temporal features (1-hour accumulated rain)
    rain_1h, rain_1h_status = history.get_rain_1h_mm()
    
    # 4. Construct Data Quality State
    missing = []
    if rain_status == DataStatus.MISSING: missing.append("rainfall")
    if soil_status == DataStatus.MISSING: missing.append("soil_moisture")
    
    score = 1.0 - (0.5 * len(missing))
    
    # 5. Build final Fused State
    return FusedCatchmentState(
        catchment_id=catchment_id,
        state_time=datetime.now(timezone.utc),
        rainfall=RainfallFeatures(
            rainfall_intensity_mm_per_hr=rainfall_intensity,
            rain_1h_mm=rain_1h,
            status=rain_status,
            confidence=0.9 if rain_status != DataStatus.MISSING else 0.0
        ),
        soil=SoilFeatures(
            saturation=soil_saturation,
            status=soil_status,
            confidence=0.85 if soil_status != DataStatus.MISSING else 0.0,
            age_minutes=0  # Simplified for MVP
        ),
        data_quality=DataQualityState(
            overall_score=score,
            missing_sources=missing
        )
    )
