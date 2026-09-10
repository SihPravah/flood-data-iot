import requests
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

class OpenMeteoAdapter:
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        self.url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current=precipitation,soil_moisture_0_to_7cm"

    def fetch(self) -> Dict[str, Any]:
        try:
            response = requests.get(self.url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            return {
                "source_id": "OPEN_METEO",
                "source_type": "API",
                "observed_at": datetime.now(timezone.utc),
                "location": {
                    "lat": self.latitude,
                    "lon": self.longitude
                },
                "raw_measurements": data.get("current", {})
            }
        except Exception as e:
            return {
                "source_id": "OPEN_METEO",
                "source_type": "API",
                "observed_at": datetime.now(timezone.utc),
                "location": {
                    "lat": self.latitude,
                    "lon": self.longitude
                },
                "raw_measurements": None
            }
