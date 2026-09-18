# SIH Demo Script

This script demonstrates PRAVAHA for PS 26192 in approximately 5-7 minutes.
It is written for a local SIH review machine.

## Preflight

Use Python 3.11 repo-local environments.

```powershell
cd D:\pravaha\flood-data-iot
.\.venv\Scripts\python.exe -m pytest -v

cd D:\pravaha\flood-ml
.\.venv\Scripts\python.exe -m pytest -v

cd D:\pravaha\flood-backend
.\.venv\Scripts\python.exe -m pytest -v

cd D:\pravaha\flood-frontend
pnpm run typecheck
pnpm run lint
pnpm test -- --run
pnpm run build
```

## Run Locally

Start Backend:

```powershell
cd D:\pravaha\flood-backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start Frontend in API mode:

```powershell
cd D:\pravaha\flood-frontend
$env:VITE_PRAVAHA_DATA_MODE="api"
$env:VITE_PRAVAHA_API_BASE_URL="http://127.0.0.1:8000"
$env:VITE_PRAVAHA_REFRESH_INTERVAL_MS="10000"
pnpm run dev
```

Open the Vite URL, normally `http://localhost:5173` or
`http://localhost:5174`.

## Segment 1 - Live Source Health

Show the source-health control in the top bar and open the source-health
drawer. Explain:

- PRAVAHA separates `OBSERVED`, `DERIVED`, `ESTIMATED`, `SIMULATED`, and
  `MISSING`.
- Demo data is visibly labelled `SIMULATED / DEMO`.
- A live external source is available through Data/IoT Open-Meteo ingestion,
  but the fully live operational ML service is still partial.

Optional live source check:

```powershell
cd D:\pravaha\flood-data-iot
.\.venv\Scripts\python.exe -c "from pravaha_data.services.catchment_state import CatchmentStateService; from pravaha_data.gis.catchments import DemoCatchmentAssigner; svc=CatchmentStateService(assigner=DemoCatchmentAssigner.dehradun_demo(), demo_mode=False); cid, obs=svc.ingest_open_meteo(latitude=30.329, longitude=78.039, timeout_seconds=10); state=svc.get_fused_catchment_state(cid, as_of=obs.observed_at); print(cid); print(state.rainfall.intensity.model_dump(mode='json')); print(state.soil.model_dump(mode='json')); print(state.data_quality.model_dump(mode='json'))"
```

## Segment 2 - Hyper-Local Map

Show the map-first command center.

Inspect:

- catchment `UK-CHM-DEHRADUN-01`
- ward `WARD-DEHRADUN-07`
- village `VILLAGE-CHANDRABANI`
- drain `D-22`
- road `ROAD-SHELTER-CORRIDOR`
- sensor `SENSOR-SIM-RAIN-SOIL-01`

Explain that the current committed GIS is deterministic demo/static context,
not authoritative municipal GIS.

## Segment 3 - IoT Event Changes State

Record the current snapshot ID from the top bar or map response:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/map/intelligence |
  Select-Object snapshot_id, generated_at
```

Publish a low-risk sensor event:

```powershell
cd D:\pravaha\flood-backend
.\.venv\Scripts\python.exe scripts\publish_sensor_event.py --device UK-SNS-00127 --rainfall 4 --soil 0.34 --lat 30.329 --lon 78.039 --observed-at 2026-09-09T08:00:00Z --received-at 2026-09-09T08:00:00Z
```

Then publish a worsening event:

```powershell
.\.venv\Scripts\python.exe scripts\publish_sensor_event.py --device UK-SNS-00127 --rainfall 48 --soil 0.82 --lat 30.329 --lon 78.039 --observed-at 2026-09-09T09:00:00Z --received-at 2026-09-09T09:00:00Z
```

Show that Backend now returns a different latest snapshot without using a
frontend-only shortcut:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/map/intelligence |
  Select-Object snapshot_id, data_label, city, model_metadata
```

Frontend API mode should update on the next poll.

## Segment 4 - DEMO-001 Disaster Progression

Publish a severe event:

```powershell
.\.venv\Scripts\python.exe scripts\publish_sensor_event.py --device UK-SNS-00127 --rainfall 72 --soil 0.96 --lat 30.329 --lon 78.039 --observed-at 2026-09-09T09:30:00Z --received-at 2026-09-09T09:30:00Z
```

Show:

- rainfall intensity and accumulation windows
- soil saturation
- runoff and discharge
- catchment risk rising to `SEVERE`
- anticipation threshold window
- landslide susceptibility
- D-22 drain overload
- road `ROAD-SHELTER-CORRIDOR` becoming `AVOID`
- `ROAD-BRIDGE-APPROACH` remaining distinct as authority `CLOSED`
- ward/village impact

## Segment 5 - Route Re-Evaluation

Request a route to the shelter:

```powershell
$body = @{
  origin = @{ lon = 78.03; lat = 30.32 }
  destination = @{ lon = 78.056; lat = 30.338; place_id = "SHELTER-SCHOOL-01" }
  strategy = "safest"
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/routes/safe -ContentType "application/json" -Body $body
```

Show the selected higher-ground bypass and explain that PRAVAHA does not
guarantee route safety.

Then show a no-route case:

```powershell
$body = @{
  origin = @{ lon = 78.03; lat = 30.32 }
  destination = @{ lon = 78.055; lat = 30.342; place_id = "DEMO-NO-SAFE-ROUTE" }
  strategy = "safest"
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/routes/safe -ContentType "application/json" -Body $body
```

Expected frontend wording:

```text
NO RELIABLE ROUTE AVAILABLE
```

## Segment 6 - Source Failure and Confidence

Switch to or publish the severe stage and inspect source health.

Expected:

- secondary hillside sensor is `UNAVAILABLE`
- provenance is `MISSING`
- freshness is `UNUSABLE`
- confidence decreases
- risk remains elevated and is not converted to LOW

## Segment 7 - Close

End with the operator-facing point:

PRAVAHA is decision support. It explains risk, confidence, provenance,
freshness, likely deterioration, infrastructure impact, and route alternatives.
It does not replace official evacuation orders or guarantee safe passage.
