from datetime import datetime, timedelta, timezone
from enum import Enum

from pravaha_data.fusion.catchment_fusion import fuse_catchment_state
from pravaha_data.models.fused_state import FusedCatchmentState
from pravaha_data.models.observation import CanonicalObservation
from pravaha_data.models.provenance import DataStatus
from pravaha_data.models.raw_sensor import RawSensorPayload
from pravaha_data.normalization.observations import normalize_raw_sensor
from pravaha_data.temporal.history import TemporalHistory
from pravaha_data.demo.ids import (
    DEMO_CATCHMENT_ID,
    DEMO_SENSOR_PRIMARY_ID,
    DEMO_SCENARIO_ID,
)


class DemoStage(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    WARNING = "WARNING"
    SEVERE = "SEVERE"


DEMO_DEVICE_ID = DEMO_SENSOR_PRIMARY_ID
DEMO_BASE_TIME = datetime(2026, 9, 9, 8, 0, 0, tzinfo=timezone.utc)
DEMO_LOCATION = {
    "village": "Example Village",
    "ward": "Ward 1",
    "lat": 30.3165,
    "lon": 78.0322,
}

_STAGE_PROFILES = {
    DemoStage.NORMAL: {
        "offset_minutes": 0,
        "rainfall": (1.0, 2.0, 2.5, 3.0),
        "soil": (42.0, 43.0, 44.0, 45.0),
    },
    DemoStage.WATCH: {
        "offset_minutes": 30,
        "rainfall": (6.0, 9.0, 12.0, 16.0),
        "soil": (52.0, 55.0, 58.0, 61.0),
    },
    DemoStage.WARNING: {
        "offset_minutes": 60,
        "rainfall": (18.0, 25.0, 34.0, 42.0),
        "soil": (64.0, 68.0, 72.0, 76.0),
    },
    DemoStage.SEVERE: {
        "offset_minutes": 90,
        "rainfall": (35.0, 50.0, 68.0, 82.0),
        "soil": (76.0, 81.0, 86.0, 90.0),
    },
}


def _payload(
    *,
    observed_at: datetime,
    rainfall_mm_per_hr: float,
    soil_moisture_percentage: float,
) -> RawSensorPayload:
    return RawSensorPayload.model_validate(
        {
            "device_id": DEMO_DEVICE_ID,
            "timestamp": observed_at,
            "location": DEMO_LOCATION,
            "sensor_metrics": {
                "rainfall_mm_per_hr": rainfall_mm_per_hr,
                "soil_moisture_percentage": soil_moisture_percentage,
                "slope_tilt_degrees": 2.0,
            },
        }
    )


def build_demo_observations(stage: DemoStage) -> tuple[CanonicalObservation, ...]:
    """
    Return deterministic SIMULATED canonical observations for one demo stage.

    The observations cover the recent temporal windows and intentionally
    increase rainfall and soil wetness as the scenario deteriorates.
    """

    profile = _STAGE_PROFILES[stage]
    state_time = DEMO_BASE_TIME + timedelta(minutes=profile["offset_minutes"])
    rainfall_values = profile["rainfall"]
    soil_values = profile["soil"]

    offsets = (-45, -30, -15, 0)
    observations = []
    for offset, rainfall, soil in zip(offsets, rainfall_values, soil_values):
        payload = _payload(
            observed_at=state_time + timedelta(minutes=offset),
            rainfall_mm_per_hr=rainfall,
            soil_moisture_percentage=soil,
        )
        observations.append(
            normalize_raw_sensor(
                payload,
                measurement_status=DataStatus.SIMULATED,
                received_at=payload.timestamp,
            )
        )

    return tuple(observations)


def build_demo_fused_state(stage: DemoStage) -> FusedCatchmentState:
    observations = build_demo_observations(stage)
    state_time = observations[-1].observed_at
    history = TemporalHistory()

    for observation in observations:
        history.add_observation(observation, as_of=state_time)

    return fuse_catchment_state(
        catchment_id=DEMO_CATCHMENT_ID,
        observations=list(observations),
        history=history,
        state_time=state_time,
    )


def iter_demo_fused_states() -> tuple[FusedCatchmentState, ...]:
    return tuple(
        build_demo_fused_state(stage)
        for stage in (
            DemoStage.NORMAL,
            DemoStage.WATCH,
            DemoStage.WARNING,
            DemoStage.SEVERE,
        )
    )
