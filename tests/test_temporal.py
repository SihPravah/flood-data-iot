from datetime import datetime, timedelta, timezone
import pytest

from pravaha_data.models.observation import CanonicalObservation, Location, Measurement
from pravaha_data.models.provenance import DataStatus, DataQuality
from pravaha_data.temporal.history import TemporalHistory

def make_rain_obs(obs_time: datetime, intensity: float, status: DataStatus = DataStatus.OBSERVED, source: str = "GENERIC_GAUGE") -> CanonicalObservation:
    return CanonicalObservation(
        observation_id=f"obs_{obs_time.timestamp()}",
        source_id=source,
        source_type="RAIN_GAUGE",
        observed_at=obs_time,
        location=Location(latitude=30.12, longitude=78.45),
        measurements={
            "rainfall_intensity_mm_per_hr": Measurement(value=intensity, status=status)
        }
    )

def test_irregularly_spaced_rainfall_integration():
    """
    Test zero-order-hold integration with non-uniform intervals.
    t=0m: 12 mm/hr for 20 mins -> 12 * (20/60) = 4.0 mm
    t=20m: 6 mm/hr for 20 mins -> 6 * (20/60) = 2.0 mm
    t=40m: 0 mm/hr for 20 mins -> 0 * (20/60) = 0.0 mm
    Total 1h window = 6.0 mm.
    """
    history = TemporalHistory()
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    
    t0 = now - timedelta(minutes=60)
    t20 = now - timedelta(minutes=40)
    t40 = now - timedelta(minutes=20)
    
    history.add_observation(make_rain_obs(t0, 12.0))
    history.add_observation(make_rain_obs(t20, 6.0))
    history.add_observation(make_rain_obs(t40, 0.0))
    
    r_1h = history.get_rain_1h(as_of=now)
    assert r_1h.status == DataStatus.DERIVED
    assert r_1h.value_mm == pytest.approx(6.0, abs=0.1)
    assert r_1h.coverage_fraction >= 0.95
    assert r_1h.quality == DataQuality.GOOD

def test_complete_1h_window():
    """Observations every 10 minutes spanning a full hour yields GOOD quality."""
    history = TemporalHistory()
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    
    for mins in range(60, -1, -10):
        t = now - timedelta(minutes=mins)
        history.add_observation(make_rain_obs(t, 10.0))
        
    r_1h = history.get_rain_1h(as_of=now)
    assert r_1h.status == DataStatus.DERIVED
    assert r_1h.quality == DataQuality.GOOD
    assert r_1h.coverage_fraction == 1.0
    assert r_1h.observation_count == 7
    # 10 mm/hr held continuously for 1 hour = 10.0 mm
    assert r_1h.value_mm == pytest.approx(10.0, abs=0.1)

def test_partial_incomplete_1h_window():
    """A sparse single reading that expires creates degraded or unusable coverage."""
    history = TemporalHistory(max_hold_minutes=15.0)
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    
    # Only one reading at t - 55 mins
    t = now - timedelta(minutes=55)
    history.add_observation(make_rain_obs(t, 20.0))
    
    r_1h = history.get_rain_1h(as_of=now)
    # 15 minutes of hold out of 60 minutes = 0.25 coverage
    assert r_1h.coverage_fraction <= 0.35
    assert r_1h.quality == DataQuality.UNUSABLE
    assert r_1h.largest_gap_minutes >= 30.0

def test_24h_retention_and_pruning():
    """History retains readings within 28h and prunes older ones."""
    history = TemporalHistory(retention_hours=28)
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    
    t_fresh = now - timedelta(hours=20)
    t_boundary = now - timedelta(hours=27)
    t_expired = now - timedelta(hours=35)
    
    history.add_observation(make_rain_obs(t_fresh, 5.0))
    history.add_observation(make_rain_obs(t_boundary, 5.0))
    history.add_observation(make_rain_obs(t_expired, 5.0))
    
    history.prune(as_of=now)
    
    obs_times = [o.observed_at for o in history.observations]
    assert t_fresh in obs_times
    assert t_boundary in obs_times
    assert t_expired not in obs_times
    
    # Verify 24h window calculation works
    r_24h = history.get_rain_24h(as_of=now)
    assert r_24h.status == DataStatus.DERIVED

def test_stale_rainfall_age_calculation():
    """Verify age_minutes correctly reflects time since latest reading."""
    history = TemporalHistory()
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    
    t_stale = now - timedelta(minutes=45)
    history.add_observation(make_rain_obs(t_stale, 15.0))
    
    r_1h = history.get_rain_1h(as_of=now)
    assert r_1h.latest_observation_age_minutes == pytest.approx(45.0, abs=1.0)
    # Since latest reading is older than 30 mins, quality is not GOOD
    assert r_1h.quality != DataQuality.GOOD

def test_provider_agnostic_rainfall():
    """History works with any source, not hardcoded to OPEN_METEO."""
    history = TemporalHistory()
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    
    obs1 = make_rain_obs(now - timedelta(minutes=20), 8.0, source="IMD_RADAR")
    obs2 = make_rain_obs(now - timedelta(minutes=10), 12.0, source="LOCAL_ESP32_PULSE")
    
    history.add_observation(obs1)
    history.add_observation(obs2)
    
    r_30m = history.get_rain_30m(as_of=now)
    assert r_30m.status == DataStatus.DERIVED
    assert r_30m.observation_count == 2
    assert r_30m.value_mm is not None
