import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from pravaha_data.demo.scenario import DemoStage
from pravaha_data.gis.catchments import DemoCatchmentAssigner
from pravaha_data.models.provenance import DataStatus
from pravaha_data.models.raw_sensor import RawSensorPayload
from pravaha_data.services.catchment_state import (
    CatchmentStateService,
    OperationalModeError,
)


class OpenMeteoIngestRequest(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    timeout_seconds: float = Field(default=5.0, gt=0.0)


def create_app(
    *,
    demo_mode: bool | None = None,
) -> FastAPI:
    if demo_mode is None:
        demo_mode = _env_bool("PRAVAHA_DATA_DEMO_MODE", default=False)

    service = CatchmentStateService(
        assigner=DemoCatchmentAssigner.dehradun_demo(),
        demo_mode=demo_mode,
    )
    app = FastAPI(
        title="PRAVAHA Data/IoT",
        version="0.1.0",
        description="Observation ingestion, source health, temporal history, and FusedCatchmentState v2.1.",
    )

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        return {
            "status": "healthy",
            "service": "pravaha-data-iot",
            "demo_mode": demo_mode,
        }

    @app.post(
        "/api/v1/ingest/sensors",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def ingest_sensor(payload: RawSensorPayload) -> dict[str, Any]:
        received_at = payload.received_at or datetime.now(timezone.utc)
        payload = payload.model_copy(update={"received_at": received_at})
        try:
            catchment_id, observation = service.ingest_raw_sensor(payload)
            fused_state = service.get_fused_catchment_state(
                catchment_id,
                as_of=observation.observed_at,
            )
        except OperationalModeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "status": "accepted",
            "device_id": payload.device_id,
            "catchment_id": catchment_id,
            "observed_at": observation.observed_at,
            "received_at": received_at,
            "provenance": payload.provenance,
            "canonical_location": observation.location.model_dump(),
            "fused_state": fused_state.model_dump(mode="json"),
        }

    @app.post(
        "/api/v1/live/open-meteo",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def ingest_open_meteo(request: OpenMeteoIngestRequest) -> dict[str, Any]:
        try:
            catchment_id, observation = service.ingest_open_meteo(
                latitude=request.latitude,
                longitude=request.longitude,
                timeout_seconds=request.timeout_seconds,
            )
            fused_state = service.get_fused_catchment_state(
                catchment_id,
                as_of=observation.observed_at,
            )
        except OperationalModeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "status": "accepted",
            "source_id": observation.source_id,
            "catchment_id": catchment_id,
            "observed_at": observation.observed_at,
            "received_at": observation.received_at,
            "canonical_location": observation.location.model_dump(),
            "fused_state": fused_state.model_dump(mode="json"),
        }

    @app.get("/api/v1/catchments/{catchment_id}/state")
    def catchment_state(
        catchment_id: str,
        demo_stage: DemoStage | None = Query(default=None),
    ) -> dict[str, Any]:
        if demo_stage is not None:
            try:
                state = service.get_demo_fused_catchment_state(demo_stage)
            except OperationalModeError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            state = service.get_fused_catchment_state(catchment_id)

        return state.model_dump(mode="json")

    @app.get("/api/v1/system/source-health")
    def source_health() -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in service.get_source_health()
        ]

    return app


def _env_bool(
    name: str,
    *,
    default: bool,
) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


app = create_app()
