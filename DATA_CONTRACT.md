# PRAVAHA Canonical Data Contracts (v2.4 - PS 26192 Integration)

> [!NOTE]
> **ARCHITECTURE / CONTRACT CHANGE ALERT (v2.1)**
> - **Change**: Refactored `rainfall` inside `FusedCatchmentState` to separate instantaneous intensity (`intensity`: value, status, confidence, age_minutes) from standard time-integrated accumulation windows (`rain_15m`, `rain_30m`, `rain_1h`, `rain_3h`, `rain_6h`, `rain_24h`).
> - **Rationale**: Instantaneous sensor/API telemetry may be `OBSERVED`, while temporal accumulations are mathematically `DERIVED` over history. ML and downstream services now receive explicit provenance, coverage fractions, and quality status for every window.
> - **Soil Freshness**: `age_minutes` dynamically reflects observation age `(state_time - observed_at)`, with `null` if unobserved.

> [!NOTE]
> **ARCHITECTURE / CONTRACT CHANGE ALERT (v2.2 proposal)**
> - **Change**: Preserves external raw sensor `location.lat/location.lon`, makes `FusedCatchmentState v2.1` the live ML boundary, and proposes stable Backend <-> Frontend map/detail/route DTOs.
> - **Rationale**: ML should consume canonical fused catchment state, not raw sensor payloads. Backend and Frontend need stable route, map, provenance, confidence, and `NO_SAFE_ROUTE` semantics before integration.
> - **Safety**: `CLOSED` is authority-confirmed only. AI-predicted unsafe roads remain `AVOID`. `NO_SAFE_ROUTE` is an explicit API response, not an exception leak.

> [!NOTE]
> **ARCHITECTURE / CONTRACT CHANGE ALERT (v2.3 proposal)**
> - **Change**: Adds the `DEMO-001` monitoring snapshot, source-health, structured-event, and model-metadata contracts used by Backend and Frontend.
> - **IDs**: Shared DTOs use `catchment_id`, `ward_id`, `village_id`, `road_id`, `drain_id`, `sensor_id`, `shelter_id`, `bridge_id`, `landslide_zone_id`, `alert_id`, `prediction_id`, `snapshot_id`, `route_id`, and `scenario_id`.
> - **Demo IDs**: `DEMO-001` uses one coherent namespace: `UK-CHM-DEHRADUN-01`, `WARD-DEHRADUN-07`, `VILLAGE-CHANDRABANI`, `D-22`, `ROAD-SHELTER-CORRIDOR`, `ROAD-HIGHER-GROUND-BYPASS`, `ROAD-BRIDGE-APPROACH`, `SENSOR-SIM-RAIN-SOIL-01`, `SENSOR-SIM-RAIN-SOIL-02`, `SHELTER-SCHOOL-01`, and `LANDSLIDE-ZONE-S-01`.

> [!NOTE]
> **ARCHITECTURE / CONTRACT CHANGE ALERT (v2.4 proposal)**
> - **Change**: Makes event-time ingestion explicit with `observed_at`, optional `received_at`, and optional measurement `provenance`; keeps `timestamp` as a backward-compatible alias for `observed_at`.
> - **Change**: Defines Data/IoT live-state endpoints for sensor ingestion, Open-Meteo ingestion, catchment state retrieval, and source health.
> - **Change**: Aligns the route API with the implemented Backend and Frontend DTO: `ROUTE_FOUND` returns `selected_route` plus `alternatives`; `NO_SAFE_ROUTE` returns a list of blocking route segments.
> - **Safety**: API mode should request the latest Backend monitoring snapshot by default. Scenario-stage query parameters are for deterministic demo review and must not be the only path by which the Frontend can observe real sensor updates.

This document is the absolute source of truth across all 4 repositories (`flood-data-iot`, `flood-ml`, `flood-backend`, `flood-frontend`).

---

## 1. Raw Sensor Ingestion (IoT -> Backend / Data Ingestion)
*Ref: PRAVAHA Rule 9*

This is the external payload sent by IoT nodes or simulators prior to normalization.

**Endpoint:** `POST /api/v1/ingest/sensors`

```json
{
  "device_id": "SENSOR-SIM-RAIN-SOIL-01",
  "observed_at": "2026-09-09T17:30:00Z",
  "received_at": "2026-09-09T17:30:04Z",
  "provenance": "OBSERVED",
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
- External raw sensor coordinates are `lat`/`lon`. Internal canonical observations normalize them to `latitude`/`longitude`.
- `observed_at` is the sensor event time. `timestamp` remains an accepted compatibility alias for existing clients.
- `received_at` is optional. If omitted, Backend/Data may use server receive time.
- `provenance` defaults to `OBSERVED`. `SIMULATED` is allowed only in demo/development mode and must stay visibly tagged.

---

## 2. Canonical Normalized Observation (Internal Data/IoT)
*Ref: PRAVAHA Rule 6 & 8*

Internal representation decoupling external vendor APIs from internal processing.

```json
{
  "observation_id": "obs_123456",
  "source_id": "SENSOR-SIM-RAIN-SOIL-01",
  "source_type": "IOT_SENSOR",
  "observed_at": "2026-09-09T17:30:00Z",
  "received_at": "2026-09-09T17:30:04Z",
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

Data/IoT endpoint families:

- `POST /api/v1/ingest/sensors`
- `POST /api/v1/live/open-meteo`
- `GET /api/v1/catchments/{catchment_id}/state`
- `GET /api/v1/system/source-health`

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

## 4. Backend <-> Frontend Map and Routing DTOs (Proposed)

These DTOs are the proposed shared public API shape for Backend and Frontend. Backend may assemble these from Data/IoT and ML, but must not duplicate ML logic.

Risk-bearing objects must keep these fields separate:

- `risk_score`
- `risk_level`
- `confidence`
- `reasons`
- `provenance`
- `last_updated`

Static map/GIS assets may expose `verification_status` separately from measurement provenance. Do not represent static `VERIFIED` assets as `OBSERVED` measurements.

### 4.1 Map Intelligence Snapshot

**Endpoint:** `GET /api/v1/map/intelligence`

If `scenario_stage` is omitted, Backend returns the latest monitoring snapshot
or builds one from configured live services. `scenario_stage` is reserved for
deterministic demo review.

```json
{
  "snapshot_id": "snap_20260909T173000Z",
  "generated_at": "2026-09-09T17:30:00Z",
  "state_time": "2026-09-09T17:30:00Z",
  "scenario_id": "DEMO-001",
  "mode": "DEMO",
  "data_label": "SIMULATED",
  "city": {
    "city_id": "UK-DEHRADUN",
    "name": "Dehradun",
    "operational_status": "ELEVATED",
    "confidence": 0.74,
    "reasons": ["drain_overload", "road_avoidance_present"],
    "last_updated": "2026-09-09T17:30:00Z"
  },
  "layers": {
    "catchments": { "type": "FeatureCollection", "features": [] },
    "wards": { "type": "FeatureCollection", "features": [] },
    "drains": { "type": "FeatureCollection", "features": [] },
    "roads": { "type": "FeatureCollection", "features": [] },
    "sensors": { "type": "FeatureCollection", "features": [] },
    "shelters": { "type": "FeatureCollection", "features": [] },
    "routes": { "type": "FeatureCollection", "features": [] }
  },
  "summary": {
    "catchment_count": 1,
    "high_risk_catchments": 0,
    "overflowing_drains": 1,
    "roads_to_avoid": 1,
    "confirmed_road_closures": 0,
    "active_alerts": 1
  },
  "source_health": [],
  "events": [],
  "model_metadata": {}
}
```

All GeoJSON coordinates must use `[longitude, latitude]`.

### 4.2 Catchment Detail

**Endpoint:** `GET /api/v1/map/catchments/{catchment_id}`

```json
{
  "catchment_id": "UK-CHM-DEHRADUN-01",
  "snapshot_id": "snap_20260909T173000Z",
  "risk_score": 0.64,
  "risk_level": "WARNING",
  "confidence": 0.76,
  "reasons": ["rainfall_increasing", "soil_saturation_high"],
  "provenance": {
    "data_label": "SIMULATED",
    "sources": ["SENSOR-SIM-RAIN-SOIL-01"],
    "static_verification_status": "ESTIMATED"
  },
  "last_updated": "2026-09-09T17:30:00Z",
  "fused_state": "FusedCatchmentState v2.1",
  "hydrology": {
    "runoff_mm": 18.2,
    "concentration_time_minutes": 26.0
  },
  "anticipation": {
    "trend": "RISING",
    "threshold_window": {
      "risk_level": "HIGH",
      "earliest_minutes": 30,
      "latest_minutes": 60
    }
  }
}
```

### 4.3 Drain Detail

**Endpoint:** `GET /api/v1/map/drains/{drain_id}`

```json
{
  "drain_id": "D-22",
  "snapshot_id": "snap_20260909T173000Z",
  "risk_score": 0.72,
  "risk_level": "HIGH",
  "confidence": 0.70,
  "reasons": ["estimated_inflow_exceeds_effective_capacity"],
  "provenance": {
    "data_label": "SIMULATED",
    "capacity_verification_status": "ESTIMATED",
    "sources": ["UK-CHM-DEHRADUN-01"]
  },
  "last_updated": "2026-09-09T17:30:00Z",
  "inflow_m3_per_s": 3.2,
  "capacity_m3_per_s": 2.6,
  "capacity_utilization": 1.23,
  "overflow_m3_per_s": 0.6,
  "condition": "ESTIMATED"
}
```

### 4.4 Road Detail

**Endpoint:** `GET /api/v1/map/roads/{road_id}`

```json
{
  "road_id": "ROAD-SHELTER-CORRIDOR",
  "snapshot_id": "snap_20260909T173000Z",
  "risk_score": 0.78,
  "risk_level": "HIGH",
  "recommendation": "AVOID",
  "confidence": 0.68,
  "reasons": ["nearby_drain_over_capacity", "catchment_flood_risk_high"],
  "provenance": {
    "data_label": "SIMULATED",
    "road_verification_status": "ESTIMATED",
    "sources": ["D-22", "UK-CHM-DEHRADUN-01"]
  },
  "last_updated": "2026-09-09T17:30:00Z",
  "associated_drain_id": "D-22",
  "authority_closed": false
}
```

`CLOSED` may appear only when `authority_closed=true`.

### 4.5 Sensor Detail

**Endpoint:** `GET /api/v1/map/sensors/{device_id}`

```json
{
  "device_id": "SENSOR-SIM-RAIN-SOIL-01",
  "snapshot_id": "snap_20260909T173000Z",
  "catchment_id": "UK-CHM-DEHRADUN-01",
  "location": {
    "latitude": 30.3165,
    "longitude": 78.0322
  },
  "measurements": {
    "rainfall_intensity_mm_per_hr": {
      "value": 42.0,
      "status": "SIMULATED"
    },
    "soil_moisture_percentage": {
      "value": 76.0,
      "status": "SIMULATED"
    }
  },
  "freshness": {
    "observed_at": "2026-09-09T17:30:00Z",
    "age_minutes": 2.5,
    "quality": "GOOD"
  },
  "provenance": {
    "data_label": "SIMULATED",
    "sources": ["SENSOR-SIM-RAIN-SOIL-01"]
  },
  "last_updated": "2026-09-09T17:30:00Z"
}
```

### 4.6 Alerts

**Endpoint:** `GET /api/v1/map/alerts`

```json
{
  "snapshot_id": "snap_20260909T173000Z",
  "alerts": [
    {
      "alert_id": "ALERT-001",
      "scope_type": "ROAD",
      "scope_id": "ROAD-SHELTER-CORRIDOR",
      "risk_score": 0.78,
      "risk_level": "HIGH",
      "confidence": 0.68,
      "message": "Road should be avoided due to modeled flood exposure.",
      "reasons": ["nearby_drain_over_capacity"],
      "provenance": {
        "data_label": "SIMULATED",
        "sources": ["D-22"]
      },
      "last_updated": "2026-09-09T17:30:00Z"
    }
  ]
}
```

### 4.7 Safe Route Request

**Endpoint:** `POST /api/v1/routes/safe`

```json
{
  "origin": {
    "longitude": 78.0322,
    "latitude": 30.3165
  },
  "destination": {
    "longitude": 78.0460,
    "latitude": 30.3290
  },
  "strategy": "safest",
  "snapshot_id": "snap_20260909T173000Z"
}
```

Supported strategies:

- `safest`
- `balanced`
- `fastest_available`

### 4.8 Safe Route Success

```json
{
  "status": "ROUTE_FOUND",
  "snapshot_id": "snap_20260909T173000Z",
  "generated_at": "2026-09-09T17:30:00Z",
  "selected_route": {
    "route_id": "ROUTE-001",
    "label": "Bypass via higher ground",
    "strategy": "safest",
    "geometry": {
      "type": "LineString",
      "coordinates": [[78.0322, 30.3165], [78.0460, 30.3290]]
    },
    "travel_time_minutes": 18.0,
    "distance_km": 2.4,
    "maximum_risk_score": 0.42,
    "minimum_confidence": 0.74,
    "additional_time_vs_fastest_minutes": 7.0,
    "unsafe_segments_avoided": 1,
    "closures_avoided": 0,
    "explanation": ["predicted_unsafe_segments_excluded"],
    "segments": []
  },
  "alternatives": [],
  "provenance": {
    "data_label": "SIMULATED",
    "sources": ["ROAD-SHELTER-CORRIDOR", "ROAD-HIGHER-GROUND-BYPASS"]
  },
  "safety_note": "PRAVAHA is decision support and does not guarantee route safety."
}
```

### 4.9 NO_SAFE_ROUTE

```json
{
  "status": "NO_SAFE_ROUTE",
  "snapshot_id": "snap_20260909T173000Z",
  "generated_at": "2026-09-09T17:30:00Z",
  "reason_code": "ALL_CANDIDATE_ROUTES_BLOCKED",
  "message": "No route meeting the configured safety policy is available.",
  "blocked_by": [
    {
      "road_id": "ROAD-BRIDGE-APPROACH",
      "recommendation": "CLOSED",
      "risk_score": 0.95,
      "risk_level": "SEVERE",
      "confidence": 0.72,
      "reasons": ["authority_confirmed_closure"]
    },
    {
      "road_id": "ROAD-SHELTER-CORRIDOR",
      "recommendation": "AVOID",
      "risk_score": 0.82,
      "risk_level": "HIGH",
      "confidence": 0.68,
      "reasons": ["model_derived_flood_exposure"]
    }
  ],
  "provenance": {
    "data_label": "SIMULATED",
    "sources": ["ROAD-SHELTER-CORRIDOR", "ROAD-HIGHER-GROUND-BYPASS", "ROAD-BRIDGE-APPROACH"]
  },
  "safety_note": "PRAVAHA is decision support and does not guarantee route safety."
}
```

`NO_SAFE_ROUTE` must be returned as an explicit domain response. It must not be exposed as a stack trace, uncaught exception, or fabricated "safe" route.

### 4.10 Source Health

**Backend Endpoint:** `GET /api/v1/system/health`

**Data/IoT Endpoint:** `GET /api/v1/system/source-health`

```json
{
  "source_id": "SENSOR-SIM-RAIN-SOIL-01",
  "name": "Demo rainfall and soil node",
  "category": "IOT_SENSOR",
  "status": "SIMULATED",
  "last_success_at": "2026-09-09T17:30:04Z",
  "last_observation_at": "2026-09-09T17:30:00Z",
  "age_seconds": 4,
  "expected_interval_seconds": 900,
  "freshness": "GOOD",
  "provenance": "SIMULATED",
  "message": "Deterministic DEMO-001 source"
}
```

Allowed source-health statuses are `HEALTHY`, `DEGRADED`, `UNAVAILABLE`, `STATIC`, and `SIMULATED`.

### 4.11 Structured Events

**Endpoint:** `GET /api/v1/events`

```json
{
  "event_id": "EVENT-DEMO-001-003",
  "snapshot_id": "snap_20260909T173000Z",
  "generated_at": "2026-09-09T17:30:00Z",
  "entity_type": "road",
  "entity_id": "ROAD-SHELTER-CORRIDOR",
  "event_type": "ROAD_RECOMMENDATION_CHANGED",
  "previous_value": "CAUTION",
  "current_value": "AVOID",
  "severity": "WARNING",
  "title": "Road recommendation changed",
  "message": "Road recommendation changed to AVOID because D-22 exceeded estimated capacity.",
  "reasons": ["nearby_drain_over_capacity"],
  "provenance": {
    "data_label": "SIMULATED",
    "sources": ["D-22", "ROAD-SHELTER-CORRIDOR"]
  }
}
```

Events provide traceability for what changed and when. They are not official closure or evacuation-order records.

### 4.12 Model Metadata

```json
{
  "prediction_id": "PRED-DEMO-001-WARNING",
  "model_version": "synthetic-development-v1",
  "generated_at": "2026-09-09T17:30:00Z",
  "input_state_time": "2026-09-09T17:30:00Z",
  "risk_score": 0.64,
  "risk_level": "WARNING",
  "confidence": 0.76,
  "data_quality_score": 0.9,
  "top_factors": ["rainfall_increasing", "soil_saturation_high", "drain_overload"],
  "runtime_status": "DEVELOPMENT_FALLBACK",
  "operationally_validated": false
}
```

Synthetic/development model metadata must stay visibly labelled and must not be presented as operational validation.

---

## 5. Static Data Verification

Measurement provenance is limited to:

- `OBSERVED`
- `DERIVED`
- `ESTIMATED`
- `SIMULATED`
- `MISSING`

Static assets such as catchment polygons, road geometry, drain geometry, DEM-derived slope, shelter capacity, and historical landslide inventories may separately expose:

- `verification_status`: `VERIFIED`, `DERIVED`, `ESTIMATED`, or `UNKNOWN`
- `source_name`
- `source_updated_at`

Do not map static `VERIFIED` evidence into measurement `OBSERVED`.

---

## 6. Fundamental Semantic Invariants

1. **`risk != confidence`**: A low risk prediction with low confidence must never be treated as safe.
2. **`prediction != observation`**: ML outputs are predictions; sensor data are observations.
3. **`0 != missing`**: 0.0 mm/hr means verified dry conditions; `null` with status `MISSING` means no data was received.
4. **`intensity != accumulated`**: Instantaneous rate (mm/hr) must be integrated across time to produce accumulation (mm).
5. **`SIMULATED != OBSERVED`**: Simulated mock data must retain `status="SIMULATED"` and never be disguised as real observations.
6. **Priority in Fusion**: Fresh `OBSERVED` takes precedence over `SIMULATED` or `DERIVED` regardless of ingestion arrival order.
7. **`AVOID != CLOSED`**: `AVOID` is model-derived route avoidance; `CLOSED` is authority-confirmed only.
8. **`NO_SAFE_ROUTE != exception`**: no-route conditions are explicit domain responses.
