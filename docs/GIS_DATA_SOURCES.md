# PRAVAHA GIS Data Sources

This document records the static GIS context used for the focused PS 26192
Chandrabani demonstration. The machine-readable static extract is committed at
`src/pravaha_data/gis/static/chandrabani_study_area.json`; the reproducible
fetch/preparation script is `scripts/download_gis_data.py`.

## Study Area

| Field | Value |
| --- | --- |
| Study area ID | `DEHRADUN-CHANDRABANI-PS26192` |
| Name | Chandrabani focused micro-catchment study area |
| District/state | Dehradun, Uttarakhand |
| Public CRS | `EPSG:4326` |
| Metric CRS | `EPSG:32643` |
| Bounding box | west `77.968`, south `30.270`, east `78.000`, north `30.300` |
| Center | longitude `77.978689`, latitude `30.285029` |
| Approximate area | `10.25 km2` |
| Reason selected | Existing PRAVAHA demo IDs reference Chandrabani, and this compact area has OSM road, stream, settlement and POI coverage. |

## Source Status Vocabulary

| Status | Meaning |
| --- | --- |
| `AUTHORITATIVE` | Government/official source for the exact layer and area. |
| `OPEN_REAL_DATA` | Real-world open dataset such as OpenStreetMap or public DEM. |
| `DERIVED_FROM_REAL_DATA` | Deterministic derivative from a real static dataset. |
| `ESTIMATED` | PRAVAHA assumption or coarse derivation not field/authority verified. |
| `DEMO` | Deterministic demo fixture or demo-only designation. |
| `NOT_AVAILABLE` | Required layer/attribute is unavailable in this workspace. |

## Layer Manifest

| Layer | Dataset/provider | Status | Resolution/version | License/source | Processing | Used by | Known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DEM/elevation | OpenTopoData SRTM 30m elevation API | `OPEN_REAL_DATA` | SRTM 30m endpoint, sampled 2026-09-16 | OpenTopoData/SRTM terms | 25-point grid sampled across bbox; stats stored in static JSON | Data static context, ML static context, Backend map inspection, Frontend detail drawer | Small sampled extract, not a committed raw raster. |
| Slope | Derived from sampled SRTM elevations | `DERIVED_FROM_REAL_DATA` | representative mean `0.46 deg`, `0.0079 fraction` | Derived from OpenTopoData SRTM | Finite-difference representative slope over metre spacing | ML terrain context, Backend catchment/road/location detail, Frontend | Not hydrologically conditioned; local cell-level slope raster not committed. |
| Catchment polygon | PRAVAHA focused micro-catchment envelope | `ESTIMATED` | bbox-derived MVP polygon | PRAVAHA static fixture | Compact envelope around Chandrabani for demo prediction unit | Data catchment assignment, ML predictor context, Backend map | Not an authoritative watershed delineation. |
| Streams | OpenStreetMap waterway via Overpass | `OPEN_REAL_DATA` | OSM way `234936176`, timestamp `2026-07-24T11:04:51Z` | OpenStreetMap ODbL | OSM way converted to EPSG:4326 LineString | ML drainage context, Backend river/drain proximity, Frontend rivers | Natural stream only; not municipal storm-drain infrastructure. |
| Drain geometry | D-22 estimated collector aligned to OSM stream | `ESTIMATED` | OSM stream geometry plus PRAVAHA estimated profile | OSM ODbL plus PRAVAHA demo assumption | Uses real stream corridor for spatial context, estimated capacity for demo hydrology | ML drainage, Backend drain detail, Frontend drains | Capacity and municipal identity are not measured/authority verified. |
| Roads | OpenStreetMap roads via Overpass | `OPEN_REAL_DATA` | Transport Nagar Road way `114099376`; Post Office Road way `101971528`; unnamed connector way `1095906636`; road timestamps `2026-05-06T03:25:00Z` | OpenStreetMap ODbL | OSM ways mapped to stable PRAVAHA road IDs for continuity | ML routing/static road context, Backend map/route/detail, Frontend road layer | OSM geometry is real/open data; hazard status remains simulated/model-derived in DEMO-001. |
| Settlement/admin context | OpenStreetMap place/POI nodes | `OPEN_REAL_DATA` | Chandrabani node `2379693646`; Subhashnagar node `2379693754` | OpenStreetMap ODbL | Settlement points retained as points | Backend location inspection, Frontend search/detail | Ward/village polygons are not available, so no fake boundaries are shown. |
| Critical assets | OpenStreetMap schools/clinics/hospitals | `OPEN_REAL_DATA` | Rajaram Mohan Roy Academy node `4254504794`; Baunthiyal Nursing Home node `6950253649`; Minocha Hospital and Maternity Home node `6956686347` | OpenStreetMap ODbL | OSM POIs converted to point assets | Backend inspection, Frontend shelter/asset context | POI existence is open real data; evacuation shelter designation is not authority verified. |
| Shelter designation | DEMO-001 shelter at Rajaram Mohan Roy Academy POI | `DEMO` | deterministic demo fixture | PRAVAHA demo fixture plus OSM POI geometry | Keeps school POI real, shelter role demo-labelled | Backend route/shelter detail, Frontend route planner | Not an official shelter list. |
| Historical landslide inventory | None committed for focused bbox | `NOT_AVAILABLE` | n/a | n/a | DEMO susceptibility zone retained only for scenario visualization | ML landslide module and Frontend layer in demo mode | No real local historical landslide inventory is represented. |
| HAND/TWI/flow direction | Not generated in this pass | `NOT_AVAILABLE` | n/a | n/a | Values return null/not available | Backend location inspection, Frontend drawer | Requires hydrologically conditioned DEM workflow before use. |

## Attribution

- OpenStreetMap geometry must retain OpenStreetMap contributor attribution and ODbL licensing.
- SRTM elevation values are accessed through OpenTopoData; upstream SRTM/OpenTopoData terms apply.
- DEMO-001 dynamic hazards, simulated IoT observations, demo closure, and demo shelter designation must stay visibly marked as simulated/demo.

## Setup

Run the fetch/preparation script from the repository root when refreshing the
small static extract:

```powershell
.venv\Scripts\python.exe scripts\download_gis_data.py
```

If public GIS endpoints are unavailable, keep the last committed static asset
and do not silently replace unavailable real/static layers with simulated data
outside demo mode.
