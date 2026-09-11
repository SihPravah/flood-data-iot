from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from ..models.observation import CanonicalObservation
from ..models.fused_state import (
    FusedCatchmentState, 
    RainfallFeatures, 
    IntensityFeatures,
    SoilFeatures, 
    DataQualityState
)
from ..models.provenance import DataStatus, DataQuality
from ..temporal.history import TemporalHistory

STALE_THRESHOLD_MINUTES = 120.0

def _get_provenance_tier(status: DataStatus, age_minutes: float) -> float:
    """
    Assigns priority tier based on provenance and freshness:
    Fresh OBSERVED (tier 4.0) > Fresh DERIVED/ESTIMATED (tier 3.0) 
    > Fresh SIMULATED (tier 2.0) > Stale OBSERVED (tier 1.5) > Stale SIMULATED (tier 1.0) > MISSING (tier 0.0)
    """
    is_fresh = age_minutes <= STALE_THRESHOLD_MINUTES
    if status == DataStatus.OBSERVED:
        return 4.0 if is_fresh else 1.5
    elif status in (DataStatus.DERIVED, DataStatus.ESTIMATED):
        return 3.0 if is_fresh else 1.2
    elif status == DataStatus.SIMULATED:
        return 2.0 if is_fresh else 1.0
    return 0.0

def fuse_catchment_state(
    catchment_id: str, 
    observations: List[CanonicalObservation], 
    history: TemporalHistory,
    state_time: Optional[datetime] = None
) -> FusedCatchmentState:
    """
    Deterministic, provenance-aware catchment fusion.
    Independent of input list order.
    """
    if state_time is None:
        state_time = datetime.now(timezone.utc)

    # 1. Candidate Selection for Rainfall Intensity (Order-Independent)
    rain_candidates: List[Tuple[float, datetime, float, DataStatus, float]] = []
    # Candidate tuple: (tier, observed_at, value, status, age_minutes)

    for obs in observations:
        meas = obs.measurements.get("rainfall_intensity_mm_per_hr")
        if meas and meas.status != DataStatus.MISSING and meas.value is not None:
            age_min = max(0.0, (state_time - obs.observed_at).total_seconds() / 60.0)
            tier = _get_provenance_tier(meas.status, age_min)
            rain_candidates.append((tier, obs.observed_at, float(meas.value), meas.status, age_min))

    # Sort candidates by: 1) Tier descending, 2) observed_at descending
    rain_candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)

    if rain_candidates:
        _, _, best_rain_val, best_rain_status, best_rain_age = rain_candidates[0]
        rain_confidence = 0.95 if best_rain_status == DataStatus.OBSERVED else (
            0.85 if best_rain_status in (DataStatus.DERIVED, DataStatus.ESTIMATED) else 0.70
        )
        intensity_feature = IntensityFeatures(
            value=best_rain_val,
            status=best_rain_status,
            confidence=rain_confidence,
            age_minutes=round(best_rain_age, 1)
        )
    else:
        intensity_feature = IntensityFeatures(
            value=None,
            status=DataStatus.MISSING,
            confidence=0.0,
            age_minutes=None
        )

    # 2. Candidate Selection for Soil Moisture (Order-Independent)
    soil_candidates: List[Tuple[float, datetime, float, DataStatus, float]] = []
    # Tuple: (tier, observed_at, saturation, status, age_minutes)

    for obs in observations:
        age_min = max(0.0, (state_time - obs.observed_at).total_seconds() / 60.0)
        
        # Primary: direct percentage from IoT
        if "soil_moisture_percentage" in obs.measurements:
            meas = obs.measurements["soil_moisture_percentage"]
            if meas.status != DataStatus.MISSING and meas.value is not None:
                tier = _get_provenance_tier(meas.status, age_min)
                sat = max(0.0, min(1.0, float(meas.value) / 100.0))
                soil_candidates.append((tier, obs.observed_at, sat, meas.status, age_min))
                
        # Secondary fallback: volumetric water content from Open-Meteo (DERIVED)
        elif "soil_moisture_volumetric" in obs.measurements:
            meas = obs.measurements["soil_moisture_volumetric"]
            if meas.status != DataStatus.MISSING and meas.value is not None:
                # Derived volumetric conversion
                tier = _get_provenance_tier(DataStatus.DERIVED, age_min)
                sat = min(float(meas.value) / 0.5, 1.0)
                soil_candidates.append((tier, obs.observed_at, sat, DataStatus.DERIVED, age_min))

    soil_candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)

    if soil_candidates:
        _, _, best_soil_sat, best_soil_status, best_soil_age = soil_candidates[0]
        soil_conf = 0.90 if best_soil_status == DataStatus.OBSERVED else (
            0.85 if best_soil_status == DataStatus.DERIVED else 0.70
        )
        soil_feature = SoilFeatures(
            saturation=round(best_soil_sat, 3),
            status=best_soil_status,
            confidence=soil_conf,
            age_minutes=round(best_soil_age, 1)
        )
    else:
        soil_feature = SoilFeatures(
            saturation=None,
            status=DataStatus.MISSING,
            confidence=0.0,
            age_minutes=None
        )

    # 3. Accumulated Rainfall Windows from History
    r_15m = history.get_rain_15m(as_of=state_time)
    r_30m = history.get_rain_30m(as_of=state_time)
    r_1h = history.get_rain_1h(as_of=state_time)
    r_3h = history.get_rain_3h(as_of=state_time)
    r_6h = history.get_rain_6h(as_of=state_time)
    r_24h = history.get_rain_24h(as_of=state_time)

    rainfall_state = RainfallFeatures(
        intensity=intensity_feature,
        rain_15m=r_15m,
        rain_30m=r_30m,
        rain_1h=r_1h,
        rain_3h=r_3h,
        rain_6h=r_6h,
        rain_24h=r_24h
    )

    # 4. Multi-Factor Data Quality Scoring (Development Policy)
    missing_sources = []
    penalties = 0.0

    # Missingness
    if intensity_feature.status == DataStatus.MISSING:
        missing_sources.append("rainfall_intensity")
        penalties += 0.30
    if soil_feature.status == DataStatus.MISSING:
        missing_sources.append("soil_moisture")
        penalties += 0.30

    # Provenance penalties (SIMULATED is not production authoritative)
    if intensity_feature.status == DataStatus.SIMULATED:
        penalties += 0.10
    if soil_feature.status == DataStatus.SIMULATED:
        penalties += 0.10

    # Freshness penalties
    if intensity_feature.age_minutes is not None:
        if intensity_feature.age_minutes > 60.0:
            penalties += 0.20
        elif intensity_feature.age_minutes > 30.0:
            penalties += 0.10

    if soil_feature.age_minutes is not None:
        if soil_feature.age_minutes > 60.0:
            penalties += 0.15
        elif soil_feature.age_minutes > 30.0:
            penalties += 0.08

    # Rainfall window completeness penalty
    if r_1h.quality == DataQuality.DEGRADED:
        penalties += 0.08
    elif r_1h.quality == DataQuality.UNUSABLE:
        penalties += 0.15

    overall_score = round(max(0.0, min(1.0, 1.0 - penalties)), 2)

    # Temporal freshness classification
    max_age = max(
        intensity_feature.age_minutes or 999.0,
        soil_feature.age_minutes or 999.0
    )
    if max_age <= 15.0:
        freshness = DataQuality.GOOD
    elif max_age <= 60.0:
        freshness = DataQuality.DEGRADED
    else:
        freshness = DataQuality.UNUSABLE

    data_quality = DataQualityState(
        overall_score=overall_score,
        missing_sources=missing_sources,
        temporal_freshness=freshness
    )

    return FusedCatchmentState(
        catchment_id=catchment_id,
        state_time=state_time,
        rainfall=rainfall_state,
        soil=soil_feature,
        data_quality=data_quality
    )
