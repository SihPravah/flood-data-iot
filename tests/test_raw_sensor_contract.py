from datetime import datetime, timezone

import pytest

from pravaha_data.models.provenance import DataStatus
from pravaha_data.models.raw_sensor import RawSensorPayload
from pravaha_data.normalization.observations import normalize_raw_sensor


def make_payload() -> RawSensorPayload:
    return RawSensorPayload.model_validate(
        {
            "device_id": "SIM_NODE_04",
            "timestamp": "2026-09-09T17:30:00Z",
            "location": {
                "village": "Example Village",
                "ward": "Ward 1",
                "lat": 30.1234,
                "lon": 78.4567,
            },
            "sensor_metrics": {
                "rainfall_mm_per_hr": 12.4,
                "soil_moisture_percentage": 67.0,
                "slope_tilt_degrees": 2.1,
            },
        }
    )


def test_raw_lat_lon_normalizes_to_canonical_latitude_longitude():
    observation = normalize_raw_sensor(make_payload())

    assert observation.location.latitude == 30.1234
    assert observation.location.longitude == 78.4567
    assert observation.observed_at == datetime(2026, 9, 9, 17, 30, tzinfo=timezone.utc)


def test_raw_sensor_provenance_is_preserved_as_simulated():
    observation = normalize_raw_sensor(
        make_payload(),
        measurement_status=DataStatus.SIMULATED,
    )

    assert (
        observation.measurements["rainfall_intensity_mm_per_hr"].status
        == DataStatus.SIMULATED
    )
    assert observation.measurements["soil_moisture_percentage"].status == DataStatus.SIMULATED


def test_raw_sensor_rejects_invalid_latitude():
    payload = make_payload().model_dump()
    payload["location"]["lat"] = 120.0

    with pytest.raises(ValueError):
        RawSensorPayload.model_validate(payload)
