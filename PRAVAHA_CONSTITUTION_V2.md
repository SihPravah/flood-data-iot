# PRAVAHA Constitution V2

## Architecture

PRAVAHA is a software-only hyper-local flash-flood prediction and anticipatory
disaster decision-support system for hilly regions. The runtime boundary remains
four repositories:

- `flood-data-iot`: external feeds, raw sensor ingestion, normalization,
  temporal history, source health, provenance and `FusedCatchmentState v2.1`.
- `flood-ml`: hydrology, flood risk, confidence, landslide, anticipation,
  cascade, drainage, road/routing, impact, evacuation and city intelligence.
- `flood-backend`: orchestration, state/cache, stable APIs, route requests,
  alerts, events, source health and frontend-facing DTOs.
- `flood-frontend`: premium map-first command center.

Canonical live flow:

```text
external/simulation
-> flood-data-iot
-> FusedCatchmentState v2.1
-> flood-ml
-> flood-backend
-> flood-frontend
```

The frontend talks only to the backend. The backend does not duplicate
hydrology, flood-risk or route-risk logic. Data/IoT never predicts flood risk.

## Contract Authority

`flood-data-iot/DATA_CONTRACT.md` is the cross-repository source of truth. Any
shared API, schema, unit, enum or ID change must emit:

```text
ARCHITECTURE / CONTRACT CHANGE ALERT
```

## Canonical IDs

Shared DTOs use these field names:

- `catchment_id`
- `ward_id`
- `village_id`
- `road_id`
- `drain_id`
- `sensor_id`
- `shelter_id`
- `bridge_id`
- `landslide_zone_id`
- `alert_id`
- `prediction_id`
- `snapshot_id`
- `route_id`
- `scenario_id`

The deterministic SIH demo scenario is `DEMO-001`.

## Units

Use unit-bearing field names wherever a number leaves a module boundary:

- rainfall intensity: `rainfall_intensity_mm_per_hr`
- rainfall accumulations: `rain_15m_mm`, `rain_30m_mm`, `rain_1h_mm`,
  `rain_3h_mm`, `rain_6h_mm`, `rain_24h_mm`
- runoff: `runoff_mm`
- discharge: `discharge_m3_s`
- elevation and distance: `elevation_m`, `distance_m`, `distance_km`
- catchment area: `area_km2`
- time horizon: `lead_time_minutes`
- terrain slope: `mean_slope_deg` or `mean_slope_fraction`
- probability/confidence: `0..1`
- GeoJSON API coordinates: `[longitude, latitude]`

## Event Time

Dynamic observations preserve:

- `source`
- `observed_at`
- `received_at`
- `value`
- `unit`
- `status` / provenance
- `quality`
- `confidence`
- computed age

`observed_at` is measurement time. `received_at` is ingestion time. They must
not be collapsed.

## FusedCatchmentState V2.1

The live ML boundary retains:

- `catchment_id`
- `state_time`
- `rainfall.intensity`
- `rainfall.rain_15m`
- `rainfall.rain_30m`
- `rainfall.rain_1h`
- `rainfall.rain_3h`
- `rainfall.rain_6h`
- `rainfall.rain_24h`
- `soil.saturation`
- provenance
- confidence
- freshness
- `coverage_fraction`
- `largest_gap_minutes`
- `latest_observation_age_minutes`
- `observation_count`
- `quality`
- `data_quality`

Rainfall intensity is a rate in `mm/hr`. Rainfall windows are accumulations in
`mm` derived by temporal integration.

## Provenance And Freshness

Measurement provenance is one of:

- `OBSERVED`
- `DERIVED`
- `ESTIMATED`
- `SIMULATED`
- `MISSING`

Freshness and quality are separate from provenance. Static GIS verification can
use a separate static-data verification field and must not be represented as
`OBSERVED` measurement provenance.

## Source Health

Source health objects use:

- `source_id`
- `name`
- `category`
- `status`
- `last_success_at`
- `last_observation_at`
- `age_seconds`
- `expected_interval_seconds`
- `freshness`
- `provenance`
- `message`

Allowed health statuses are `HEALTHY`, `DEGRADED`, `UNAVAILABLE`, `STATIC` and
`SIMULATED`.

## Degradation Rules

- Never silently substitute simulated data in operational mode.
- Missing rainfall/soil data degrades confidence or blocks reliable prediction;
  it does not become zero or LOW risk.
- If a model artifact is synthetic/development fallback, label it as such.
- If routing cannot produce an acceptable path, return explicit `NO_SAFE_ROUTE`.
- `CLOSED` means authority-confirmed closure only.
- `AVOID` means model-derived route avoidance.

## Monitoring Snapshot

The backend-facing snapshot concept includes:

- `snapshot_id`
- `generated_at`
- `state_time`
- `scenario_id`
- `mode`
- `operational_status`
- `source_health`
- `catchments`
- `wards`
- `villages`
- `sensors`
- `drains`
- `roads`
- `bridges`
- `shelters`
- `landslide_zones`
- `alerts`
- `routes`
- `anticipation`
- `model_metadata`

All frontend panels derive from the current snapshot instead of duplicating
hardcoded counters.

## Events

Structured events use:

- `event_id`
- `timestamp`
- `entity_type`
- `entity_id`
- `event_type`
- `previous_value`
- `current_value`
- `severity`
- `message`
- `provenance`

Events are decision-support traceability, not authority bulletins.

## Demo Scenario

`DEMO-001` is deterministic and entirely `SIMULATED`. It contains:

```text
NORMAL -> WATCH -> WARNING -> SEVERE
```

The scenario demonstrates rising rainfall, wetter soil, higher flood risk,
drain overload, road `AVOID`, route recomputation and city status escalation.

## Runtime Topology

Local SIH runtime may use in-process Python adapters for Data/IoT and ML, but
must keep service boundaries replaceable with HTTP services. Production mode
must fail explicitly when live dependencies are unavailable.

## Golden Integration Path

```text
DEMO-001 raw observations
-> normalization
-> temporal fusion
-> FusedCatchmentState v2.1
-> ML intelligence
-> backend snapshot/API
-> frontend map/detail/route/event/source-health UX
```

A degraded critical input must reduce confidence or make intelligence
insufficient; it must not force LOW risk or fabricate safe conditions.
