# PS 26192 Traceability Matrix

This document maps PRAVAHA against Smart India Hackathon 2026 Problem
Statement 26192: Flash Flood Prediction System for Hilly Regions using
Multi-Source Data.

Status values: `IMPLEMENTED`, `PARTIAL`, `DEMO`, `BLOCKED`, `NOT AVAILABLE`.

## Study Area

- `study_area_id`: `UK-CHM-DEHRADUN-01`
- Name: Chandrabani upper catchment demo sector, Dehradun, Uttarakhand
- CRS: WGS84 longitude/latitude for API GeoJSON
- Approximate demo bounding box: `[78.02, 30.31, 78.06, 30.35]`
- Static GIS status: demo/estimated geometry only in the current repositories
- Operational GIS limitation: verified DEM, derived slope rasters, authoritative
  ward boundaries, road inventories, shelters, and historical landslide
  inventories are not yet committed as source datasets

## Requirement Matrix

| Problem Statement requirement | PRAVAHA component | Implementation | Endpoint/module | Demo proof | Validation status | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| Rainfall ingestion | Data/IoT | Raw sensor rainfall and Open-Meteo current rainfall normalize to canonical observations | `POST /api/v1/ingest/sensors`, `POST /api/v1/live/open-meteo`, `pravaha_data.adapters.open_meteo` | Open-Meteo adapter returned `OBSERVED` rainfall on 2026-09-15; demo sensor stream drives worsening state | IMPLEMENTED | Live provider value varies by weather and network |
| Rainfall windows | Data/IoT | ZOH temporal fusion calculates 15m, 30m, 1h, 3h, 6h, and 24h accumulation windows with coverage and gap quality | `pravaha_data.temporal.history`, `pravaha_data.fusion.catchment_fusion` | `DEMO-001` fixed observation sequence returns deterministic FusedCatchmentState v2.1 | IMPLEMENTED | One live observation alone correctly yields low coverage or `UNUSABLE` windows |
| Soil moisture | Data/IoT, ML | Sensor soil moisture is accepted; Open-Meteo soil variable is marked `DERIVED`; ML consumes soil saturation | `RawSensorPayload`, `normalize_open_meteo`, ML fused-state adapter | Sensor publisher can send `--soil 0.82`; demo state rises from 34% to 96% | PARTIAL | No physical soil sensor feed is configured in this workspace |
| Slope stability | ML | Landslide susceptibility and slope/soil/rainfall drivers exist in ML intelligence | `pravaha_ml.landslide`, Backend road/catchment detail DTOs | DEMO-001 severe stage raises landslide susceptibility and road impact | DEMO | Verified DEM-derived slope data is not committed |
| Historical landslide inventory | ML | ML model supports inventory influence and missing inventory confidence penalties | `pravaha_ml.landslide` tests | Demo labels inventory context as estimated/unavailable | PARTIAL | No real historical landslide inventory dataset is loaded |
| Real-time IoT ingestion | Backend, Data/IoT | Canonical POST accepts asynchronous event time, receive time, `location.lat/lon`, rainfall, soil, tilt, and provenance | `POST /api/v1/ingest/sensors`, `scripts/publish_sensor_event.py` | Golden backend test posts multiple events and observes snapshot changes | IMPLEMENTED | Current publisher is a software simulator, not a deployed hardware gateway |
| Multi-source fusion | Data/IoT | Canonical observations preserve provenance; observed data outranks simulated; missing is not zero | `CatchmentStateService`, `fuse_catchment_state` | Data tests cover provenance, missing, source health, deterministic fusion | IMPLEMENTED | Operational source registry remains in-memory |
| FusedCatchmentState v2.1 | Data/IoT | Authoritative ML-facing boundary includes rainfall intensity, windows, soil, data quality, freshness, gaps, counts, coverage, provenance | `GET /api/v1/catchments/{catchment_id}/state` | Data tests and Backend golden test consume the shape | IMPLEMENTED | Contract versioning is documentation-based today |
| Hyper-local prediction | ML | Prediction unit is catchment/sub-catchment; downstream DTOs map to ward, road, drain, shelter context | `pravaha_ml.inference.predictor`, Backend map/detail endpoints | DEMO-001 shows `UK-CHM-DEHRADUN-01` changing risk | DEMO | Real calibrated model artifact and operational validation are not available |
| Lead time | ML, Backend, Frontend | Timeline and threshold crossing windows are exposed with confidence and scenario assumptions | Backend catchment detail, map summary, frontend anticipation UI | WARNING shows `+30 min HIGH`; SEVERE shows `NOW SEVERE` | DEMO | Lead time is deterministic demo/development intelligence, not operational forecast validation |
| Village/ward warning | Backend, Frontend | Ward/village identifiers and impacts are exposed in map layers, search, alerts, and detail views | `GET /api/v1/map/intelligence`, frontend drawer | `WARD-DEHRADUN-07` and `VILLAGE-CHANDRABANI` appear in demo | DEMO | Authoritative ward/village polygons are not committed |
| Alert object | Backend, Frontend | Structured alerts include risk, confidence, reasons, provenance, affected entities, and review action | `GET /api/v1/map/alerts`, frontend alert center | DEMO-001 warning/drain alerts display separately from authority orders | IMPLEMENTED | Operational alert publishing/escalation workflow is not connected |
| Landslide-flood cascade | ML, Backend, Frontend | Cascade steps show rainfall, saturation, runoff, drain overload, road flooding, and landslide context | Backend catchment detail, frontend cascade UI | SEVERE scenario shows cascade and landslide road exposure | DEMO | Real inventory and terrain layers remain missing |
| Drainage impact | ML, Backend, Frontend | Drain details expose inflow, capacity, utilization, overflow, affected roads, provenance | `GET /api/v1/map/drains/{drain_id}` | D-22 exceeds capacity in WARNING/SEVERE | DEMO | Capacity and geometry are estimated demo data |
| Road risk | ML, Backend, Frontend | Road status distinguishes `PASSABLE`, `CAUTION`, `AVOID`, and `CLOSED` | `GET /api/v1/map/roads/{road_id}` | `ROAD-SHELTER-CORRIDOR` becomes `AVOID`; bridge closure remains authority-marked | IMPLEMENTED | Demo road geometry is not an authoritative road inventory |
| Evacuation/routing support | ML, Backend, Frontend | Route API returns selected route, alternatives, no-safe-route state, safety note, and blocked segments | `POST /api/v1/routes/safe` | Route reroutes to higher-ground bypass; isolated destination returns `NO_SAFE_ROUTE` | DEMO | No live traffic, authority order, or field verification feed |
| Source failure handling | Data/IoT, Backend, Frontend | Source health, freshness, missing values, and confidence are explicit; missing does not become zero or safe | `GET /api/v1/system/health`, source-health drawer | DEMO-001 SEVERE marks secondary sensor unavailable and keeps risk elevated | IMPLEMENTED | Source state is in-memory for local demo |
| Frontend command center | Frontend | Map-first UI with layers, search, detail drawer, route planner, alerts, source health, timeline, and polling | `flood-frontend/src` | API mode polls Backend; mock mode remains isolated and tagged | IMPLEMENTED | Browser QA is local; no production deployment/auth setup |
| Operational deployment | All repos | Dev/test packaging exists and suites run on Python 3.11 and pnpm | `pyproject.toml`, `package.json` | Data 33 passed, ML 502 passed, Backend 25 passed | PARTIAL | Durable persistence, production orchestration, and real model serving are not complete |

## Data Classification

### Live sources currently available

- Open-Meteo current conditions through Data/IoT.
- Verified locally on 2026-09-15 with `OPEN_METEO` returning:
  - rainfall intensity: `0.0 mm/hr`, `OBSERVED`
  - soil moisture volumetric: `0.361 m3/m3`, `DERIVED`
  - observed time: `2026-09-15T13:15:00+00:00`
  - received time: `2026-09-15T13:25:25.287949+00:00`

### Simulated sources

- `DEMO-001` rainfall/soil sensor sequence.
- Backend deterministic development intelligence adapter.
- Frontend local mock provider, isolated behind the same typed API interface.

### Static sources

- Demo catchment, drain, road, stream, ward/village, shelter, landslide, and route
  geometries embedded as deterministic local fixtures.

### Estimated values

- Demo terrain, mean slope, drain capacity, shelter capacity, road exposure,
  historical waterlogging, and landslide inventory context.

### Missing or unavailable sources

- Physical IoT network.
- Verified DEM/elevation/slope raster source files.
- Authoritative road closures and evacuation orders.
- Real historical landslide inventory dataset.
- Calibrated operational ML artifact with real-world validation metrics.

## Current Acceptance Position

PRAVAHA can demonstrate the PS 26192 software flow with explicit demo labelling:

```text
canonical observation
-> Data/IoT normalization
-> temporal fusion
-> FusedCatchmentState v2.1
-> ML/development intelligence
-> Backend monitoring snapshot
-> Frontend map
```

The live Open-Meteo source is working through Data/IoT into FusedCatchmentState,
but the complete live Backend-to-real-ML operational path remains `PARTIAL`
until a deployable ML service/artifact and verified static GIS datasets are
connected.
