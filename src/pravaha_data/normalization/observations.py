from datetime import datetime, timezone
import uuid
from typing import Dict, Any

from ..models.observation import CanonicalObservation, Location, Measurement
from ..models.provenance import DataStatus
from ..models.raw_sensor import RawSensorPayload

def normalize_open_meteo(raw_data: Dict[str, Any]) -> CanonicalObservation:
    measurements = {}
    measurement_status = DataStatus(raw_data.get("measurement_status", DataStatus.OBSERVED))
    
    if raw_data["raw_measurements"] is None:
        measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=None, status=DataStatus.MISSING, unit="mm/hr")
        measurements["soil_moisture_volumetric"] = Measurement(value=None, status=DataStatus.MISSING, unit="m3/m3")
    else:
        # Extract intensity
        precip = raw_data["raw_measurements"].get("precipitation")
        if precip is not None:
            measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=float(precip), status=measurement_status, unit="mm/hr")
        else:
            measurements["rainfall_intensity_mm_per_hr"] = Measurement(value=None, status=DataStatus.MISSING, unit="mm/hr")
            
        # Extract soil moisture
        soil = raw_data["raw_measurements"].get("soil_moisture_0_to_7cm")
        if soil is not None:
            # We explicitly label this as derived since OpenMeteo returns volumetric water content, not saturation
            soil_status = DataStatus.SIMULATED if measurement_status == DataStatus.SIMULATED else DataStatus.DERIVED
            measurements["soil_moisture_volumetric"] = Measurement(value=float(soil), status=soil_status, unit="m3/m3")
        else:
            measurements["soil_moisture_volumetric"] = Measurement(value=None, status=DataStatus.MISSING, unit="m3/m3")

    return CanonicalObservation(
        observation_id=str(uuid.uuid4()),
        source_id=raw_data["source_id"],
        source_type=raw_data["source_type"],
        observed_at=raw_data["observed_at"],
        received_at=raw_data.get("received_at", raw_data["observed_at"]),
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
        status=DataStatus.SIMULATED if soil is not None else DataStatus.MISSING,
        unit="percent",
    )
    
    measurements["slope_tilt_degrees"] = Measurement(
        value=float(tilt) if tilt is not None else None,
        status=DataStatus.SIMULATED if tilt is not None else DataStatus.MISSING,
        unit="degrees",
    )
    
    return CanonicalObservation(
        observation_id=str(uuid.uuid4()),
        source_id=raw_data["source_id"],
        source_type=raw_data["source_type"],
        observed_at=raw_data["observed_at"],
        received_at=raw_data.get("received_at", raw_data["observed_at"]),
        location=Location(
            latitude=raw_data["location"]["lat"],
            longitude=raw_data["location"]["lon"]
        ),
        measurements=measurements
    )


def normalize_raw_sensor(
    payload: RawSensorPayload | Dict[str, Any],
    *,
    measurement_status: DataStatus | None = None,
    received_at: datetime | None = None,
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
    if received_at is None:
        received_at = payload.received_at or datetime.now(timezone.utc)

    status = measurement_status or payload.provenance

    measurements = {
        "rainfall_intensity_mm_per_hr": Measurement(
            value=float(metrics.rainfall_mm_per_hr),
            status=status,
            unit="mm/hr",
        ),
        "soil_moisture_percentage": Measurement(
            value=float(metrics.soil_moisture_percentage),
            status=status,
            unit="percent",
        ),
        "slope_tilt_degrees": Measurement(
            value=float(metrics.slope_tilt_degrees),
            status=status,
            unit="degrees",
        ),
    }

    return CanonicalObservation(
        observation_id=str(uuid.uuid4()),
        source_id=payload.device_id,
        source_type="IOT_SENSOR",
        observed_at=payload.timestamp,
        received_at=received_at,
        location=Location(
            latitude=payload.location.lat,
            longitude=payload.location.lon,
        ),
        measurements=measurements,
    )
