# PRAVAHA Canonical Data Contracts (v2.1 - Hardened Temporal & Provenance)

> [!NOTE]
> **ARCHITECTURE / CONTRACT CHANGE ALERT (v2.1)**
> - **Change**: Refactored `rainfall` inside `FusedCatchmentState` to separate instantaneous intensity (`intensity`: value, status, confidence, age_minutes) from standard time-integrated accumulation windows (`rain_15m`, `rain_30m`, `rain_1h`, `rain_3h`, `rain_6h`, `rain_24h`).
> - **Rationale**: Instantaneous sensor/API telemetry may be `OBSERVED`, while temporal accumulations are mathematically `DERIVED` over history. ML and downstream services now receive explicit provenance, coverage fractions, and quality status for every window.
> - **Soil Freshness**: `age_minutes` dynamically reflects observation age `(state_time - observed_at)`, with `null` if unobserved.

This document is the absolute source of truth across all 4 repositories (`flood-data-iot`, `flood-ml`, `flood-backend`, `flood-frontend`).

---

## 1. Raw Sensor Ingestion (IoT -> Backend / Data Ingestion)
*Ref: PRAVAHA Rule 9*

This is the external payload sent by IoT nodes or simulators prior to normalization.

**Endpoint:** `POST /api/v1/ingest/sensors`

```json
{
  "device_id": "SIM_NODE_04",
  "timestamp": "2026-09-09T17:30:00Z",
  "location": {
    "village": "Example Village",
    "ward": "Ward 1",
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

*Notes:*
- `rainfall_mm_per_hr` represents instantaneous intensity, **NOT** 1-hour accumulation.
- `soil_moisture_percentage` is bounded $[0, 100]$.
- `slope_tilt_degrees` is local node physical tilt, distinct from static DEM GIS terrain slope.

---

## 2. Canonical Normalized Observation (Internal Data/IoT)
*Ref: PRAVAHA Rule 6 & 8*

Internal representation decoupling external vendor APIs from internal processing.

```json
{
  "observation_id": "obs_123456",
  "source_id": "SIM_NODE_04",
  "source_type": "IOT_SENSOR",
  "observed_at": "2026-09-09T17:30:00Z",
  "location": {
    "latitude": 30.1234,
    "longitude": 78.4567
  },
  "measurements": {
    "rainfall_intensity_mm_per_hr": {
      "value": 12.4,
      "status": "OBSERVED"
    },
    "soil_moisture_percentage": {
      "value": 67.0,
      "status": "SIMULATED"
    },
    "slope_tilt_degrees": {
      "value": 2.1,
      "status": "SIMULATED"
    }
  }
}
```

---

## 3. Fused Catchment State (Data/IoT -> ML Engine / Backend)
*Ref: PRAVAHA Rule 20 & Hardening Pass v2.1*

Produced by the Data Fusion layer for an assigned catchment. Integrates multi-source telemetry, enforces provenance, evaluates Zero-Order Hold time integration, and calculates data quality.

**Endpoint:** `GET /api/v1/catchments/{catchment_id}/state`

```json
{
  "catchment_id": "UK-CHM-DEHRADUN-01",
  "state_time": "2026-09-09T17:30:00Z",
  "rainfall": {
    "intensity": {
      "value": 12.4,
      "status": "OBSERVED",
      "confidence": 0.95,
      "age_minutes": 2.5
    },
    "rain_15m": {
      "value_mm": 3.1,
      "status": "DERIVED",
      "coverage_fraction": 1.0,
      "largest_gap_minutes": 5.0,
      "latest_observation_age_minutes": 2.5,
      "observation_count": 3,
      "quality": "GOOD"
    },
    "rain_30m": {
      "value_mm": 6.2,
      "status": "DERIVED",
      "coverage_fraction": 0.95,
      "largest_gap_minutes": 5.0,
      "latest_observation_age_minutes": 2.5,
      "observation_count": 6,
      "quality": "GOOD"
    },
    "rain_1h": {
      "value_mm": 12.4,
      "status": "DERIVED",
      "coverage_fraction": 0.90,
      "largest_gap_minutes": 10.0,
      "latest_observation_age_minutes": 2.5,
      "observation_count": 12,
      "quality": "GOOD"
    },
    "rain_3h": {
      "value_mm": 24.8,
      "status": "DERIVED",
      "coverage_fraction": 0.85,
      "largest_gap_minutes": 15.0,
      "latest_observation_age_minutes": 2.5,
      "observation_count": 30,
      "quality": "GOOD"
    },
    "rain_6h": {
      "value_mm": 40.0,
      "status": "DERIVED",
      "coverage_fraction": 0.80,
      "largest_gap_minutes": 20.0,
      "latest_observation_age_minutes": 2.5,
      "observation_count": 55,
      "quality": "GOOD"
    },
    "rain_24h": {
      "value_mm": 65.5,
      "status": "DERIVED",
      "coverage_fraction": 0.75,
      "largest_gap_minutes": 45.0,
      "latest_observation_age_minutes": 2.5,
      "observation_count": 120,
      "quality": "DEGRADED"
    }
  },
  "soil": {
    "saturation": 0.67,
    "status": "SIMULATED",
    "confidence": 0.70,
    "age_minutes": 2.5
  },
  "data_quality": {
    "overall_score": 0.92,
    "missing_sources": [],
    "temporal_freshness": "GOOD"
  }
}
```

---

## 4. Fundamental Semantic Invariants

1. **`risk != confidence`**: A low risk prediction with low confidence must never be treated as safe.
2. **`prediction != observation`**: ML outputs are predictions; sensor data are observations.
3. **`0 != missing`**: 0.0 mm/hr means verified dry conditions; `null` with status `MISSING` means no data was received.
4. **`intensity != accumulated`**: Instantaneous rate (mm/hr) must be integrated across time to produce accumulation (mm).
5. **`SIMULATED != OBSERVED`**: Simulated mock data must retain `status="SIMULATED"` and never be disguised as real observations.
6. **Priority in Fusion**: Fresh `OBSERVED` takes precedence over `SIMULATED` or `DERIVED` regardless of ingestion arrival order.
