# PRAVAHA Canonical Data Contracts (v2 - Constitution Compliant)

This document is the absolute source of truth across all 4 repositories (`flood-data-iot`, `flood-ml`, `flood-backend`, `flood-frontend`). Local Pydantic/TypeScript schemas MUST mirror this exactly.

## 1. Raw Sensor Ingestion (IoT -> Data Fusion Engine)
*Ref: PRAVAHA Rule 9*
This is what a single sensor payload looks like before normalization.

**Endpoint:** `POST /api/v1/ingest/observation`
```json
{
  "source_id": "UK-SNS-00127",
  "variable": "soil_moisture",
  "observed_at": "2026-08-30T14:30:00Z",
  "received_at": "2026-08-30T14:30:02Z",
  "value": 0.82,
  "unit": "normalized",
  "quality": "GOOD",
  "status": "OBSERVED",
  "age_seconds": 2,
  "location": {
    "catchment_id": "UK-CHM-00042",
    "latitude": 30.5505,
    "longitude": 79.5659
  }
}

## 2. Fused Catchment State (Data Fusion -> ML / Backend)
*Ref: PRAVAHA Rule 20*
The Data engine aggregates all sensors and external APIs into this single state for a specific catchment. This is what Anushree's ML model consumes.

**Endpoint:** `GET /api/v1/catchments/{catchment_id}/state`
```json
{
  "catchment_id": "UK-CHM-00042",
  "state_time": "2026-08-30T14:35:00Z",
  "rainfall": {
    "rain_1h_mm": 45.5,
    "status": "OBSERVED",
    "confidence": 0.95
  },
  "soil": {
    "saturation": 0.82,
    "status": "OBSERVED",
    "confidence": 0.90,
    "age_minutes": 5
  },
  "data_quality": {
    "overall_score": 0.92,
    "missing_sources": []
  }
}

## 3. ML Prediction Output (ML -> Backend -> Frontend)
Ref: PRAVAHA Rule 21
When Anushree's ML model evaluates the Fused State, it returns this exact structure. Paaji will use this for Disaster
Intelligence, and Banduni/Areca will render this on the Frontend map.

**Endpoint:** `POST /m1/v1/predict`
```json
{
  "prediction_id": "PRD-20260830-000123",
  "catchment_id": "UK-CHM-00042",
  "timestamp": "2026-08-30T14:36:00Z",
  "risk_score": 0.87,
  "risk_level": "SEVERE",
  "lead_time_minutes": 72,
  "hydrology": {
    "rainfall_1h_mm": 45.5,
    "soil_saturation": 0.82
  },
  "confidence": 0.81,
  "data_quality_score": 0.92,
  "top_factors": [
    {
      "factor": "rainfall_1h_mm",
      "importance": 0.45
    },
    {
      "factor": "soil_saturation",
      "importance": 0.32
    }
  ],
  "model_version": "risk-xgb-v1"
}

## 4. Map Intelligence Snapshot (Backend -> Frontend)
*Ref: PRAVAHA Map Intelligence Contract v0.1*
Returns a coherent, timestamped snapshot of the entire city's risk state.

**Endpoint:** `GET /api/v1/map/intelligence`
```json
{
  "snapshot_id": "snap_20260904_224500",
  "generated_at": "2026-09-04T22:45:00Z",
  "model_version": "pravaha-city-v0.1",
  "city": {
    "city_id": "DEHRADUN",
    "name": "Dehradun"
  },
  "operational_status": "ELEVATED",
  "summary": {
    "catchment_count": 48,
    "high_risk_catchments": 4,
    "roads_to_avoid": 19,
    "confirmed_road_closures": 2,
    "low_confidence_catchments": 3
  }
}


## 5. Map Object Detail (Backend -> Frontend)
*Ref: PRAVAHA Map Intelligence Contract v0.1*
Clicking a specific entity on the frontend map triggers a fetch for detailed intelligence. All geometries MUST use GeoJSON `[longitude, latitude]` ordering.

**Endpoint (Catchment Example):** `GET /api/v1/map/catchments/{catchment_id}`
```json
{
  "catchment_id": "C_018",
  "snapshot_id": "snap_20260904_224500",
  "risk": {
    "score": 0.81,
    "level": "HIGH"
  },
  "confidence": {
    "score": 0.88,
    "level": "HIGH",
    "disposition": "NORMAL"
  },
  "impact": {
    "affected_population": 4820,
    "roads_at_risk": 7,
    "critical_drains": 3
  },
  "reasons": [
    "intense_recent_rainfall",
    "wet_soil_condition",
    "high_runoff"
  ],
  "last_updated": "2026-09-04T22:44:45Z"
}

## 6. Safe route Request (frontend -> backend)
Ref: PRAVAHA Map Intelligence Contract v0.1
PRAVAHA must NEVER invent a safe route. If all routes cross severe flood-risk segments or authority-closed zones, the backend must return "status": "NO_SAFE_ROUTE".
Endpoint: POST /api/v1/routes/safe

{
  "origin": { "latitude": 30.3165, "longitude": 78.0322 },
  "destination": { "latitude": 30.3250, "longitude": 78.0410 },
  "routing_mode": "SAFEST"
}
