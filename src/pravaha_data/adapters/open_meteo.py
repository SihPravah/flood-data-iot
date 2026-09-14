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
        try:
            response = requests.get(self.url, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
            
            return {
                "source_id": "OPEN_METEO",
                "source_type": "API",
                "observed_at": datetime.now(timezone.utc),
                "measurement_status": "OBSERVED",
                "error": None,
                "location": {
                    "lat": self.latitude,
                    "lon": self.longitude
                },
                "raw_measurements": data.get("current", {})
            }
        except Exception as e:
            if self.demo_mode and self.demo_fallback_measurements is not None:
                return {
                    "source_id": "OPEN_METEO_DEMO_FALLBACK",
                    "source_type": "API_DEMO_FALLBACK",
                    "observed_at": datetime.now(timezone.utc),
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
                "observed_at": datetime.now(timezone.utc),
                "measurement_status": "MISSING",
                "error": str(e),
                "location": {
                    "lat": self.latitude,
                    "lon": self.longitude
                },
                "raw_measurements": None
            }
