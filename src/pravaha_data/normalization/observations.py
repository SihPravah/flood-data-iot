from datetime import datetime
import uuid
from typing import Dict, Any

from ..models.observation import CanonicalObservation, Location, Measurement
from ..models.provenance import DataStatus
from ..models.raw_sensor import RawSensorPayload

def normalize_open_meteo(raw_data: Dict[str, Any]) -> CanonicalObservation:
    measurements = {}
    measurement_status = DataStatus(raw_data.get("measurement_status", DataStatus.OBSERVED))
    
    if raw_data["raw_measurements"] is None:
        measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=None, status=DataStatus.MISSING)
        measurements["soil_moisture_volumetric"] = Measurement(value=None, status=DataStatus.MISSING)
    else:
        # Extract intensity
        precip = raw_data["raw_measurements"].get("precipitation")
        if precip is not None:
            measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=float(precip), status=measurement_status)
        else:
            measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=None, status=DataStatus.MISSING)
            
        # Extract soil moisture
        soil = raw_data["raw_measurements"].get("soil_moisture_0_to_7cm")
        if soil is not None:
            # We explicitly label this as derived since OpenMeteo returns volumetric water content, not saturation
            soil_status = DataStatus.SIMULATED if measurement_status == DataStatus.SIMULATED else DataStatus.DERIVED
            measurements["soil_moisture_volumetric"] = Measurement(value=float(soil), status=soil_status)
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


def normalize_raw_sensor(
    payload: RawSensorPayload | Dict[str, Any],
    *,
    measurement_status: DataStatus = DataStatus.OBSERVED,
) -> CanonicalObservation:
    """
    Normalize the public raw sensor payload into Data/IoT's internal
    CanonicalObservation shape.

    Public contract coordinates remain location.lat/location.lon. The
    canonical observation uses location.latitude/location.longitude.
    """

    if not isinstance(payload, RawSensorPayload):
        payload = RawSensorPayload.model_validate(payload)

    metrics = payload.sensor_metrics

    measurements = {
        "rainfall_intensity_mm_per_hr": Measurement(
            value=float(metrics.rainfall_mm_per_hr),
            status=measurement_status,
        ),
        "soil_moisture_percentage": Measurement(
            value=float(metrics.soil_moisture_percentage),
            status=measurement_status,
        ),
        "slope_tilt_degrees": Measurement(
            value=float(metrics.slope_tilt_degrees),
            status=measurement_status,
        ),
    }

    return CanonicalObservation(
        observation_id=str(uuid.uuid4()),
        source_id=payload.device_id,
        source_type="IOT_SENSOR",
        observed_at=payload.timestamp,
        location=Location(
            latitude=payload.location.lat,
            longitude=payload.location.lon,
        ),
        measurements=measurements,
    )
