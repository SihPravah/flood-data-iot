import random
from datetime import datetime, timezone
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

    def generate_raw_sensor_payload(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc),
            "location": {
                "village": "Demo Village",
                "ward": "Demo Ward",
                "lat": self.latitude,
                "lon": self.longitude,
            },
            "sensor_metrics": {
                "rainfall_mm_per_hr": random.uniform(0.0, 20.0),
                "soil_moisture_percentage": random.uniform(50.0, 90.0),
                "slope_tilt_degrees": random.uniform(0.0, 5.0),
            },
        }
