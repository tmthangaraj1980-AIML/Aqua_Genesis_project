# 🌊 PROJECT AQUA-GENESIS
> **Smart City Command & Control Center | Autonomous Watershed & Urban Flood Management Engine**

[![Streamlit](https://img.shields.io/badge/Framework-Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![OpenCV](https://img.shields.io/badge/Vision-OpenCV-5C3EE8?style=for-the-badge&logo=opencv)](https://opencv.org)
[![Folium](https://img.shields.io/badge/GIS-Folium-77B829?style=for-the-badge&logo=leaflet)](https://python-visualization.github.io/folium/)

---

## 📌 Executive Overview

**AQUA-GENESIS** is a next-generation urban watershed management and flash-flood response system built for smart cities. Traditional municipal drainage systems rely on static threshold sensors that frequently fail or break during severe weather. AQUA-GENESIS replaces passive monitoring with an **Agentic AI Swarm** that combines live weather telemetry, mass-balance hydraulic modeling, and vector-grounded disaster response protocols.

### 🌟 Key Innovations & Problem Solved
1. **Hydraulic Mass-Balance Modeling ($Q_{\text{in}}$ vs $Q_{\text{out}}$):** Sensed water accumulation is modeled using fluid continuity dynamics ($\frac{dV}{dt} = Q_{\text{in}} - Q_{\text{out}}$) based on spatial catchment topography rather than simple rainfall multipliers.
2. **Sub-Surface Pipe Blockage Detection:** Senses inflow vs. outflow anomalies to detect siltation and debris obstructions in real time before severe surface flooding occurs.
3. **Agentic RAG Knowledge Base:** Grounded in **US EPA SWMM (Storm Water Management Model)** regulations and **NDMA Urban Flood Standard Operating Procedures**.
4. **Human-in-the-Loop (HITL) Gate:** Enforces operator verification before heavy mechanical outfall pumps (>100 L/s) or sluice gate overrides are actuated.

---

## 🤖 Multi-Agent AI Architecture

The system operates via a 6-Agent Swarm processing stream:
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│   1. LOCATION AGENT    │ ───► │  2. TELEMETRY AGENT    │ ───► │ 3. DIGITAL TWIN (SWMM) │
│ (Geopy / GPS Locking)  │      │ (Open-Meteo Live Feed) │      │  (15x15 Mesh / Hydro)  │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
│
┌────────────────────────┐      ┌────────────────────────┐                   ▼
│   6. ALERT AGENT       │ ◄─── │  5. DECISION & HITL    │ ◄─── ┌────────────────────────┐
│ (Municipal Broadcast)  │      │ (SWMM RAG + Actuation) │      │  4. RISK ASSESSMENT    │
└────────────────────────┘      └────────────────────────┘      │ (Multi-Factor Scoring) │
└────────────────────────┘


* **1. Location Agent:** Spatially geocodes target wards and locks catchment boundary vectors via OpenStreetMap APIs.
* **2. Weather Telemetry Agent:** Pulls keyless real-time precipitation, humidity, and forecast streams via Open-Meteo API.
* **3. Dynamic Digital Twin Agent:** Simulates spatial 2D surface runoff, elevation topography, and outfall discharge rates using OpenCV JET colormaps.
* **4. Risk Assessment Agent:** Evaluates a normalized Flood Risk Score ($0-100$) using weighted hydrological factors.
* **5. Decision & HITL Actuation Agent:** Matches live telemetry against embedded SWMM/NDMA vector RAG rules and enforces human operator approval for pump overrides.
* **6. Municipal Alert Agent:** Formulates formatted emergency warning dispatches for ward engineers and corporate officers.

---

## 🛠️ Tech Stack & Dependencies

* **Frontend Dashboard:** `Streamlit` (with high-contrast Command & Control dark CSS)
* **GIS Mapping Layer:** `Folium` & `streamlit-folium` (CartoDB Dark Matter base tiles)
* **Digital Twin Hydrodynamics:** `NumPy` & `OpenCV` (`opencv-python-headless`)
* **Geocoding & API Streams:** `geopy` (Nominatim) & `requests` (Open-Meteo API)
* **Data Pipelines:** `Pandas` & `Pillow`

---

## ⚡ Quick Start & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/tmthangaraj1980-AIML/Aqua_Genesis_project.git
cd AQUA_GENESIS_Hackathon
2. Create and Activate Virtual Environment
PowerShell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
3. Install Requirements
PowerShell
pip install -r requirements.txt
4. Run the Control Room Application
PowerShell
streamlit run app.py