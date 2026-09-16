\# PRAVAHA — IoT \& Data Ingestion Pipeline



\*\*Team Vmax | Smart India Hackathon 2026\*\*



Repository: `flood-data-iot`



PRAVAHA's foundational data ingestion and event-time fusion engine for a flash flood prediction architecture in hilly regions.



\---



\## Problem Statement



\*\*Problem ID 26192: Flash Flood Prediction System for Hilly Regions using Multi-Source Data\*\*



\- Current disaster management relies heavily on district-scale warnings and manual responses, which lack hyper-local context.

\- Responders need actionable intelligence to understand the hazard cascade — how rainfall intensity converts to soil saturation, surface runoff, and eventual infrastructure failure.



\## What We Have Built



PRAVAHA is a catchment-aware decision-intelligence layer designed to answer \*\*"What should we do next?"\*\* rather than just issuing warnings. This repository handles the critical first step: gathering and making sense of the chaos.



\- \*\*Multi-Source Fusion\*\* — Ingests and normalizes data from IMD forecasts, live IoT sensors, soil moisture data, digital elevation models (DEM), and landslide inventories.

\- \*\*Temporal Processing\*\* — Calculates dynamic rainfall windows (15m, 30m, 1h, 3h, 6h, 24h) to build a constantly updating "Fused Catchment State".

\- \*\*Graceful Degradation\*\* — Explicitly tracks source health, data freshness, and provenance, ensuring that a broken sensor or missing data is never falsely interpreted as "zero risk".



\## Features \& Tech Stack



This service focuses entirely on backend data ingestion and contracts.



| Feature                   | Description                                                                                                                         |

| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |

| \*\*Live \& Demo Modes\*\*     | Live-source adapters for real-time weather ingestion, alongside a deterministic simulated IoT mode for reproducible judging at SIH. |

| \*\*Strict Data Contracts\*\* | Python + Pydantic enforce rigorous data validation and maintain clean service boundaries.                                           |

| \*\*API Delivery\*\*          | Powers the downstream hydrology and ML engines (FastAPI backend) to ultimately serve the MapLibre/React command center.             |

| \*\*Scalability\*\*           | Modular pipeline design — a physical gateway or new sensor can seamlessly publish to existing endpoints.                            |



\*\*Tech Stack:\*\* Python · Pydantic · FastAPI · MapLibre/React (downstream) · IMD/IoT/DEM data sources



\## Architecture Overview



```

IMD Forecasts ─┐

IoT Sensors ────┼──▶  Ingestion \& Normalization  ──▶  Fused Catchment State  ──▶  Hydrology/ML Engine (FastAPI)  ──▶  Command Center (MapLibre/React)

Soil Moisture ──┤            (this repo)

DEM / Landslide ┘

```



\## Getting Started



> Update this section with actual setup instructions once finalized.



```bash

\# Clone the repository

git clone <repo-url>

cd flood-data-iot



\# Install dependencies

pip install -r requirements.txt



\# Run in demo/simulated mode

python main.py --mode demo



\# Run in live mode

python main.py --mode live

```



\## Team



\*\*Team Vmax\*\* — Smart India Hackathon 2026



\---



\_Built for Smart India Hackathon 2026 — Problem ID 26192\_



