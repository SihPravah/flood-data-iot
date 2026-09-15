# PRAVAHA Data Credibility

This document is judge-facing. It explains which PRAVAHA evidence is live,
real static, derived, simulated, estimated or unavailable for the focused
Chandrabani PS 26192 demonstration.

## Live

| Data | Status | Notes |
| --- | --- | --- |
| Open-Meteo rainfall/current weather | `OBSERVED` when fetched successfully | Pulled through Data/IoT Open-Meteo adapter; network/weather values vary by run. |
| Canonical raw sensor POST | `OBSERVED` or caller-provided provenance | Backend/Data accept `location.lat/lon` and normalize to internal `latitude/longitude`. |

## Real Static

| Data | Status | Notes |
| --- | --- | --- |
| Study locality | `OPEN_REAL_DATA` | Chandrabani OSM place node anchors the focused demo area. |
| Road geometry | `OPEN_REAL_DATA` | OSM road ways are mapped onto stable PRAVAHA road IDs. |
| Stream geometry | `OPEN_REAL_DATA` | OSM waterway geometry is used as natural stream context. |
| Critical assets | `OPEN_REAL_DATA` | OSM schools/clinics/hospitals are shown as POIs, not automatically as evacuation shelters. |
| DEM/elevation | `OPEN_REAL_DATA` | OpenTopoData SRTM 30m samples provide elevation coverage for the focused bbox. |

## Derived

| Data | Status | Notes |
| --- | --- | --- |
| Slope summary | `DERIVED_FROM_REAL_DATA` | Representative mean slope is derived from the SRTM sample grid. |
| Terrain statistics | `DERIVED_FROM_REAL_DATA` | Min, max and mean elevation are calculated from sampled SRTM points. |
| Temporal rainfall windows | `DERIVED` measurement provenance | Data/IoT derives 15m, 30m, 1h, 3h, 6h and 24h accumulations from observation history. |
| ML hydrology/risk outputs | `DERIVED`/development model output | Derived from fused catchment state plus static context; not operationally calibrated. |

## Simulated

| Data | Status | Notes |
| --- | --- | --- |
| DEMO-001 rainfall/soil progression | `SIMULATED` | Deterministic scenario from NORMAL to WATCH to WARNING to SEVERE. |
| Software IoT nodes | `SIMULATED` unless a real device submits `OBSERVED` | Current local demo uses software publishers. |
| Demo authority closure | `DEMO` plus route status `CLOSED` | The closure fixture demonstrates semantics only; it is not a real authority feed. |
| Frontend mock provider | `SIMULATED` | Used only when `VITE_PRAVAHA_DATA_MODE=mock`. |

## Estimated

| Data | Status | Notes |
| --- | --- | --- |
| Focused micro-catchment polygon | `ESTIMATED` | An MVP envelope around Chandrabani, not an authoritative watershed delineation. |
| D-22 drain capacity | `ESTIMATED` | Demonstrates drainage overload logic; not measured municipal capacity. |
| Road flood exposure/historical waterlogging | `ESTIMATED`/model-derived | Decision-support context, not field verification. |
| Population/exposure counts | `MISSING`/`ESTIMATED` where shown | Not based on a committed authoritative population dataset. |

## Unavailable

| Data | Status | Notes |
| --- | --- | --- |
| Physical deployed IoT network | `NOT_AVAILABLE` | No hardware gateway is configured in this workspace. |
| Official road closures/evacuation orders | `NOT_AVAILABLE` | `CLOSED` appears only in a clearly marked demo authority-closure fixture. |
| Official shelter list | `NOT_AVAILABLE` | The school POI is real; the shelter role is demo-only. |
| Municipal storm-drain GIS/capacity | `NOT_AVAILABLE` | D-22 is estimated and spatially aligned to an OSM stream for demo context. |
| Ward/village polygons | `NOT_AVAILABLE` | OSM settlement points are used instead of fake polygons. |
| Historical local landslide inventory | `NOT_AVAILABLE` | The landslide zone is demo susceptibility context only. |
| HAND, TWI, flow direction, flow accumulation | `NOT_AVAILABLE` | Requires a hydrologically conditioned DEM workflow before use. |
| Operationally calibrated ML model | `NOT_AVAILABLE` | Current inference remains a development fallback and must be labelled accordingly. |

## Answering Judge Questions

| Question | Honest PRAVAHA answer |
| --- | --- |
| Where did this elevation come from? | OpenTopoData SRTM 30m samples stored in the Chandrabani static GIS asset. |
| Is this road real? | The road geometry/name is from OpenStreetMap where available; model risk over it is simulated/development unless fed by live observations. |
| Is this landslide real? | No local historical landslide inventory is committed; the displayed susceptibility zone is demo-only. |
| Is this drain capacity measured? | No. Drain capacity is estimated and must stay labelled `ESTIMATED`. |
| Is this rainfall currently live? | Open-Meteo rainfall can be live `OBSERVED`; DEMO-001 rainfall is `SIMULATED`. |
| Is this sensor physical? | The current local demo sensors are software/simulated unless a real device posts observed data. |
| Which values are simulated? | DEMO-001 dynamic hazards, software IoT values, demo closure and demo shelter designation are simulated/demo. |
