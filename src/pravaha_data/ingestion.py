import requests
import json
import time
import random
from datetime import datetime, timezone

# Target Location: Dehradun Catchment
CATCHMENT_ID = "UK-CHM-DEHRADUN-01"
LAT = 30.3165
LON = 78.0322

def get_current_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def fetch_open_meteo_data():
    """Fetches real-time precipitation and soil moisture from Open-Meteo."""
    # Fetching current precipitation and soil moisture (0-7cm depth)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=precipitation,soil_moisture_0_to_7cm"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        rain_1h_mm = current.get("precipitation", 0.0)
        
        # Open-Meteo returns soil moisture as m³/m³ (0.0 to ~0.8). 
        # We normalize it roughly to a 0-1 saturation scale.
        raw_soil = current.get("soil_moisture_0_to_7cm", 0.0)
        api_soil_saturation = min(raw_soil / 0.5, 1.0) 
        
        return rain_1h_mm, api_soil_saturation, "OBSERVED", 0.95
        
    except Exception as e:
        print(f"API Error: {e}")
        # Rule 14: Graceful degradation / Missing data handling
        return 0.0, 0.0, "MISSING", 0.0

def simulate_iot_sensor(api_soil_base):
    """Simulates a local IoT soil moisture sensor fluctuating around the API baseline."""
    # Add +/- 5% random noise to the API base to simulate a real hardware sensor
    noise = random.uniform(-0.05, 0.05)
    simulated_saturation = max(0.0, min(1.0, api_soil_base + noise))
    
    return round(simulated_saturation, 2)

def generate_fused_state():
    """Builds the canonical Fused Catchment State defined in DATA_CONTRACT.md."""
    rain_mm, api_soil, rain_status, rain_confidence = fetch_open_meteo_data()
    
    # Fuse the macro API data with our simulated micro IoT sensor
    local_soil_saturation = simulate_iot_sensor(api_soil)
    
    fused_state = {
        "catchment_id": CATCHMENT_ID,
        "state_time": get_current_utc(),
        "rainfall": {
            "rain_1h_mm": rain_mm,
            "status": rain_status,
            "confidence": rain_confidence
        },
        "soil": {
            "saturation": local_soil_saturation,
            "status": "OBSERVED" if rain_status == "OBSERVED" else "ESTIMATED",
            "confidence": 0.88 if rain_status == "OBSERVED" else 0.40,
            "age_minutes": random.randint(0, 5) # Simulating sensor ping age
        },
        "data_quality": {
            "overall_score": 0.91 if rain_status == "OBSERVED" else 0.30,
            "missing_sources": [] if rain_status == "OBSERVED" else ["open_meteo_rainfall"]
        }
    }
    
    return fused_state

if __name__ == "__main__":
    print(f"Starting PRAVAHA Data Ingestion & Fusion Engine for {CATCHMENT_ID}...\n")
    
    # Run a continuous loop simulating data arriving every 5 seconds
    try:
        while True:
            state = generate_fused_state()
            print("--- New Fused State Generated ---")
            print(json.dumps(state, indent=2))
            print("---------------------------------\n")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nIngestion Engine stopped by user.")
