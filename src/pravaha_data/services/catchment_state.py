from collections import defaultdict
from datetime import datetime

from pravaha_data.demo.scenario import DemoStage, build_demo_fused_state
from pravaha_data.fusion.catchment_fusion import fuse_catchment_state
from pravaha_data.gis.catchments import DemoCatchmentAssigner
from pravaha_data.models.fused_state import FusedCatchmentState
from pravaha_data.models.observation import CanonicalObservation
from pravaha_data.models.provenance import DataStatus
from pravaha_data.models.raw_sensor import RawSensorPayload
from pravaha_data.normalization.observations import normalize_raw_sensor
from pravaha_data.temporal.history import TemporalHistory


class OperationalModeError(RuntimeError):
    pass


class CatchmentStateService:
    """
    In-memory service boundary for retrieving live/demo FusedCatchmentState.

    This keeps Data/IoT responsible for observations and fusion only. It
    deliberately does not calculate flood risk.
    """

    def __init__(
        self,
        *,
        assigner: DemoCatchmentAssigner | None = None,
        demo_mode: bool = False,
    ):
        self.assigner = assigner or DemoCatchmentAssigner.dehradun_demo()
        self.demo_mode = demo_mode
        self._histories: dict[str, TemporalHistory] = defaultdict(TemporalHistory)
        self._latest: dict[str, list[CanonicalObservation]] = defaultdict(list)

    def ingest_raw_sensor(
        self,
        payload: RawSensorPayload | dict,
        *,
        measurement_status: DataStatus = DataStatus.OBSERVED,
    ) -> tuple[str, CanonicalObservation]:
        if measurement_status == DataStatus.SIMULATED and not self.demo_mode:
            raise OperationalModeError(
                "Operational mode cannot silently ingest SIMULATED sensor data."
            )

        observation = normalize_raw_sensor(
            payload,
            measurement_status=measurement_status,
        )
        catchment_id = self.assigner.assign(observation.location)
        history = self._histories[catchment_id]
        history.add_observation(observation, as_of=observation.observed_at)
        self._latest[catchment_id].append(observation)
        return catchment_id, observation

    def get_fused_catchment_state(
        self,
        catchment_id: str,
        *,
        as_of: datetime | None = None,
    ) -> FusedCatchmentState:
        observations = self._latest.get(catchment_id, [])
        history = self._histories[catchment_id]
        return fuse_catchment_state(
            catchment_id=catchment_id,
            observations=list(observations),
            history=history,
            state_time=as_of,
        )

    def get_demo_fused_catchment_state(
        self,
        stage: DemoStage,
    ) -> FusedCatchmentState:
        if not self.demo_mode:
            raise OperationalModeError(
                "Demo FusedCatchmentState is only available when demo_mode is enabled."
            )
        return build_demo_fused_state(stage)
