import requests
from datetime import datetime, timezone
from typing import Dict, Any

class OpenMeteoAdapter:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        *,
        timeout_seconds: float = 5.0,
        demo_mode: bool = False,
        demo_fallback_measurements: Dict[str, Any] | None = None,
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.timeout_seconds = timeout_seconds
        self.demo_mode = demo_mode
        self.demo_fallback_measurements = demo_fallback_measurements
        self.url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current=precipitation,soil_moisture_0_to_7cm"

    def fetch(self) -> Dict[str, Any]:
        received_at = datetime.now(timezone.utc)
        try:
            response = requests.get(self.url, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
            current = data.get("current") or {}
            observed_at = _parse_open_meteo_time(
                current.get("time"),
                fallback=received_at,
            )
            
            return {
                "source_id": "OPEN_METEO",
                "source_type": "API",
                "observed_at": observed_at,
                "received_at": received_at,
                "measurement_status": "OBSERVED",
                "error": None,
                "location": {
                    "lat": self.latitude,
                    "lon": self.longitude
                },
                "raw_measurements": current
            }
        except Exception as e:
            if self.demo_mode and self.demo_fallback_measurements is not None:
                return {
                    "source_id": "OPEN_METEO_DEMO_FALLBACK",
                    "source_type": "API_DEMO_FALLBACK",
                    "observed_at": received_at,
                    "received_at": received_at,
                    "measurement_status": "SIMULATED",
                    "error": str(e),
                    "location": {
                        "lat": self.latitude,
                        "lon": self.longitude
                    },
                    "raw_measurements": self.demo_fallback_measurements
                }

            return {
                "source_id": "OPEN_METEO",
                "source_type": "API",
                "observed_at": received_at,
                "received_at": received_at,
                "measurement_status": "MISSING",
                "error": str(e),
                "location": {
                    "lat": self.latitude,
                    "lon": self.longitude
                },
                "raw_measurements": None
            }


def _parse_open_meteo_time(
    value: Any,
    *,
    fallback: datetime,
) -> datetime:
    if not isinstance(value, str) or not value:
        return fallback

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
