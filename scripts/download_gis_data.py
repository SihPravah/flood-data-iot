"""Fetch and prepare the focused PRAVAHA Chandrabani GIS asset pack.

The script intentionally writes only small processed JSON/GeoJSON assets.
Raw Overpass/OpenTopoData responses are not committed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "src"
    / "pravaha_data"
    / "gis"
    / "static"
    / "chandrabani_study_area.json"
)

OVERPASS_URLS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
OPENTOPO_URL = "https://api.opentopodata.org/v1/srtm30m"

STUDY_AREA = {
    "study_area_id": "DEHRADUN-CHANDRABANI-PS26192",
    "name": "Chandrabani focused micro-catchment study area",
    "state": "Uttarakhand",
    "district": "Dehradun",
    "country": "India",
    "bounding_box": {
        "west": 77.968,
        "south": 30.270,
        "east": 78.000,
        "north": 30.300,
    },
    "center": {
        "latitude": 30.285029,
        "longitude": 77.978689,
    },
    "public_crs": "EPSG:4326",
    "metric_crs": "EPSG:32643",
    "reason_selected": (
        "The existing PRAVAHA demo ID names Chandrabani, and OSM provides "
        "locality, road, stream and POI coverage for this compact sector."
    ),
}

OSM_ROAD_WAY_IDS = (101971528, 114099376, 1095906636)
OSM_CONTEXT_WAY_IDS = (234936176, 1154487446)
OSM_CONTEXT_NODE_IDS = (
    2379693646,
    2379693652,
    2379693654,
    2379693679,
    2379693686,
    2379693689,
    2379693694,
    2379693696,
    2379693735,
    2379693754,
    2379693772,
    4254488391,
    4254504794,
    4712005944,
    6066288486,
    6950253649,
    6956686347,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch and prepare the Chandrabani PRAVAHA GIS asset pack.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--downloaded-at",
        default=utc_now(),
        help="UTC timestamp recorded in the generated manifest.",
    )
    args = parser.parse_args()

    roads_osm = fetch_overpass(road_query())
    context_osm = fetch_overpass(context_query())
    terrain = fetch_terrain_grid(
        STUDY_AREA["bounding_box"],
        downloaded_at=args.downloaded_at,
    )

    asset = build_asset(
        roads_osm=roads_osm,
        context_osm=context_osm,
        terrain=terrain,
        downloaded_at=args.downloaded_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asset, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    return 0


def fetch_overpass(query: str) -> dict[str, Any]:
    errors: list[str] = []
    for endpoint in OVERPASS_URLS:
        request = Request(
            f"{endpoint}?{urlencode({'data': query})}",
            headers={
                "User-Agent": "PRAVAHA-GIS-prep/1.0",
            },
        )
        try:
            with urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network fallback path
            errors.append(f"{endpoint}: {exc}")
    raise RuntimeError("Overpass fetch failed: " + " | ".join(errors))


def road_query() -> str:
    ids = ",".join(str(item) for item in OSM_ROAD_WAY_IDS)
    return (
        "[out:json][timeout:45];"
        f"way(id:{ids});"
        "out body geom;"
    )


def context_query() -> str:
    way_ids = ",".join(str(item) for item in OSM_CONTEXT_WAY_IDS)
    node_ids = ",".join(str(item) for item in OSM_CONTEXT_NODE_IDS)
    return (
        "[out:json][timeout:45];("
        f"way(id:{way_ids});"
        f"node(id:{node_ids});"
        ");out body geom;"
    )


def fetch_terrain_grid(
    bbox: dict[str, float],
    *,
    downloaded_at: str,
) -> dict[str, Any]:
    lats = linspace(bbox["south"], bbox["north"], 5)
    lons = linspace(bbox["west"], bbox["east"], 5)
    locations = "|".join(f"{lat:.6f},{lon:.6f}" for lat in lats for lon in lons)
    url = f"{OPENTOPO_URL}?{urlencode({'locations': locations})}"
    request = Request(url, headers={"User-Agent": "PRAVAHA-GIS-prep/1.0"})
    with urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    results = payload.get("results", [])
    grid = []
    nodata_count = 0
    for result in results:
        location = result.get("location") or {}
        elevation = result.get("elevation")
        if elevation is None:
            nodata_count += 1
            continue
        grid.append(
            {
                "latitude": float(location["lat"]),
                "longitude": float(location["lng"]),
                "elevation_m": float(elevation),
            }
        )

    elevations = [point["elevation_m"] for point in grid]
    slopes = slope_samples(grid, lats=lats, lons=lons)
    mean_slope_fraction = statistics.fmean(slopes) if slopes else None
    mean_slope_deg = (
        math.degrees(math.atan(mean_slope_fraction))
        if mean_slope_fraction is not None
        else None
    )
    width_m = haversine_m(
        bbox["south"],
        bbox["west"],
        bbox["south"],
        bbox["east"],
    )
    height_m = haversine_m(
        bbox["south"],
        bbox["west"],
        bbox["north"],
        bbox["west"],
    )
    return {
        "source_id": "opentopodata_srtm30m",
        "source_name": "OpenTopoData SRTM 30m elevation API",
        "source_url": OPENTOPO_URL,
        "source_status": "OPEN_REAL_DATA",
        "derived_status": "DERIVED_FROM_REAL_DATA",
        "dataset": "SRTM 30m",
        "spatial_resolution_m": 30,
        "sample_grid": grid,
        "sample_spacing_m": {
            "east_west": round(width_m / 4.0, 1),
            "north_south": round(height_m / 4.0, 1),
        },
        "min_elevation_m": min(elevations) if elevations else None,
        "max_elevation_m": max(elevations) if elevations else None,
        "mean_elevation_m": round(statistics.fmean(elevations), 1)
        if elevations
        else None,
        "mean_slope_fraction": round(mean_slope_fraction, 4)
        if mean_slope_fraction is not None
        else None,
        "mean_slope_deg": round(mean_slope_deg, 2)
        if mean_slope_deg is not None
        else None,
        "nodata_count": nodata_count,
        "hand_m": None,
        "twi": None,
        "downloaded_at": downloaded_at,
        "processing": (
            "Queried a 5x5 SRTM 30m point grid and derived representative "
            "slope from finite elevation differences in metres."
        ),
        "limitations": (
            "This is a small sampled terrain asset for the focused demo area; "
            "it is not a committed raw DEM raster or a hydrologically filled DEM."
        ),
    }


def build_asset(
    *,
    roads_osm: dict[str, Any],
    context_osm: dict[str, Any],
    terrain: dict[str, Any],
    downloaded_at: str,
) -> dict[str, Any]:
    study_area = {
        **STUDY_AREA,
        "approx_area_km2": approx_bbox_area_km2(STUDY_AREA["bounding_box"]),
        "downloaded_at": downloaded_at,
    }
    roads = select_roads(roads_osm)
    streams = osm_features(
        context_osm,
        kinds={"way"},
        tag_filter=lambda tags: "waterway" in tags,
        entity_type="river",
        source_status="OPEN_REAL_DATA",
        max_features=4,
    )
    settlements = osm_features(
        context_osm,
        kinds={"node"},
        tag_filter=lambda tags: "place" in tags,
        entity_type="ward",
        source_status="OPEN_REAL_DATA",
        max_features=12,
    )
    critical_assets = osm_features(
        context_osm,
        kinds={"node", "way"},
        tag_filter=lambda tags: "amenity" in tags,
        entity_type="critical_asset",
        source_status="OPEN_REAL_DATA",
        max_features=10,
    )

    return {
        "schema_version": "pravaha-gis-static-v1",
        "study_area": study_area,
        "sources": sources(
            roads_osm=roads_osm,
            context_osm=context_osm,
            downloaded_at=downloaded_at,
        ),
        "terrain": terrain,
        "layers": {
            "catchments": feature_collection(
                [
                    catchment_feature(
                        study_area["bounding_box"],
                        terrain=terrain,
                    )
                ]
            ),
            "wards": feature_collection(settlements),
            "roads": feature_collection(roads),
            "rivers": feature_collection(streams),
            "drains": feature_collection([estimated_drain(streams)] if streams else []),
            "critical_assets": feature_collection(critical_assets),
            "shelters": feature_collection([demo_shelter(critical_assets)]),
            "landslide": feature_collection([demo_landslide_zone(study_area["bounding_box"])]),
        },
        "validation_points": validation_points(terrain, roads, streams, settlements),
        "limitations": [
            "Municipal storm-drain geometry and capacity are not authoritative.",
            "Ward/village polygons are not included; OSM settlement points are used.",
            "Historical landslide inventory is not available for the focused box.",
            "DEMO-001 hazards remain simulated dynamic conditions over real base geometry.",
        ],
    }


def sources(
    *,
    roads_osm: dict[str, Any],
    context_osm: dict[str, Any],
    downloaded_at: str,
) -> list[dict[str, Any]]:
    return [
        {
            "source_id": "osm_overpass",
            "source_name": "OpenStreetMap via Overpass API",
            "source_url": "https://www.openstreetmap.org/copyright",
            "license": "Open Database License (ODbL)",
            "source_status": "OPEN_REAL_DATA",
            "dataset_version": {
                "roads_timestamp_osm_base": roads_osm.get("osm3s", {}).get(
                    "timestamp_osm_base"
                ),
                "context_timestamp_osm_base": context_osm.get("osm3s", {}).get(
                    "timestamp_osm_base"
                ),
            },
            "downloaded_at": downloaded_at,
            "processing_steps": [
                "Query a bounded Chandrabani study-area extract.",
                "Convert OSM nodes/ways to EPSG:4326 GeoJSON.",
                "Assign stable PRAVAHA IDs to selected demo-critical road corridors.",
            ],
        },
        {
            "source_id": "opentopodata_srtm30m",
            "source_name": "OpenTopoData SRTM 30m elevation API",
            "source_url": OPENTOPO_URL,
            "license": "See OpenTopoData and upstream SRTM terms.",
            "source_status": "OPEN_REAL_DATA",
            "dataset_version": "SRTM 30m API endpoint",
            "downloaded_at": downloaded_at,
            "processing_steps": [
                "Sample 25 elevation points across the focused study box.",
                "Derive representative elevation statistics and slope.",
            ],
        },
    ]


def select_roads(osm: dict[str, Any]) -> list[dict[str, Any]]:
    raw = [
        feature
        for feature in osm_features(
            osm,
            kinds={"way"},
            tag_filter=lambda tags: "highway" in tags,
            entity_type="road",
            source_status="OPEN_REAL_DATA",
            max_features=8,
        )
    ]
    selected: list[dict[str, Any]] = []
    mapping = [
        ("Transport Nagar Road", "ROAD-SHELTER-CORRIDOR"),
        ("Post Office Road", "ROAD-HIGHER-GROUND-BYPASS"),
    ]
    used_ids: set[str] = set()
    for road_name, road_id in mapping:
        match = next(
            (
                feature
                for feature in raw
                if feature["properties"].get("name") == road_name
            ),
            None,
        )
        if match is not None:
            selected.append(with_id(match, road_id))
            used_ids.add(str(match["properties"]["source_osm_id"]))

    remaining = [
        feature
        for feature in raw
        if str(feature["properties"]["source_osm_id"]) not in used_ids
    ]
    if remaining:
        selected.append(with_id(remaining[0], "ROAD-BRIDGE-APPROACH"))

    for index, feature in enumerate(remaining[1:], start=1):
        selected.append(with_id(feature, f"ROAD-OSM-{index:03d}"))

    for feature in selected:
        feature["properties"]["road_verification_status"] = "OPEN_REAL_DATA"
        feature["properties"]["hazard_status_basis"] = "MODEL_RECOMMENDATION"

    return selected[:6]


def osm_features(
    osm: dict[str, Any],
    *,
    kinds: set[str],
    tag_filter,
    entity_type: str,
    source_status: str,
    max_features: int,
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for element in osm.get("elements", []):
        if element.get("type") not in kinds:
            continue
        tags = element.get("tags", {})
        if not tag_filter(tags):
            continue
        geometry = geometry_for(element)
        if geometry is None:
            continue
        osm_id = f"osm-{element['type']}-{element['id']}"
        properties = {
            "id": osm_id,
            "entityType": entity_type,
            "name": tags.get("name") or tags.get("name:en") or "Unnamed Road"
            if entity_type == "road"
            else tags.get("name") or osm_id,
            "source": "OpenStreetMap",
            "source_status": source_status,
            "source_osm_id": element["id"],
            "source_osm_type": element["type"],
            "dataset_version": osm.get("osm3s", {}).get("timestamp_osm_base"),
        }
        for key in (
            "highway",
            "waterway",
            "amenity",
            "place",
            "surface",
            "oneway",
        ):
            if key in tags:
                properties[key] = tags[key]
        features.append(
            {
                "type": "Feature",
                "id": osm_id,
                "geometry": geometry,
                "properties": properties,
            }
        )
        if len(features) >= max_features:
            break
    return features


def geometry_for(element: dict[str, Any]) -> dict[str, Any] | None:
    if element.get("type") == "node":
        return {
            "type": "Point",
            "coordinates": [float(element["lon"]), float(element["lat"])],
        }
    geometry = element.get("geometry")
    if not geometry:
        return None
    coordinates = [[float(point["lon"]), float(point["lat"])] for point in geometry]
    return {
        "type": "LineString",
        "coordinates": coordinates,
    }


def with_id(feature: dict[str, Any], feature_id: str) -> dict[str, Any]:
    updated = json.loads(json.dumps(feature))
    updated["id"] = feature_id
    updated["properties"]["id"] = feature_id
    updated["properties"]["pravaha_id"] = feature_id
    return updated


def catchment_feature(
    bbox: dict[str, float],
    *,
    terrain: dict[str, Any],
) -> dict[str, Any]:
    west, south, east, north = (
        bbox["west"],
        bbox["south"],
        bbox["east"],
        bbox["north"],
    )
    return {
        "type": "Feature",
        "id": "UK-CHM-DEHRADUN-01",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [west, south],
                    [east, south],
                    [east, north],
                    [west, north],
                    [west, south],
                ]
            ],
        },
        "properties": {
            "id": "UK-CHM-DEHRADUN-01",
            "entityType": "catchment",
            "name": "Chandrabani focused micro-catchment",
            "source_status": "ESTIMATED",
            "geometry_basis": (
                "Focused MVP micro-catchment envelope around Chandrabani; "
                "not an authoritative watershed polygon."
            ),
            "mean_elevation_m": terrain["mean_elevation_m"],
            "mean_slope_deg": terrain["mean_slope_deg"],
            "mean_slope_fraction": terrain["mean_slope_fraction"],
            "area_km2": approx_bbox_area_km2(bbox),
        },
    }


def estimated_drain(streams: list[dict[str, Any]]) -> dict[str, Any]:
    stream = streams[0]
    feature = with_id(stream, "D-22")
    feature["properties"].update(
        {
            "entityType": "drain",
            "name": "D-22 estimated municipal collector",
            "source_status": "ESTIMATED",
            "geometry_basis": (
                "Aligned to nearby OSM waterway only for demo spatial context; "
                "not a verified municipal storm-drain asset."
            ),
            "capacity_verification_status": "ESTIMATED",
        }
    )
    return feature


def demo_shelter(critical_assets: list[dict[str, Any]]) -> dict[str, Any]:
    preferred = next(
        (
            asset
            for asset in critical_assets
            if "academy" in str(asset["properties"].get("name", "")).lower()
            or asset["properties"].get("amenity") == "school"
        ),
        None,
    )
    coordinates = (
        preferred["geometry"]["coordinates"]
        if preferred is not None
        else [77.994094, 30.28497]
    )
    source_osm_id = (
        preferred["properties"].get("source_osm_id")
        if preferred is not None
        else None
    )
    return {
        "type": "Feature",
        "id": "SHELTER-SCHOOL-01",
        "geometry": {
            "type": "Point",
            "coordinates": coordinates,
        },
        "properties": {
            "id": "SHELTER-SCHOOL-01",
            "entityType": "shelter",
            "name": "Demo shelter at mapped school POI",
            "source": "OpenStreetMap POI + PRAVAHA demo designation",
            "source_status": "DEMO",
            "poi_source_status": "OPEN_REAL_DATA",
            "source_osm_id": source_osm_id,
            "designation_status": "DEMO_EVACUATION_SHELTER_NOT_AUTHORITY_VERIFIED",
            "status": "AVAILABLE",
        },
    }


def demo_landslide_zone(bbox: dict[str, float]) -> dict[str, Any]:
    west = bbox["west"] + 0.003
    east = bbox["west"] + 0.012
    south = bbox["north"] - 0.010
    north = bbox["north"] - 0.002
    return {
        "type": "Feature",
        "id": "LANDSLIDE-ZONE-S-01",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [west, south],
                    [east, south],
                    [east, north],
                    [west, north],
                    [west, south],
                ]
            ],
        },
        "properties": {
            "id": "LANDSLIDE-ZONE-S-01",
            "entityType": "landslide",
            "name": "DEMO steep-slope susceptibility zone",
            "source_status": "DEMO",
            "historical_inventory_status": "NOT_AVAILABLE",
            "basis": (
                "Retained only as DEMO-001 susceptibility fixture; no local "
                "historical landslide inventory is committed for this box."
            ),
        },
    }


def validation_points(
    terrain: dict[str, Any],
    roads: list[dict[str, Any]],
    streams: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "point_id": "VP-CHANDRABANI-LOCALITY",
            "name": "Chandrabani OSM locality point",
            "latitude": 30.285029,
            "longitude": 77.978689,
            "expected": {
                "within_study_area": True,
                "elevation_non_null": terrain["mean_elevation_m"] is not None,
                "nearest_road_available": bool(roads),
                "nearest_stream_available": bool(streams),
                "admin_context_available": bool(settlements),
            },
        },
        {
            "point_id": "VP-TRANSPORT-NAGAR-ROAD",
            "name": "Transport Nagar Road corridor",
            "latitude": 30.2854,
            "longitude": 77.9926,
            "expected": {
                "within_study_area": True,
                "nearest_road_available": True,
            },
        },
        {
            "point_id": "VP-SCHOOL-POI",
            "name": "Mapped school / demo shelter location",
            "latitude": 30.28497,
            "longitude": 77.994094,
            "expected": {
                "within_study_area": True,
                "critical_asset_available": True,
                "shelter_designation": "DEMO",
            },
        },
    ]


def feature_collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": features,
    }


def linspace(start: float, end: float, count: int) -> list[float]:
    if count < 2:
        return [start]
    step = (end - start) / (count - 1)
    return [start + step * index for index in range(count)]


def slope_samples(
    grid: list[dict[str, float]],
    *,
    lats: list[float],
    lons: list[float],
) -> list[float]:
    points = {
        (round(point["latitude"], 6), round(point["longitude"], 6)): point
        for point in grid
    }
    slopes: list[float] = []
    for row in range(1, len(lats) - 1):
        for col in range(1, len(lons) - 1):
            west = points.get((round(lats[row], 6), round(lons[col - 1], 6)))
            east = points.get((round(lats[row], 6), round(lons[col + 1], 6)))
            south = points.get((round(lats[row - 1], 6), round(lons[col], 6)))
            north = points.get((round(lats[row + 1], 6), round(lons[col], 6)))
            if not all((west, east, south, north)):
                continue
            dz_dx = (
                east["elevation_m"] - west["elevation_m"]
            ) / haversine_m(lats[row], lons[col - 1], lats[row], lons[col + 1])
            dz_dy = (
                north["elevation_m"] - south["elevation_m"]
            ) / haversine_m(lats[row - 1], lons[col], lats[row + 1], lons[col])
            slopes.append(math.sqrt(dz_dx * dz_dx + dz_dy * dz_dy))
    return slopes


def approx_bbox_area_km2(bbox: dict[str, float]) -> float:
    center_lat = (bbox["south"] + bbox["north"]) / 2.0
    width_m = haversine_m(center_lat, bbox["west"], center_lat, bbox["east"])
    height_m = haversine_m(bbox["south"], bbox["west"], bbox["north"], bbox["west"])
    return round((width_m * height_m) / 1_000_000.0, 2)


def haversine_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    return 2.0 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


if __name__ == "__main__":
    raise SystemExit(main())
