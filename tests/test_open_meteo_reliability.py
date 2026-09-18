from pravaha_data.adapters.open_meteo import OpenMeteoAdapter
from pravaha_data.models.provenance import DataStatus
from pravaha_data.normalization.observations import normalize_open_meteo


class FailingResponse:
    def raise_for_status(self):
        raise RuntimeError("upstream unavailable")


def test_open_meteo_operational_failure_returns_missing_not_simulated(monkeypatch):
    def fail_get(*args, **kwargs):
        return FailingResponse()

    monkeypatch.setattr("requests.get", fail_get)

    raw = OpenMeteoAdapter(30.3165, 78.0322, timeout_seconds=0.1).fetch()
    observation = normalize_open_meteo(raw)

    assert raw["raw_measurements"] is None
    assert raw["measurement_status"] == "MISSING"
    assert (
        observation.measurements["rainfall_intensity_mm_per_hr"].status
        == DataStatus.MISSING
    )


def test_open_meteo_demo_fallback_is_explicitly_simulated(monkeypatch):
    def fail_get(*args, **kwargs):
        return FailingResponse()

    monkeypatch.setattr("requests.get", fail_get)

    raw = OpenMeteoAdapter(
        30.3165,
        78.0322,
        timeout_seconds=0.1,
        demo_mode=True,
        demo_fallback_measurements={
            "precipitation": 8.0,
            "soil_moisture_0_to_7cm": 0.24,
        },
    ).fetch()
    observation = normalize_open_meteo(raw)

    assert raw["source_id"] == "OPEN_METEO_DEMO_FALLBACK"
    assert raw["measurement_status"] == "SIMULATED"
    assert (
        observation.measurements["rainfall_intensity_mm_per_hr"].status
        == DataStatus.SIMULATED
    )
    assert observation.measurements["soil_moisture_volumetric"].status == DataStatus.SIMULATED
