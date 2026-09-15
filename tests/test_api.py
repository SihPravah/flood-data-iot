from fastapi.testclient import TestClient

from pravaha_data.api import create_app


RAW_PAYLOAD = {
    "device_id": "UK-SNS-00127",
    "observed_at": "2026-09-09T08:30:00Z",
    "received_at": "2026-09-09T08:30:04Z",
    "location": {
        "village": "Chandrabani",
        "ward": "Ward 7",
        "lat": 30.329,
        "lon": 78.039,
    },
    "sensor_metrics": {
        "rainfall_mm_per_hr": 48.0,
        "soil_moisture_percentage": 82.0,
        "slope_tilt_degrees": 2.2,
    },
}


def test_sensor_post_enters_fusion_path():
    client = TestClient(create_app(demo_mode=False))

    response = client.post(
        "/api/v1/ingest/sensors",
        json=RAW_PAYLOAD,
    )

    assert response.status_code == 202
    body = response.json()

    assert body["status"] == "accepted"
    assert body["device_id"] == "UK-SNS-00127"
    assert body["catchment_id"] == "UK-CHM-DEHRADUN-01"
    assert body["canonical_location"] == {
        "latitude": 30.329,
        "longitude": 78.039,
    }
    assert body["fused_state"]["catchment_id"] == "UK-CHM-DEHRADUN-01"
    assert body["fused_state"]["rainfall"]["intensity"]["value"] == 48.0
    assert body["fused_state"]["rainfall"]["intensity"]["status"] == "OBSERVED"
    assert body["fused_state"]["soil"]["saturation"] == 0.82


def test_operational_api_rejects_simulated_sensor_payload():
    client = TestClient(create_app(demo_mode=False))
    payload = {
        **RAW_PAYLOAD,
        "provenance": "SIMULATED",
    }

    response = client.post(
        "/api/v1/ingest/sensors",
        json=payload,
    )

    assert response.status_code == 400
    assert "SIMULATED" in response.json()["detail"]


def test_demo_catchment_state_uses_deterministic_fixtures():
    client = TestClient(create_app(demo_mode=True))

    response = client.get(
        "/api/v1/catchments/UK-CHM-DEHRADUN-01/state?demo_stage=WARNING"
    )

    assert response.status_code == 200
    body = response.json()

    assert body["catchment_id"] == "UK-CHM-DEHRADUN-01"
    assert body["rainfall"]["intensity"]["status"] == "SIMULATED"
    assert body["rainfall"]["rain_1h"]["quality"] == "DEGRADED"


def test_source_health_reflects_ingested_sensor():
    client = TestClient(create_app(demo_mode=False))
    client.post(
        "/api/v1/ingest/sensors",
        json=RAW_PAYLOAD,
    )

    response = client.get("/api/v1/system/source-health")

    assert response.status_code == 200
    body = response.json()

    assert body[0]["source_id"] == "UK-SNS-00127"
    assert body[0]["provenance"] == "OBSERVED"
