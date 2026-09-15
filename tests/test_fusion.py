from datetime import datetime, timedelta, timezone
import pytest

from pravaha_data.models.observation import CanonicalObservation, Location, Measurement
from pravaha_data.models.provenance import DataStatus, DataQuality
from pravaha_data.demo.ids import DEMO_SENSOR_PRIMARY_ID, DEMO_SENSOR_SECONDARY_ID
from pravaha_data.temporal.history import TemporalHistory
from pravaha_data.fusion.catchment_fusion import fuse_catchment_state

def make_obs(obs_time: datetime, measurements: dict, source_id: str = "SRC_1") -> CanonicalObservation:
    return CanonicalObservation(
        observation_id=f"obs_{obs_time.timestamp()}_{source_id}",
        source_id=source_id,
        source_type="DEVICE",
        observed_at=obs_time,
        location=Location(latitude=30.12, longitude=78.45),
        measurements=measurements
    )

def test_order_independence_of_candidate_selection():
    """Fusion output must be identical regardless of the order of observations in the list."""
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    t_old = now - timedelta(minutes=10)
    t_new = now - timedelta(minutes=2)
    
    obs_old = make_obs(t_old, {
        "rainfall_intensity_mm_per_hr": Measurement(value=5.0, status=DataStatus.OBSERVED),
        "soil_moisture_percentage": Measurement(value=50.0, status=DataStatus.OBSERVED)
    }, source_id="OLD_STATION")
    
    obs_new = make_obs(t_new, {
        "rainfall_intensity_mm_per_hr": Measurement(value=15.0, status=DataStatus.OBSERVED),
        "soil_moisture_percentage": Measurement(value=80.0, status=DataStatus.OBSERVED)
    }, source_id="NEW_STATION")
    
    history1 = TemporalHistory()
    history2 = TemporalHistory()
    
    # Order 1: [old, new]
    res1 = fuse_catchment_state("CAT_01", [obs_old, obs_new], history1, state_time=now)
    # Order 2: [new, old]
    res2 = fuse_catchment_state("CAT_01", [obs_new, obs_old], history2, state_time=now)
    
    assert res1.rainfall.intensity.value == res2.rainfall.intensity.value == 15.0
    assert res1.soil.saturation == res2.soil.saturation == 0.80
    assert res1.rainfall.intensity.age_minutes == res2.rainfall.intensity.age_minutes == 2.0
    assert res1.soil.age_minutes == res2.soil.age_minutes == 2.0

def test_observed_preferred_over_simulated():
    """A fresh OBSERVED reading must win over a SIMULATED reading, even if SIMULATED is slightly newer."""
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    
    obs_observed = make_obs(now - timedelta(minutes=5), {
        "rainfall_intensity_mm_per_hr": Measurement(value=12.0, status=DataStatus.OBSERVED)
    }, source_id="REAL_RADAR")
    
    obs_simulated = make_obs(now - timedelta(minutes=1), {
        "rainfall_intensity_mm_per_hr": Measurement(value=99.0, status=DataStatus.SIMULATED)
    }, source_id=DEMO_SENSOR_PRIMARY_ID)
    
    history = TemporalHistory()
    
    # Pass simulated second to verify it doesn't overwrite observed
    res = fuse_catchment_state("CAT_01", [obs_observed, obs_simulated], history, state_time=now)
    assert res.rainfall.intensity.value == 12.0
    assert res.rainfall.intensity.status == DataStatus.OBSERVED

def test_simulated_preserved():
    """SIMULATED status must never be converted to OBSERVED."""
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    
    obs_sim = make_obs(now - timedelta(minutes=3), {
        "soil_moisture_percentage": Measurement(value=75.0, status=DataStatus.SIMULATED)
    }, source_id=DEMO_SENSOR_SECONDARY_ID)
    
    history = TemporalHistory()
    res = fuse_catchment_state("CAT_01", [obs_sim], history, state_time=now)
    
    assert res.soil.status == DataStatus.SIMULATED
    assert res.soil.saturation == 0.75

def test_soil_age_calculation():
    """Soil age_minutes must be dynamically calculated as state_time - observed_at."""
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    t_obs = now - timedelta(minutes=14, seconds=30)
    
    obs = make_obs(t_obs, {
        "soil_moisture_percentage": Measurement(value=60.0, status=DataStatus.SIMULATED)
    })
    
    history = TemporalHistory()
    res = fuse_catchment_state("CAT_01", [obs], history, state_time=now)
    
    assert res.soil.age_minutes == pytest.approx(14.5, abs=0.2)

def test_missing_data_handling():
    """When sources are absent, status must be MISSING, values None, and null age."""
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    history = TemporalHistory()
    
    res = fuse_catchment_state("CAT_01", [], history, state_time=now)
    
    assert res.rainfall.intensity.status == DataStatus.MISSING
    assert res.rainfall.intensity.value is None
    assert res.rainfall.intensity.age_minutes is None
    
    assert res.soil.status == DataStatus.MISSING
    assert res.soil.saturation is None
    assert res.soil.age_minutes is None
    
    assert "rainfall_intensity" in res.data_quality.missing_sources
    assert "soil_moisture" in res.data_quality.missing_sources
    assert res.data_quality.overall_score <= 0.50
    assert res.data_quality.temporal_freshness == DataQuality.UNUSABLE

def test_rainfall_window_provenance_is_derived():
    """Even when intensity is OBSERVED, window accumulations must remain DERIVED."""
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    history = TemporalHistory()
    
    obs = make_obs(now - timedelta(minutes=5), {
        "rainfall_intensity_mm_per_hr": Measurement(value=10.0, status=DataStatus.OBSERVED)
    })
    history.add_observation(obs, as_of=now)
    
    res = fuse_catchment_state("CAT_01", [obs], history, state_time=now)
    
    assert res.rainfall.intensity.status == DataStatus.OBSERVED
    assert res.rainfall.rain_15m.status == DataStatus.DERIVED
    assert res.rainfall.rain_1h.status == DataStatus.DERIVED
    assert res.rainfall.rain_24h.status == DataStatus.DERIVED
