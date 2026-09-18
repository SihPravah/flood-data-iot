from collections import defaultdict
from datetime import datetime, timezone

from pravaha_data.adapters.open_meteo import OpenMeteoAdapter
from pravaha_data.demo.scenario import DemoStage, build_demo_fused_state
from pravaha_data.fusion.catchment_fusion import fuse_catchment_state
from pravaha_data.gis.catchments import DemoCatchmentAssigner
from pravaha_data.models.fused_state import FusedCatchmentState
from pravaha_data.models.observation import CanonicalObservation
from pravaha_data.models.provenance import DataStatus
from pravaha_data.models.raw_sensor import RawSensorPayload
from pravaha_data.models.source_health import SourceHealth
from pravaha_data.normalization.observations import normalize_open_meteo, normalize_raw_sensor
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
        self._sources: dict[str, CanonicalObservation] = {}

    def ingest_raw_sensor(
        self,
        payload: RawSensorPayload | dict,
        *,
        measurement_status: DataStatus | None = None,
    ) -> tuple[str, CanonicalObservation]:
        normalized_payload = (
            payload
            if isinstance(payload, RawSensorPayload)
            else RawSensorPayload.model_validate(payload)
        )
        effective_status = measurement_status or normalized_payload.provenance
        if effective_status == DataStatus.SIMULATED and not self.demo_mode:
            raise OperationalModeError(
                "Operational mode cannot silently ingest SIMULATED sensor data."
            )

        observation = normalize_raw_sensor(
            normalized_payload,
            measurement_status=effective_status,
        )
        catchment_id = self._record_observation(observation)
        return catchment_id, observation

    def ingest_open_meteo(
        self,
        *,
        latitude: float,
        longitude: float,
        timeout_seconds: float = 5.0,
        demo_fallback_measurements: dict | None = None,
    ) -> tuple[str, CanonicalObservation]:
        adapter = OpenMeteoAdapter(
            latitude=latitude,
            longitude=longitude,
            timeout_seconds=timeout_seconds,
            demo_mode=self.demo_mode,
            demo_fallback_measurements=demo_fallback_measurements,
        )
        observation = normalize_open_meteo(adapter.fetch())
        statuses = {
            measurement.status
            for measurement in observation.measurements.values()
        }
        if DataStatus.SIMULATED in statuses and not self.demo_mode:
            raise OperationalModeError(
                "Operational mode cannot silently use SIMULATED Open-Meteo fallback."
            )
        catchment_id = self._record_observation(observation)
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

    def _record_observation(
        self,
        observation: CanonicalObservation,
    ) -> str:
        catchment_id = self.assigner.assign(observation.location)
        history = self._histories[catchment_id]
        history.add_observation(observation, as_of=observation.observed_at)
        self._latest[catchment_id].append(observation)
        self._sources[observation.source_id] = observation
        return catchment_id

    def get_source_health(
        self,
        *,
        as_of: datetime | None = None,
        expected_interval_seconds: int = 900,
    ) -> tuple[SourceHealth, ...]:
        if as_of is None:
            as_of = datetime.now(timezone.utc)

        health: list[SourceHealth] = []
        for source_id, observation in sorted(self._sources.items()):
            observed_at = observation.observed_at
            age_seconds = max(0, int((as_of - observed_at).total_seconds()))
            statuses = {
                measurement.status
                for measurement in observation.measurements.values()
            }
            provenance = (
                DataStatus.MISSING
                if statuses == {DataStatus.MISSING}
                else DataStatus.SIMULATED
                if DataStatus.SIMULATED in statuses
                else DataStatus.OBSERVED
            )

            if provenance == DataStatus.SIMULATED:
                status = "SIMULATED"
            elif provenance == DataStatus.MISSING:
                status = "UNAVAILABLE"
            elif age_seconds <= expected_interval_seconds * 2:
                status = "HEALTHY"
            else:
                status = "DEGRADED"

            if status in {"HEALTHY", "SIMULATED"}:
                freshness = "GOOD"
            elif status == "DEGRADED":
                freshness = "DEGRADED"
            else:
                freshness = "UNUSABLE"

            health.append(
                SourceHealth(
                    source_id=source_id,
                    name=source_id,
                    category="IOT_SENSOR",
                    status=status,
                    last_success_at=observation.received_at,
                    last_observation_at=observed_at,
                    age_seconds=age_seconds,
                    expected_interval_seconds=expected_interval_seconds,
                    freshness=freshness,
                    provenance=provenance,
                    message=(
                        "SIMULATED demo source"
                        if status == "SIMULATED"
                        else "Source has recent observations"
                        if status == "HEALTHY"
                        else "Source observations are stale or missing"
                    ),
                )
            )

        return tuple(health)
