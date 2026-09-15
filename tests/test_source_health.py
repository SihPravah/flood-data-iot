from datetime import datetime, timedelta, timezone

from pravaha_data.demo.ids import DEMO_SENSOR_PRIMARY_ID
from pravaha_data.models.provenance import DataStatus
from pravaha_data.normalization.observations import normalize_raw_sensor
from pravaha_data.services.catchment_state import CatchmentStateService


RAW_PAYLOAD = {
    "device_id": DEMO_SENSOR_PRIMARY_ID,
    "timestamp": "2026-09-09T08:45:00Z",
    "location": {
        "village": "Example Village",
        "ward": "Ward 1",
        "lat": 30.3165,
        "lon": 78.0322,
    },
    "sensor_metrics": {
        "rainfall_mm_per_hr": 12.4,
        "soil_moisture_percentage": 67.0,
        "slope_tilt_degrees": 2.1,
    },
}


def test_canonical_observation_preserves_observed_and_received_time():
    observation = normalize_raw_sensor(
        RAW_PAYLOAD,
        received_at=datetime(2026, 9, 9, 8, 45, 5, tzinfo=timezone.utc),
    )

    assert observation.observed_at.isoformat() == "2026-09-09T08:45:00+00:00"
    assert observation.received_at is not None
    assert observation.measurements["rainfall_intensity_mm_per_hr"].unit == "mm/hr"


def test_source_health_keeps_simulated_provenance_separate_from_freshness():
    service = CatchmentStateService(demo_mode=True)
    catchment_id, observation = service.ingest_raw_sensor(
        RAW_PAYLOAD,
        measurement_status=DataStatus.SIMULATED,
    )

    health = service.get_source_health(as_of=observation.observed_at)

    assert catchment_id == "UK-CHM-DEHRADUN-01"
    assert health[0].source_id == DEMO_SENSOR_PRIMARY_ID
    assert health[0].status == "SIMULATED"
    assert health[0].freshness.value == "GOOD"
    assert health[0].provenance == DataStatus.SIMULATED


def test_source_health_degrades_stale_observed_sources():
    service = CatchmentStateService(demo_mode=False)
    _, observation = service.ingest_raw_sensor(RAW_PAYLOAD)

    health = service.get_source_health(
        as_of=observation.observed_at + timedelta(hours=2),
        expected_interval_seconds=900,
    )

    assert health[0].status == "DEGRADED"
    assert health[0].freshness.value == "DEGRADED"
    assert health[0].provenance == DataStatus.OBSERVED
