import time
from pravaha_data.adapters.open_meteo import OpenMeteoAdapter
from pravaha_data.adapters.simulated_iot import SimulatedIoTAdapter
from pravaha_data.normalization.observations import normalize_open_meteo, normalize_simulated_iot
from pravaha_data.temporal.history import TemporalHistory
from pravaha_data.fusion.catchment_fusion import fuse_catchment_state
from pravaha_data.demo.ids import DEMO_CATCHMENT_ID, DEMO_SENSOR_PRIMARY_ID

# Demo coordinates are explicit and replaceable by GIS integration.
TARGET_LAT = 30.3165
TARGET_LON = 78.0322

def run_pipeline():
    print(f"Starting PRAVAHA Data Ingestion & Fusion Engine for {DEMO_CATCHMENT_ID}...\n")
    
    # 1. Initialize Adapters & History
    weather_api = OpenMeteoAdapter(latitude=TARGET_LAT, longitude=TARGET_LON)
    iot_sensor = SimulatedIoTAdapter(device_id=DEMO_SENSOR_PRIMARY_ID, latitude=TARGET_LAT, longitude=TARGET_LON)
    history = TemporalHistory()

    try:
        while True:
            # 2. Load Sources
            raw_weather = weather_api.fetch()
            raw_iot = iot_sensor.generate_payload()
            
            # 3. Normalize
            obs_weather = normalize_open_meteo(raw_weather)
            obs_iot = normalize_simulated_iot(raw_iot)
            
            # 4. Temporal Processing
            history.add_observation(obs_weather)
            history.add_observation(obs_iot)
            
            # 5. Fusion
            fused_state = fuse_catchment_state(
                catchment_id=DEMO_CATCHMENT_ID,
                observations=[obs_weather, obs_iot],
                history=history
            )
            
            # 6. Output (Serialize with Pydantic)
            print("--- New Fused State Generated ---")
            print(fused_state.model_dump_json(indent=2))
            print("---------------------------------\n")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nIngestion Engine stopped by user.")

if __name__ == "__main__":
    run_pipeline()
