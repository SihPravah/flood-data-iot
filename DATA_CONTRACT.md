# System Data Contracts (SIH PS 192)

This document defines the exact JSON structures that will be passed between our simulated IoT sensors, our backend API, our ML engine, and the frontend dashboard. 

**Endpoint:** `POST /api/v1/ingest/sensors`
```json
{
  "device_id": "SIM_NODE_04",
  "timestamp": "2026-08-30T14:30:00Z",
  "location": {
    "village": "Munnar",
    "ward": "Ward_3",
    "latitude": 10.0889,
    "longitude": 77.0595
  },
  "sensor_metrics": {
    "rainfall_mm_per_hr": 45.5,
    "soil_moisture_percentage": 82.0,
    "slope_tilt_degrees": 12.2
  }
}

