# PRAVAHA Canonical Data Contracts (v2 - Constitution Compliant)

This document is the absolute source of truth across all 4 repositories (`flood-data-iot`, `flood-ml`, `flood-backend`, `flood-frontend`).

## 1. Raw Sensor Ingestion (IoT -> Data Fusion Engine)
*Ref: PRAVAHA Rule 9*
This is what a single sensor payload looks like before normalization.
**Endpoint:** `POST /api/v1/ingest/sensors`

```json
{
  "device_id": "sensor-001",
  "timestamp": "2026-09-09T17:30:00Z",
  "location": {
    "lat": 30.1234,
    "lon": 78.4567
  },
  "sensor_metrics": {
    "rainfall_mm_per_hr": 12.4,
    "soil_moisture_percentage": 67.0,
    "slope_tilt_degrees": 2.1
  }
}
```

## 2. Canonical Normalized Observation (Internal Data/IoT)
*Ref: PRAVAHA Rule 6 & 8*
The Data engine converts raw payloads and external APIs into this strict canonical format.

```json
{
  "observation_id": "obs_123",
  "source_id": "sensor-001",
  "source_type": "IOT_SENSOR",
  "observed_at": "2026-09-09T17:30:00Z",
  "location": {
    "latitude": 30.123,
    "longitude": 78.456
  },
  "measurements": {
    "rainfall_intensity_mm_per_hr": {
      "value": 12.4,
      "status": "OBSERVED"
    },
    "soil_moisture_percentage": {
      "value": 67.0,
      "status": "SIMULATED"
    }
  }
}
```

## 3. Fused Catchment State (Data Fusion -> ML / Backend)
*Ref: PRAVAHA Rule 20*
The Data engine aggregates all sensors and temporal history into this single state for a specific catchment.

**Endpoint:** `GET /api/v1/catchments/{catchment_id}/state`

```json
{
  "catchment_id": "UK-CHM-00042",
  "state_time": "2026-08-30T14:35:00Z",
  "rainfall": {
    "rainfall_intensity_mm_per_hr": 12.4,
    "rain_1h_mm": 8.7,
    "status": "OBSERVED",
    "confidence": 0.90
  },
  "soil": {
    "saturation": 0.82,
    "status": "SIMULATED",
    "confidence": 0.85,
    "age_minutes": 5
  },
  "data_quality": {
    "overall_score": 0.92,
    "missing_sources": []
  }
}
```
