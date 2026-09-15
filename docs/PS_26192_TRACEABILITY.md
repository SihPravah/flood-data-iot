# PS 26192 Traceability Matrix

This document maps PRAVAHA against Smart India Hackathon 2026 Problem
Statement 26192: Flash Flood Prediction System for Hilly Regions using
Multi-Source Data.

Status values: `IMPLEMENTED`, `PARTIAL`, `DEMO`, `BLOCKED`, `NOT AVAILABLE`.

## Study Area

- `study_area_id`: `DEHRADUN-CHANDRABANI-PS26192`
- Prediction unit: `UK-CHM-DEHRADUN-01`
- Name: Chandrabani focused micro-catchment study area, Dehradun, Uttarakhand
- CRS: WGS84 longitude/latitude for API GeoJSON
- Metric CRS for distance/slope processing: `EPSG:32643`
- Approximate study bounding box: west `77.968`, south `30.270`,
  east `78.000`, north `30.300`
- Static GIS status: OpenStreetMap roads/stream/settlement/POIs and
  OpenTopoData SRTM elevation are committed as a small focused static extract.
- Operational GIS limitation: catchment boundary, drain capacity, shelter
  designation, official closures, HAND/TWI/flow accumulation, ward/village
  polygons, and historical landslide inventory remain estimated, demo, or not
  available as labelled.

## Requirement Matrix

| Problem Statement requirement | PRAVAHA component | Implementation | Endpoint/module | Demo proof | Validation status | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| Rainfall ingestion | Data/IoT | Raw sensor rainfall and Open-Meteo current rainfall normalize to canonical observations | `POST /api/v1/ingest/sensors`, `POST /api/v1/live/open-meteo`, `pravaha_data.adapters.open_meteo` | Open-Meteo adapter returned `OBSERVED` rainfall on 2026-09-15; demo sensor stream drives worsening state | IMPLEMENTED | Live provider value varies by weather and network |
| Rainfall windows | Data/IoT | ZOH temporal fusion calculates 15m, 30m, 1h, 3h, 6h, and 24h accumulation windows with coverage and gap quality | `pravaha_data.temporal.history`, `pravaha_data.fusion.catchment_fusion` | `DEMO-001` fixed observation sequence returns deterministic FusedCatchmentState v2.1 | IMPLEMENTED | One live observation alone correctly yields low coverage or `UNUSABLE` windows |
| Soil moisture | Data/IoT, ML | Sensor soil moisture is accepted; Open-Meteo soil variable is marked `DERIVED`; ML consumes soil saturation | `RawSensorPayload`, `normalize_open_meteo`, ML fused-state adapter | Sensor publisher can send `--soil 0.82`; demo state rises from 34% to 96% | PARTIAL | No physical soil sensor feed is configured in this workspace |
| Slope stability | ML | Landslide susceptibility and slope/soil/rainfall drivers exist in ML intelligence; SRTM-derived representative slope is now exposed as static GIS context | `pravaha_ml.landslide`, `pravaha_ml.geospatial.static_context`, Backend road/catchment/location DTOs | DEMO-001 severe stage raises landslide susceptibility and road impact over real/static terrain context | PARTIAL | Representative SRTM slope exists; detailed slope raster and field validation are not committed |
| Historical landslide inventory | ML | ML model supports inventory influence and missing inventory confidence penalties | `pravaha_ml.landslide` tests | Demo labels inventory context as unavailable and keeps the displayed susceptibility zone demo-only | NOT AVAILABLE | No credible local historical landslide inventory dataset is loaded |
| Real-time IoT ingestion | Backend, Data/IoT | Canonical POST accepts asynchronous event time, receive time, `location.lat/lon`, rainfall, soil, tilt, and provenance | `POST /api/v1/ingest/sensors`, `scripts/publish_sensor_event.py` | Golden backend test posts multiple events and observes snapshot changes | IMPLEMENTED | Current publisher is a software simulator, not a deployed hardware gateway |
| Multi-source fusion | Data/IoT | Canonical observations preserve provenance; observed data outranks simulated; missing is not zero | `CatchmentStateService`, `fuse_catchment_state` | Data tests cover provenance, missing, source health, deterministic fusion | IMPLEMENTED | Operational source registry remains in-memory |
| FusedCatchmentState v2.1 | Data/IoT | Authoritative ML-facing boundary includes rainfall intensity, windows, soil, data quality, freshness, gaps, counts, coverage, provenance | `GET /api/v1/catchments/{catchment_id}/state` | Data tests and Backend golden test consume the shape | IMPLEMENTED | Contract versioning is documentation-based today |
| Hyper-local prediction | ML | Prediction unit is catchment/sub-catchment; downstream DTOs map to ward, road, drain, shelter context | `pravaha_ml.inference.predictor`, Backend map/detail endpoints | DEMO-001 shows `UK-CHM-DEHRADUN-01` changing risk | DEMO | Real calibrated model artifact and operational validation are not available |
| Lead time | ML, Backend, Frontend | Timeline and threshold crossing windows are exposed with confidence and scenario assumptions | Backend catchment detail, map summary, frontend anticipation UI | WARNING shows `+30 min HIGH`; SEVERE shows `NOW SEVERE` | DEMO | Lead time is deterministic demo/development intelligence, not operational forecast validation |
| Village/ward warning | Backend, Frontend | Chandrabani settlement context is exposed through OSM settlement points, map search, alerts, and detail views | `GET /api/v1/map/intelligence`, `GET /api/v1/map/inspect`, frontend drawer | `VILLAGE-CHANDRABANI` appears as an OSM settlement point; no fake ward polygon is shown | PARTIAL | Authoritative ward/village polygons are not committed |
| Alert object | Backend, Frontend | Structured alerts include risk, confidence, reasons, provenance, affected entities, and review action | `GET /api/v1/map/alerts`, frontend alert center | DEMO-001 warning/drain alerts display separately from authority orders | IMPLEMENTED | Operational alert publishing/escalation workflow is not connected |
| Landslide-flood cascade | ML, Backend, Frontend | Cascade steps show rainfall, saturation, runoff, drain overload, road flooding, and landslide context | Backend catchment detail, frontend cascade UI | SEVERE scenario shows cascade and landslide road exposure | DEMO | Real inventory and terrain layers remain missing |
| Drainage impact | ML, Backend, Frontend | Drain details expose inflow, capacity, utilization, overflow, affected roads, provenance; D-22 geometry is aligned to a real OSM stream corridor | `GET /api/v1/map/drains/{drain_id}` | D-22 exceeds estimated capacity in WARNING/SEVERE | PARTIAL | Municipal drain identity and capacity are estimated, not measured or authority verified |
| Road risk | ML, Backend, Frontend | Road status distinguishes `PASSABLE`, `CAUTION`, `AVOID`, and `CLOSED`; current demo road geometries come from OSM | `GET /api/v1/map/roads/{road_id}` | Transport Nagar Road becomes model `AVOID`; mapped unnamed connector has a clearly labelled demo authority closure | IMPLEMENTED | OSM road geometry is real/open data; hazard status and demo closure are not real field observations |
| Evacuation/routing support | ML, Backend, Frontend | Route API returns selected route, alternatives, no-safe-route state, safety note, and blocked segments | `POST /api/v1/routes/safe` | Route reroutes to higher-ground bypass; isolated destination returns `NO_SAFE_ROUTE` | DEMO | No live traffic, authority order, or field verification feed |
| Source failure handling | Data/IoT, Backend, Frontend | Source health, freshness, missing values, and confidence are explicit; missing does not become zero or safe | `GET /api/v1/system/health`, source-health drawer | DEMO-001 SEVERE marks secondary sensor unavailable and keeps risk elevated | IMPLEMENTED | Source state is in-memory for local demo |
| Frontend command center | Frontend | Map-first UI with layers, search, detail drawer, route planner, alerts, source health, timeline, polling, and coordinate inspection | `flood-frontend/src` | API mode polls Backend; mock mode remains isolated and tagged; source status is visible in drawers/source health | IMPLEMENTED | Browser QA is local; no production deployment/auth setup |
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

- OpenStreetMap road geometry for Transport Nagar Road, Post Office Road, and
  an unnamed connector mapped to stable PRAVAHA road IDs.
- OpenStreetMap stream geometry used as natural stream context.
- OpenStreetMap settlement and critical-asset POIs, including Chandrabani and
  Rajaram Mohan Roy Academy.
- OpenTopoData SRTM 30m elevation samples for the focused Chandrabani bbox.

### Estimated values

- Focused micro-catchment envelope around Chandrabani.
- Representative SRTM-derived slope summary, until a full conditioned terrain
  product is prepared.
- D-22 municipal drain identity/capacity profile.
- Road exposure, historical waterlogging, population/exposure and local
  landslide susceptibility features where no authoritative local dataset exists.

### Missing or unavailable sources

- Physical IoT network.
- Full committed DEM raster, flow direction, flow accumulation, HAND and TWI.
- Authoritative road closures and evacuation orders.
- Official shelter list and shelter capacities.
- Authoritative ward/village polygons for the focused box.
- Measured municipal storm-drain geometry/capacity.
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

The live Open-Meteo source is working through Data/IoT into FusedCatchmentState.
The current full demo path now combines live/simulated dynamic observations with
real static OSM/SRTM context, while ML remains a labelled development fallback
and unverified/official GIS layers remain explicitly estimated, demo, or not
available.
