from pravaha_data.gis.study_area import (
    layer,
    source_manifest,
    study_area,
    study_area_bbox,
    terrain_summary,
    validation_points,
)


def test_study_area_is_focused_chandrabani_extent():
    area = study_area()
    bbox = study_area_bbox()

    assert area["study_area_id"] == "DEHRADUN-CHANDRABANI-PS26192"
    assert area["public_crs"] == "EPSG:4326"
    assert area["metric_crs"] == "EPSG:32643"
    assert 30.27 <= area["center"]["latitude"] <= 30.30
    assert 77.968 <= area["center"]["longitude"] <= 78.0
    assert bbox == {
        "west": 77.968,
        "south": 30.27,
        "east": 78.0,
        "north": 30.3,
    }


def test_geojson_uses_longitude_latitude_order():
    roads = layer("roads")
    coordinate = roads["features"][0]["geometry"]["coordinates"][0]

    assert coordinate[0] > 70.0
    assert coordinate[1] < 40.0


def test_terrain_grid_has_srtm_values_and_no_nodata():
    terrain = terrain_summary()

    assert terrain["source_status"] == "OPEN_REAL_DATA"
    assert terrain["derived_status"] == "DERIVED_FROM_REAL_DATA"
    assert terrain["spatial_resolution_m"] == 30
    assert terrain["nodata_count"] == 0
    assert terrain["min_elevation_m"] <= terrain["mean_elevation_m"]
    assert terrain["max_elevation_m"] >= terrain["mean_elevation_m"]
    assert terrain["mean_slope_deg"] is not None


def test_static_gis_metadata_keeps_demo_and_real_separate():
    roads = layer("roads")["features"]
    shelter = layer("shelters")["features"][0]
    landslide = layer("landslide")["features"][0]

    assert all(
        road["properties"]["source_status"] == "OPEN_REAL_DATA"
        for road in roads
    )
    assert shelter["properties"]["poi_source_status"] == "OPEN_REAL_DATA"
    assert shelter["properties"]["source_status"] == "DEMO"
    assert landslide["properties"]["source_status"] == "DEMO"
    assert landslide["properties"]["historical_inventory_status"] == "NOT_AVAILABLE"


def test_validation_points_record_golden_gis_expectations():
    points = validation_points()

    assert len(points) == 3
    assert points[0]["expected"]["within_study_area"] is True
    assert points[0]["expected"]["nearest_road_available"] is True
    assert points[0]["expected"]["nearest_stream_available"] is True


def test_source_manifest_documents_osm_and_srtm():
    sources = {source["source_id"]: source for source in source_manifest()}

    assert sources["osm_overpass"]["source_status"] == "OPEN_REAL_DATA"
    assert "ODbL" in sources["osm_overpass"]["license"]
    assert sources["opentopodata_srtm30m"]["source_status"] == "OPEN_REAL_DATA"
