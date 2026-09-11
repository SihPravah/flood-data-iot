from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Tuple
from ..models.observation import CanonicalObservation
from ..models.provenance import DataStatus, DataQuality
from ..models.fused_state import RainWindowFeatures

# Retention settings: keep 24 hours + 4 hours safety margin = 28 hours
DEFAULT_RETENTION_HOURS = 28
# Maximum duration an intensity reading can be held forward if no subsequent reading arrives
DEFAULT_MAX_HOLD_MINUTES = 60.0

class TemporalHistory:
    def __init__(self, retention_hours: float = DEFAULT_RETENTION_HOURS, max_hold_minutes: float = DEFAULT_MAX_HOLD_MINUTES):
        self.observations: List[CanonicalObservation] = []
        self.retention_hours = retention_hours
        self.max_hold_minutes = max_hold_minutes

    def add_observation(self, obs: CanonicalObservation):
        """Add a canonical observation and prune records older than retention window."""
        self.observations.append(obs)
        self.prune()

    def prune(self, as_of: Optional[datetime] = None):
        """Prune observations older than retention period."""
        if as_of is None:
            as_of = datetime.now(timezone.utc)
        cutoff = as_of - timedelta(hours=self.retention_hours)
        self.observations = [o for o in self.observations if o.observed_at >= cutoff]

    def _get_rainfall_observations(self) -> List[Tuple[datetime, float, DataStatus]]:
        """
        Extract and sort all valid rainfall intensity measurements.
        Provider-agnostic: looks for rainfall_intensity_mm_per_hr in measurements.
        """
        rain_obs: List[Tuple[datetime, float, DataStatus]] = []
        for o in self.observations:
            meas = o.measurements.get("rainfall_intensity_mm_per_hr")
            if meas and meas.value is not None and meas.status != DataStatus.MISSING:
                rain_obs.append((o.observed_at, float(meas.value), meas.status))
        rain_obs.sort(key=lambda x: x[0])
        return rain_obs

    def get_rain_accumulation(
        self, 
        window: timedelta, 
        as_of: Optional[datetime] = None
    ) -> RainWindowFeatures:
        """
        Calculates accumulated rainfall using Zero-Order Hold (ZOH) numerical integration.
        Tracks coverage, gaps, age, and assigns quality (GOOD, DEGRADED, UNUSABLE).
        """
        if as_of is None:
            as_of = datetime.now(timezone.utc)

        t_end = as_of
        t_start = as_of - window
        window_seconds = window.total_seconds()
        if window_seconds <= 0:
            return RainWindowFeatures(
                value_mm=0.0,
                status=DataStatus.DERIVED,
                coverage_fraction=1.0,
                largest_gap_minutes=0.0,
                latest_observation_age_minutes=0.0,
                observation_count=0,
                quality=DataQuality.GOOD
            )

        all_rain = self._get_rainfall_observations()

        if not all_rain:
            return RainWindowFeatures(
                value_mm=None,
                status=DataStatus.MISSING,
                coverage_fraction=0.0,
                largest_gap_minutes=round(window_seconds / 60.0, 1),
                latest_observation_age_minutes=None,
                observation_count=0,
                quality=DataQuality.UNUSABLE
            )

        # Count observations strictly within the window
        obs_in_window = [x for x in all_rain if t_start <= x[0] <= t_end]
        observation_count = len(obs_in_window)

        # Relevant observations: all within window plus the latest observation prior to t_start (if any)
        prior_obs = [x for x in all_rain if x[0] < t_start]
        relevant: List[Tuple[datetime, float, DataStatus]] = []
        if prior_obs:
            relevant.append(prior_obs[-1])
        relevant.extend([x for x in all_rain if t_start <= x[0] <= t_end])

        # Latest observation age relative to t_end
        latest_obs_time = all_rain[-1][0]
        latest_age_minutes = max(0.0, (t_end - latest_obs_time).total_seconds() / 60.0)

        # Perform Zero-Order Hold (ZOH) integration across the window
        total_rain_mm = 0.0
        covered_seconds = 0.0
        covered_intervals: List[Tuple[datetime, datetime]] = []

        max_hold_delta = timedelta(minutes=self.max_hold_minutes)

        for i, (t_obs, intensity, _) in enumerate(relevant):
            # The interval that this observation's intensity holds for:
            interval_start = max(t_obs, t_start)
            
            if i + 1 < len(relevant):
                # Next observation determines end of hold, capped by max_hold_delta
                next_t = relevant[i + 1][0]
                interval_end = min(next_t, t_obs + max_hold_delta, t_end)
            else:
                # Last relevant observation holds forward up to max_hold_delta or t_end
                interval_end = min(t_obs + max_hold_delta, t_end)

            if interval_end > interval_start:
                duration_sec = (interval_end - interval_start).total_seconds()
                duration_hrs = duration_sec / 3600.0
                total_rain_mm += intensity * duration_hrs
                covered_seconds += duration_sec
                covered_intervals.append((interval_start, interval_end))

        # Calculate coverage fraction
        coverage_fraction = min(1.0, max(0.0, covered_seconds / window_seconds))

        # Calculate largest gap in minutes within [t_start, t_end]
        # Merge overlapping/adjacent covered intervals
        covered_intervals.sort(key=lambda x: x[0])
        merged: List[Tuple[datetime, datetime]] = []
        for start, end in covered_intervals:
            if not merged:
                merged.append((start, end))
            else:
                prev_start, prev_end = merged[-1]
                if start <= prev_end:
                    merged[-1] = (prev_start, max(prev_end, end))
                else:
                    merged.append((start, end))

        # Compute gaps
        gaps_sec: List[float] = []
        curr = t_start
        for start, end in merged:
            if start > curr:
                gaps_sec.append((start - curr).total_seconds())
            curr = max(curr, end)
        if curr < t_end:
            gaps_sec.append((t_end - curr).total_seconds())

        largest_gap_min = max(gaps_sec) / 60.0 if gaps_sec else 0.0

        # Determine Quality
        # Policy:
        # GOOD: >= 80% coverage and largest gap <= 30 mins (or window length if window <= 30m) and latest age <= 30 mins
        # DEGRADED: >= 40% coverage
        # UNUSABLE: < 40% coverage or largest gap occupies majority of window
        threshold_gap = min(30.0, window_seconds / 60.0)
        if coverage_fraction >= 0.80 and largest_gap_min <= max(threshold_gap, 15.0) and latest_age_minutes <= 30.0:
            quality = DataQuality.GOOD
        elif coverage_fraction >= 0.40:
            quality = DataQuality.DEGRADED
        else:
            quality = DataQuality.UNUSABLE

        # If coverage is too low (< 20%) or quality unusable with no readings, mark MISSING
        if coverage_fraction < 0.20 and observation_count == 0:
            return RainWindowFeatures(
                value_mm=None,
                status=DataStatus.MISSING,
                coverage_fraction=round(coverage_fraction, 2),
                largest_gap_minutes=round(largest_gap_min, 1),
                latest_observation_age_minutes=round(latest_age_minutes, 1) if latest_age_minutes is not None else None,
                observation_count=observation_count,
                quality=DataQuality.UNUSABLE
            )

        return RainWindowFeatures(
            value_mm=round(total_rain_mm, 2),
            status=DataStatus.DERIVED,
            coverage_fraction=round(coverage_fraction, 2),
            largest_gap_minutes=round(largest_gap_min, 1),
            latest_observation_age_minutes=round(latest_age_minutes, 1) if latest_age_minutes is not None else None,
            observation_count=observation_count,
            quality=quality
        )

    # Convenience methods for ML-required rainfall windows
    def get_rain_15m(self, as_of: Optional[datetime] = None) -> RainWindowFeatures:
        return self.get_rain_accumulation(timedelta(minutes=15), as_of=as_of)

    def get_rain_30m(self, as_of: Optional[datetime] = None) -> RainWindowFeatures:
        return self.get_rain_accumulation(timedelta(minutes=30), as_of=as_of)

    def get_rain_1h(self, as_of: Optional[datetime] = None) -> RainWindowFeatures:
        return self.get_rain_accumulation(timedelta(hours=1), as_of=as_of)

    def get_rain_3h(self, as_of: Optional[datetime] = None) -> RainWindowFeatures:
        return self.get_rain_accumulation(timedelta(hours=3), as_of=as_of)

    def get_rain_6h(self, as_of: Optional[datetime] = None) -> RainWindowFeatures:
        return self.get_rain_accumulation(timedelta(hours=6), as_of=as_of)

    def get_rain_24h(self, as_of: Optional[datetime] = None) -> RainWindowFeatures:
        return self.get_rain_accumulation(timedelta(hours=24), as_of=as_of)
