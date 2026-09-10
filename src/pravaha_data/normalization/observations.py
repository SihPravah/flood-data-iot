from datetime import datetime
import uuid
from typing import Dict, Any

from ..models.observation import CanonicalObservation, Location, Measurement
from ..models.provenance import DataStatus

def normalize_open_meteo(raw_data: Dict[str, Any]) -> CanonicalObservation:
    measurements = {}
    
    if raw_data["raw_measurements"] is None:
        measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=None, status=DataStatus.MISSING)
        measurements["soil_moisture_volumetric"] = Measurement(value=None, status=DataStatus.MISSING)
    else:
        # Extract intensity
        precip = raw_data["raw_measurements"].get("precipitation")
        if precip is not None:
            measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=float(precip), status=DataStatus.OBSERVED)
        else:
            measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=None, status=DataStatus.MISSING)
            
        # Extract soil moisture
        soil = raw_data["raw_measurements"].get("soil_moisture_0_to_7cm")
        if soil is not None:
            # We explicitly label this as derived since OpenMeteo returns volumetric water content, not saturation
            measurements["soil_moisture_volumetric"] = Measurement(value=float(soil), status=DataStatus.DERIVED)
        else:
            measurements["soil_moisture_volumetric"] = Measurement(value=None, status=DataStatus.MISSING)

    return CanonicalObservation(
        observation_id=str(uuid.uuid4()),
        source_id=raw_data["source_id"],
        source_type=raw_data["source_type"],
        observed_at=raw_data["observed_at"],
        location=Location(
            latitude=raw_data["location"]["lat"],
            longitude=raw_data["location"]["lon"]
        ),
        measurements=measurements
    )

def normalize_simulated_iot(raw_data: Dict[str, Any]) -> CanonicalObservation:
    measurements = {}
    
    soil = raw_data["raw_measurements"].get("soil_moisture_percentage")
    tilt = raw_data["raw_measurements"].get("slope_tilt_degrees")
    
    measurements["soil_moisture_percentage"] = Measurement(
        value=float(soil) if soil is not None else None,
        status=DataStatus.SIMULATED if soil is not None else DataStatus.MISSING
    )
    
    measurements["slope_tilt_degrees"] = Measurement(
        value=float(tilt) if tilt is not None else None,
        status=DataStatus.SIMULATED if tilt is not None else DataStatus.MISSING
    )
    
    return CanonicalObservation(
        observation_id=str(uuid.uuid4()),
        source_id=raw_data["source_id"],
        source_type=raw_data["source_type"],
        observed_at=raw_data["observed_at"],
        location=Location(
            latitude=raw_data["location"]["lat"],
            longitude=raw_data["location"]["lon"]
        ),
        measurements=measurements
    )
