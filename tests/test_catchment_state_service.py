import pytest

from pravaha_data.demo.scenario import DemoStage
from pravaha_data.demo.ids import DEMO_SENSOR_PRIMARY_ID
from pravaha_data.models.provenance import DataStatus
from pravaha_data.services.catchment_state import CatchmentStateService, OperationalModeError


RAW_PAYLOAD = {
    "device_id": DEMO_SENSOR_PRIMARY_ID,
    "timestamp": "2026-09-09T17:30:00Z",
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


def test_catchment_state_service_returns_fused_state_for_assigned_catchment():
    service = CatchmentStateService(demo_mode=False)

    catchment_id, observation = service.ingest_raw_sensor(RAW_PAYLOAD)
    state = service.get_fused_catchment_state(
        catchment_id,
        as_of=observation.observed_at,
    )

    assert catchment_id == "UK-CHM-DEHRADUN-01"
    assert state.catchment_id == catchment_id
    assert state.rainfall.intensity.value == 12.4
    assert state.soil.saturation == 0.67


def test_operational_mode_rejects_silent_simulated_substitution():
    service = CatchmentStateService(demo_mode=False)

    with pytest.raises(OperationalModeError):
        service.ingest_raw_sensor(
            RAW_PAYLOAD,
            measurement_status=DataStatus.SIMULATED,
        )


def test_demo_mode_can_return_deterministic_demo_fused_state():
    service = CatchmentStateService(demo_mode=True)

    first = service.get_demo_fused_catchment_state(DemoStage.WARNING)
    second = service.get_demo_fused_catchment_state(DemoStage.WARNING)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.rainfall.intensity.status == DataStatus.SIMULATED
