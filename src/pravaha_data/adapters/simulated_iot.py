import random
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

class SimulatedIoTAdapter:
    def __init__(self, device_id: str, latitude: float, longitude: float):
        self.device_id = device_id
        self.latitude = latitude
        self.longitude = longitude

    def generate_payload(self) -> Dict[str, Any]:
        return {
            "source_id": self.device_id,
            "source_type": "IOT_SENSOR",
            "observed_at": datetime.now(timezone.utc),
            "location": {
                "lat": self.latitude,
                "lon": self.longitude
            },
            "raw_measurements": {
                "soil_moisture_percentage": random.uniform(50.0, 90.0),
                "slope_tilt_degrees": random.uniform(0.0, 5.0)
            }
        }
