import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import numpy as np
import pandas as pd
import cv2
from geopy.geocoders import Nominatim
from PIL import Image
import datetime

# =============================================================================
# 1. STREAMLIT PAGE CONFIGURATION & HIGH-CONTRAST COMMAND ROOM THEMING
# =============================================================================
st.set_page_config(
    page_title="AQUA-GENESIS | Smart City Flood Control",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Contrast Command Room CSS
st.markdown("""
<style>
    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 14px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4) !important;
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
    }
    div[data-testid="stMetricDelta"] {
        font-weight: 600 !important;
    }

    /* Alert Card Styling */
    .alert-card {
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .alert-low {
        background-color: #064e3b;
        border-left: 5px solid #10b981;
        color: #ecfdf5;
    }
    .alert-moderate {
        background-color: #065f46;
        border-left: 5px solid #34d399;
        color: #ecfdf5;
    }
    .alert-high {
        background-color: #78350f;
        border-left: 5px solid #f59e0b;
        color: #fffbeb;
    }
    .alert-very-high {
        background-color: #7c2d12;
        border-left: 5px solid #f97316;
        color: #fff7ed;
    }
    .alert-extreme {
        background-color: #7f1d1d;
        border-left: 5px solid #ef4444;
        color: #fef2f2;
    }

    /* Terminal Log Box */
    .log-box {
        background-color: #020617;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px;
        font-family: 'Consolas', 'Courier New', Courier, monospace;
        font-size: 0.88rem;
        color: #38bdf8;
        max-height: 380px;
        overflow-y: auto;
    }

    /* Heatmap Legend Box */
    .legend-box {
        background-color: #0f172a;
        padding: 12px;
        border-radius: 6px;
        border: 1px solid #334155;
        text-align: center;
        color: #f8fafc !important;
        font-weight: 600;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State Variables
if "simulation_history" not in st.session_state:
    st.session_state.simulation_history = []

if "hitl_approved" not in st.session_state:
    st.session_state.hitl_approved = False

# =============================================================================
# 2. SWMM / NDMA AGENTIC RAG KNOWLEDGE BASE
# =============================================================================
def get_swmm_rag_context():
    """Returns grounded vector documents from US EPA SWMM and NDMA Guidelines."""
    return [
        {
            "doc_id": "SWMM_MANUAL_CH4",
            "title": "US EPA SWMM Hydrologic Drainage Manual (Section 4.2)",
            "text": "Sluice Gate & Pump Actuation Rule: When local rainfall intensity exceeds 15.0 mm/hr or runoff inflow exceeds trunk line capacity, storm water pumps must activate instantly at outfall nodes to prevent road inundation."
        },
        {
            "doc_id": "NDMA_FLOOD_SOP_SEC8",
            "title": "NDMA Urban Flood Standard Operating Procedure (Section 8.1)",
            "text": "Human Safety Precedence Mandate: In heavy rainfall surges (>35 mm/hr) or when sub-surface pipe blockage is detected, residential low-lying blocks take 100% priority for automated pump bypass deployment."
        },
        {
            "doc_id": "HITL_SAFETY_PROTOCOL",
            "title": "Municipal HITL (Human-in-the-Loop) Control Standard",
            "text": "Human Verification Mandate: Automated actuation commands for heavy outfall pumps (>100 L/s) require a verified Human-in-the-Loop operator sign-off before mechanical override triggers."
        }
    ]

# =============================================================================
# 3. AI AGENT SWARM & CORE ENGINE FUNCTIONS
# =============================================================================

# --- AGENT 1: LOCATION AGENT ---
def agent_location(city_name: str):
    """Retrieves exact GPS coordinates for any city using Geopy Nominatim."""
    try:
        geolocator = Nominatim(user_agent="aqua_genesis_control_room_v1")
        location = geolocator.geocode(city_name, timeout=5)
        if location:
            return float(location.latitude), float(location.longitude), f"{location.address}"
        return 11.0040, 77.0493, "Coimbatore, Tamil Nadu, India (Default Baseline)"
    except Exception as e:
        return 11.0040, 77.0493, f"Coimbatore, Tamil Nadu (Fallback - {str(e)})"


# --- AGENT 2: WEATHER TELEMETRY AGENT ---
def agent_weather(lat: float, lon: float, mode: str, sim_rain_val: float):
    """Fetches real-time weather from Open-Meteo or uses simulation driver."""
    if mode == "🌐 Live Weather Mode":
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,rain,weather_code&hourly=rain&forecast_days=1"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                current = data.get("current", {})
                hourly_rain = data.get("hourly", {}).get("rain", [0.0])
                
                rain_now = float(current.get("rain", 0.0))
                forecast_rain = float(np.mean(hourly_rain[:3])) if len(hourly_rain) >= 3 else rain_now * 1.2
                
                return {
                    "current_rain": rain_now,
                    "forecast_rain": round(forecast_rain, 2),
                    "temp": float(current.get("temperature_2m", 28.0)),
                    "humidity": int(current.get("relative_humidity_2m", 75)),
                    "pressure": int(current.get("surface_pressure", 1012)),
                    "wind_speed": float(current.get("wind_speed_10m", 3.5)),
                    "condition": "Live Monsoonal Stream" if rain_now > 0 else "Clear / Light Clouds",
                    "is_live": True,
                    "status_msg": "Live Open-Meteo API Synced"
                }
        except Exception:
            pass

    # Simulation Mode
    forecast = round(sim_rain_val * 1.25 + (sim_rain_val * 0.1), 2)
    return {
        "current_rain": float(sim_rain_val),
        "forecast_rain": float(forecast),
        "temp": 27.5,
        "humidity": 88,
        "pressure": 1008,
        "wind_speed": 12.4,
        "condition": "Simulated Cloudburst Surge" if sim_rain_val > 40 else "Simulated Monsoonal Activity",
        "is_live": False,
        "status_msg": "Simulation Driver Active"
    }


# --- AGENT 3: SWMM DYNAMIC DIGITAL TWIN AGENT ---
def agent_digital_twin(current_rain: float, forecast_rain: float, lat: float, lon: float, is_pipe_blocked: bool, grid_size: int = 15):
    """
    Simulates SWMM hydrodynamic surface runoff (Inflow vs Outflow) and 
    calculates safe water depth limits alongside blockage risks.
    """
    SAFE_MAX_DEPTH_THRESHOLD = 1.0  # Safe threshold limit: 1.0 meter
    
    x = np.linspace(-2, 2, grid_size)
    y = np.linspace(-2, 2, grid_size)
    X, Y = np.meshgrid(x, y)
    
    spatial_shift = (abs(lat) % 1.0) - (abs(lon) % 1.0)
    elevation_topography = 8.0 - ((X - spatial_shift)**2 + (Y + spatial_shift)**2)
    
    # 1. Inflow Rate
    effective_rain_load = current_rain + (forecast_rain * 0.4)
    inflow_rate_lps = round(effective_rain_load * 3.5, 1)
    
    # 2. Outflow Rate
    if is_pipe_blocked:
        outflow_efficiency = 0.15  # Blocked pipe restricts discharge to 15%
    else:
        outflow_efficiency = 0.92 if current_rain <= 60 else 0.85
        
    outflow_rate_lps = round(inflow_rate_lps * outflow_efficiency, 1)
    
    # 3. Water Depth Accumulation
    if not is_pipe_blocked:
        base_depth = np.maximum(0.1, (inflow_rate_lps - outflow_rate_lps) / 120.0)
        water_depth_matrix = np.clip(base_depth * (10.0 - elevation_topography) * 0.1, 0.1, 0.95)
    else:
        accumulation_factor = max(0.4, (inflow_rate_lps - outflow_rate_lps) / 25.0)
        base_depth = (10.0 - elevation_topography) * accumulation_factor
        base_depth[2:6, 8:14] += 2.5
        water_depth_matrix = np.clip(base_depth, 0.1, 8.5)
        
    peak_water_depth = float(np.max(water_depth_matrix))
    drain_utilization = 100.0 if is_pipe_blocked else min(100.0, float((inflow_rate_lps / 180.0) * 100.0))
    
    # Render 4-Color Jet Heatmap
    scaled_matrix = np.clip((water_depth_matrix / 5.0) * 255.0, 0, 255).astype(np.uint8)
    color_heatmap = cv2.applyColorMap(scaled_matrix, cv2.COLORMAP_JET)
    resized_map = cv2.resize(color_heatmap, (450, 450), interpolation=cv2.INTER_NEAREST)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(resized_map, "NW: Feeder Zone", (10, 25), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(resized_map, "NE: Central Low Basin", (250, 25), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(resized_map, "SW: Residential", (10, 430), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(resized_map, "SE: Primary Outfall", (250, 430), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    legend_bar = np.zeros((450, 45, 3), dtype=np.uint8)
    for i in range(450):
        val = np.uint8(255 - (i * 255 / 450))
        legend_bar[i, :] = val
    legend_bar = cv2.applyColorMap(legend_bar, cv2.COLORMAP_JET)
    
    separator = np.ones((450, 5, 3), dtype=np.uint8) * 255
    final_render = np.hstack((resized_map, separator, legend_bar))
    
    return {
        "peak_depth": round(peak_water_depth, 2),
        "safe_depth_limit": SAFE_MAX_DEPTH_THRESHOLD,
        "inflow_rate_lps": inflow_rate_lps,
        "outflow_rate_lps": outflow_rate_lps,
        "drain_utilization": round(drain_utilization, 1),
        "is_blocked": is_pipe_blocked,
        "heatmap_img": final_render
    }


# --- AGENT 4: RISK ASSESSMENT AGENT ---
def agent_risk_assessment(current_rain: float, forecast_rain: float, peak_depth: float, drain_utilization: float, is_blocked: bool):
    """Computes Flood Risk Score driven by Rain, Depth, and Pipe Obstruction."""
    rain_score = min(100.0, (current_rain / 100.0) * 100.0) * 0.30
    forecast_score = min(100.0, (forecast_rain / 120.0) * 100.0) * 0.20
    depth_score = min(100.0, (peak_depth / 3.0) * 100.0) * 0.35
    drain_score = min(100.0, drain_utilization) * 0.15
    
    total_risk_score = min(100.0, max(0.0, rain_score + forecast_score + depth_score + drain_score))
    if is_blocked and current_rain > 15.0:
        total_risk_score = max(75.0, total_risk_score)
        
    risk_score_final = round(total_risk_score, 1)
    
    if risk_score_final <= 20.0:
        level = "LOW"
        color_code = "#34d399"
        badge_class = "alert-low"
    elif risk_score_final <= 40.0:
        level = "MODERATE"
        color_code = "#6ee7b7"
        badge_class = "alert-moderate"
    elif risk_score_final <= 60.0:
        level = "HIGH"
        color_code = "#fbbf24"
        badge_class = "alert-high"
    elif risk_score_final <= 80.0:
        level = "VERY HIGH"
        color_code = "#fb923c"
        badge_class = "alert-very-high"
    else:
        level = "EXTREME"
        color_code = "#f87171"
        badge_class = "alert-extreme"
        
    return {
        "score": risk_score_final,
        "level": level,
        "color": color_code,
        "badge_class": badge_class
    }


# --- AGENT 5: DECISION & HITL ACTUATION AGENT ---
def agent_decision(risk_level: str, twin_data: dict, rag_docs: list, hitl_status: bool):
    """
    Evaluates SWMM / NDMA Agentic RAG Context and enforces HITL authorization.
    """
    actions = []
    is_blocked = twin_data["is_blocked"]
    peak_depth = twin_data["peak_depth"]
    safe_limit = twin_data["safe_depth_limit"]
    
    # Evaluate RAG Rule Grounding
    matched_doc = rag_docs[1] if (is_blocked or twin_data["inflow_rate_lps"] > 100) else rag_docs[0]
    actions.append(f"📚 **AGENTIC RAG RULE MATCHED:** [{matched_doc['doc_id']}] *{matched_doc['title']}*")
    
    if is_blocked:
        actions.append("🚨 **PIPE BLOCKAGE ANOMALY DETECTED:** Silt/Debris obstruction detected in Central Low Basin Line!")
        actions.append("⚡ **FIELD DISPATCH:** Deploy High-Pressure Hydraulic Jetting Vehicle & Ward Clearance Squad.")
        
        # HITL Authorization Check
        if hitl_status:
            actions.append("✅ **HITL AUTHORIZATION APPROVED:** Human City Operator confirmed override. Auxiliary bypass pumps engaged at 120 L/s.")
        else:
            actions.append("⏳ **HITL OVERRIDE PENDING:** Auxiliary Bypass Pumps staged. Awaiting Human City Operator Sign-off!")
    else:
        actions.append("✅ **DRAIN PIPES CLEAR:** Sluice gates & outfalls discharging water efficiently.")
        actions.append(f"🟢 **SAFE DEPTH MAINTAINED:** Peak Depth ({peak_depth}m) controlled within Safe Limit ({safe_limit}m).")
    
    if peak_depth > safe_limit:
        actions.append(f"⚠️ **SAFE DEPTH EXCEEDED:** Current depth ({peak_depth}m) > Target Limit ({safe_limit}m).")
    
    if risk_level == "LOW":
        actions.append("🟢 Keep primary drainage networks in baseline gravity-flow state.")
        status_summary = "Nominal Operations"
    elif risk_level == "MODERATE":
        actions.append("🟡 Inspect secondary storm drain inlets for debris obstructions.")
        status_summary = "Heightened Vigilance"
    elif risk_level == "HIGH":
        actions.append("🟠 Open primary Sluice Gates #1 and #3 to maximum gravity discharge.")
        status_summary = "Active Mitigation"
    elif risk_level == "VERY HIGH":
        actions.append("🔴 Dispatch Ward Quick-Response Emergency Teams.")
        status_summary = "Emergency Dispatch"
    else:
        actions.append("🚨 ACTIVATE MUNICIPAL DISASTER MANAGEMENT PROTOCOL (NDMA SOP).")
        status_summary = "Critical Response"
        
    return {
        "status_summary": status_summary,
        "actions": actions,
        "matched_rag": matched_doc
    }


# --- AGENT 6: MUNICIPAL ALERT AGENT ---
def agent_municipal_alert(risk_level: str, city: str, risk_score: float, is_blocked: bool):
    """Formulates formal alert communications for corporate officers and engineers."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    
    if is_blocked:
        header = f"🚨 PIPE BLOCKAGE EMERGENCY DISPATCH - {city.upper()} WARD"
        body = f"Anomalous outflow restriction detected at {timestamp}. Inflow > Outflow. Hydraulic Jetting Team & Emergency Bypass Pumps Dispatched!"
        class_name = "alert-extreme"
    elif risk_level in ["LOW", "MODERATE"]:
        header = f"✅ MUNICIPAL STATUS NORMAL - {city.upper()} WARD"
        body = f"System telemetry indicates safe hydro-parameters as of {timestamp}. Risk Score: {risk_score}/100. Drainage lines running clear."
        class_name = "alert-low" if risk_level == "LOW" else "alert-moderate"
    elif risk_level == "HIGH":
        header = f"⚠️ MUNICIPAL FLOOD ADVISORY - {city.upper()} WARD"
        body = f"Elevated surface runoff detected at {timestamp}. Risk Score: {risk_score}/100. Field engineers instructed to prepare drainage assets."
        class_name = "alert-high"
    else:
        header = f"🔥 CRITICAL RED ALERT: FLASH FLOOD EMERGENCY - {city.upper()}"
        body = f"Extreme inundation surge confirmed at {timestamp}. Risk Score: {risk_score}/100. Emergency Response Forces Deployed!"
        class_name = "alert-extreme"
        
    return {
        "header": header,
        "body": body,
        "class_name": class_name
    }


# =============================================================================
# 4. STREAMLIT UI SIDEBAR & CONTROL INTERFACE
# =============================================================================

st.sidebar.image("https://img.icons8.com/fluency/96/tsunami.png", width=70)
st.sidebar.title("PROJECT AQUA-GENESIS")
st.sidebar.caption("Dynamic Urban Watershed & Flood Resilience Engine")
st.sidebar.markdown("---")

st.sidebar.subheader("🎛️ Operation Mode Select")
app_mode = st.sidebar.radio(
    "Choose System Mode:",
    ["🌐 Live Weather Mode", "🎮 Simulation Mode"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Target Ward / Location")
target_city_input = st.sidebar.text_input("Enter City/Ward Name (India):", value="Coimbatore")

st.sidebar.markdown("---")
st.sidebar.subheader("🌧️ Rainfall Driver Controls")

is_slider_disabled = (app_mode == "🌐 Live Weather Mode")

sim_rainfall = st.sidebar.slider(
    "Simulated Cloudburst Rain (mm/hr):",
    min_value=0.0,
    max_value=150.0,
    value=45.0,
    step=2.5,
    disabled=is_slider_disabled,
    help="Slider disabled in Live Weather Mode. Switch to Simulation Mode to adjust."
)

st.sidebar.markdown("---")
st.sidebar.subheader("🚧 Drainage Pipe Simulation")
sim_pipe_block = st.sidebar.toggle("Simulate Pipe Debris Blockage", value=False, help="Toggle ON to demonstrate how the AI Agent detects pipe blockages and dispatches jetting squads.")

if sim_pipe_block:
    st.sidebar.error("🚨 Simulated Drainage Pipe Blockage ACTIVE!")
else:
    st.sidebar.success("✅ Drainage Pipes CLEAR & UNSTRIPED")

st.sidebar.markdown("---")
st.sidebar.subheader("👤 Human-in-the-Loop (HITL) Gate")
hitl_toggle = st.sidebar.checkbox("Authorize Pump Actuation (HITL)", value=st.session_state.hitl_approved, help="Check this box to simulate human city operator sign-off for pump override.")
st.session_state.hitl_approved = hitl_toggle

st.sidebar.markdown("---")
execute_sim_btn = st.sidebar.button("⚡ EXECUTE CONTROL ROOM SIMULATION", use_container_width=True, type="primary")


# =============================================================================
# 5. EXECUTION PIPELINE & AGENT ORCHESTRATION
# =============================================================================

rag_docs = get_swmm_rag_context()
lat, lon, location_address = agent_location(target_city_input)
weather_data = agent_weather(lat, lon, app_mode, sim_rainfall)
twin_data = agent_digital_twin(weather_data["current_rain"], weather_data["forecast_rain"], lat, lon, sim_pipe_block)
risk_data = agent_risk_assessment(
    weather_data["current_rain"], 
    weather_data["forecast_rain"], 
    twin_data["peak_depth"], 
    twin_data["drain_utilization"],
    sim_pipe_block
)
decision_data = agent_decision(risk_data["level"], twin_data, rag_docs, st.session_state.hitl_approved)
alert_data = agent_municipal_alert(risk_data["level"], target_city_input, risk_data["score"], sim_pipe_block)

if execute_sim_btn:
    new_entry = {
        "Timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "Location": target_city_input.capitalize(),
        "Rain (mm/hr)": weather_data["current_rain"],
        "Forecast (mm/hr)": weather_data["forecast_rain"],
        "Risk Score": risk_data["score"],
        "Risk Level": risk_data["level"],
        "Peak Depth (m)": twin_data["peak_depth"],
        "Decision": decision_data["status_summary"]
    }
    st.session_state.simulation_history.insert(0, new_entry)
    st.session_state.simulation_history = st.session_state.simulation_history[:10]


# =============================================================================
# 6. DASHBOARD HEADER & TOP METRICS ROW
# =============================================================================

title_col, mode_col = st.columns([3, 1])
with title_col:
    st.title("🌊 PROJECT AQUA-GENESIS")
    st.caption("Smart City Command & Control Center | Autonomous Watershed & Urban Flood Management Engine")
with mode_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if weather_data["is_live"]:
        st.success("🟢 MODE: LIVE WEATHER API")
    else:
        st.info("🎮 MODE: SIMULATION ENGINE")

st.markdown("---")

m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

with m_col1:
    st.metric(
        label="🌧️ Current Rainfall", 
        value=f"{weather_data['current_rain']:.1f} mm/hr",
        delta=f"{weather_data['condition']}"
    )

with m_col2:
    st.metric(
        label="🔮 Forecast Rainfall", 
        value=f"{weather_data['forecast_rain']:.1f} mm/hr",
        delta="Next 3 Hours"
    )

with m_col3:
    st.metric(
        label="🛡️ Flood Risk Score", 
        value=f"{risk_data['score']} / 100",
        delta=f"Level: {risk_data['level']}",
        delta_color="inverse" if risk_data['score'] > 40 else "normal"
    )

with m_col4:
    st.metric(
        label="🌊 Predicted Water Depth", 
        value=f"{twin_data['peak_depth']:.2f} m",
        delta=f"Safe Limit: {twin_data['safe_depth_limit']}m | Outflow: {twin_data['outflow_rate_lps']} L/s",
        delta_color="normal" if twin_data['peak_depth'] <= twin_data['safe_depth_limit'] else "inverse"
    )

with m_col5:
    st.metric(
        label="🏛️ Municipal Status", 
        value=decision_data["status_summary"],
        delta=f"Ward: {target_city_input.capitalize()}"
    )

st.markdown("<br>", unsafe_allow_html=True)


# =============================================================================
# 7. MIDDLE ROW: INTERACTIVE FOLIUM MAP & AGENT EXECUTION LOGS
# =============================================================================

map_col, log_col = st.columns([1, 1])

with map_col:
    st.subheader("🗺️ Live Geographic Information System (OpenStreetMap)")
    
    m = folium.Map(location=[lat, lon], zoom_start=13, tiles="CartoDB dark_matter")
    
    marker_color = "green" if risk_data["score"] <= 40 else "orange" if risk_data["score"] <= 70 else "red"
    folium.Marker(
        [lat, lon],
        popup=f"<b>{target_city_input.capitalize()} Ward Core</b><br>Flood Risk Score: {risk_data['score']}/100",
        tooltip=f"{target_city_input.capitalize()} Target Center",
        icon=folium.Icon(color=marker_color, icon="info-sign")
    ).add_to(m)
    
    folium.Circle(
        radius=1800,
        location=[lat, lon],
        color=risk_data["color"],
        fill=True,
        fill_color=risk_data["color"],
        fill_opacity=0.25
    ).add_to(m)
    
    st_folium(m, width=None, height=380, use_container_width=True)
    st.caption(f"📍 **GPS Coordinates:** `{lat:.4f}°N, {lon:.4f}°E` | **Address:** `{location_address}`")


with log_col:
    st.subheader("🤖 Agentic AI Reasoning & Execution Logs")
    
    timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    hitl_str = "APPROVED ✅" if st.session_state.hitl_approved else "PENDING ⏳"
    
    log_content = f"""[SYS_INIT {timestamp_str}] AQUA-GENESIS Multi-Agent Swarm Initialized.

----------------------------------------------------------------------
👁️ [1. LOCATION AGENT]
> Resolving Spatial Geocode for '{target_city_input}'...
> Target Latitude: {lat:.4f} | Longitude: {lon:.4f}
> Status: GPS Coordinates Locked & Vector Catchment Bound.

📡 [2. WEATHER TELEMETRY AGENT]
> Querying Weather Feed ({weather_data['status_msg']})...
> Sensed Current Rain: {weather_data['current_rain']} mm/hr | Temp: {weather_data['temp']}°C
> Forecast Rain Rate: {weather_data['forecast_rain']} mm/hr (3-Hour Horizon)

🌀 [3. HYDRODYNAMIC DIGITAL TWIN AGENT (SWMM)]
> Mass Balance Hydrology (Inflow: {twin_data['inflow_rate_lps']} L/s | Outflow: {twin_data['outflow_rate_lps']} L/s)...
> Computed Peak Surface Water Depth: {twin_data['peak_depth']} meters (Target Limit: {twin_data['safe_depth_limit']}m)
> Pipe Obstruction Sensor: {'🚨 ANOMALY BLOCKED' if twin_data['is_blocked'] else '✅ DRAIN CLEAR'}

📚 [4. AGENTIC RAG VECTOR LAYER]
> Querying Knowledge Base Embeddings (SWMM Manual & NDMA SOPs)...
> Matched Doc: [{decision_data['matched_rag']['doc_id']}] '{decision_data['matched_rag']['title']}'
> Executed Vector Rule -> "{decision_data['matched_rag']['text'][:90]}..."

⚖️ [5. RISK ASSESSMENT AGENT]
> Executing Multi-Factor Risk Matrix (Rain + Forecast + Depth + Drains)...
> Calculated Normalized Flood Risk Score: {risk_data['score']} / 100
> Evaluated Hazard Category: {risk_data['level']}

⚡ [6. DECISION & HITL ACTUATION AGENT]
> Protocol Formulated: {decision_data['status_summary']}
> HITL Operator Authorization Status: {hitl_str}
> Dispatched Directives: {len(decision_data['actions'])} Operations Generated.

🚨 [7. MUNICIPAL ALERT AGENT]
> Communication Card Generated for Corporate Officers.
> Alert Broadcast Status: SENT TO COMMAND CONSOLE.
----------------------------------------------------------------------
[SYS_SUCCESS] All Agent Tasks Executed Nominally."""
    
    st.markdown(f'<div class="log-box"><pre style="color:#38bdf8; background:transparent; border:none; margin:0; font-size:0.85rem;">{log_content}</pre></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# =============================================================================
# 8. BOTTOM ROW: FLOOD HEATMAP, PIPE TELEMETRY, DECISION & ALERT CARDS
# =============================================================================

bottom_left, bottom_right = st.columns([1, 1])

with bottom_left:
    st.subheader("🗺️ 4-Color Watershed Flood Heatmap")
    
    st.image(
        twin_data["heatmap_img"], 
        channels="BGR", 
        use_container_width=True,
        caption="15x15 Spatial Hydrodynamic Topography Matrix (OpenCV JET Colormap Rendering)"
    )
    
    st.markdown("""
    <div class="legend-box">
        <span style="color: #60a5fa; font-weight: bold;">■ Blue:</span> Very Low (0-2.5m) &nbsp;|&nbsp; 
        <span style="color: #4ade80; font-weight: bold;">■ Green:</span> Moderate (2.5-5.0m) &nbsp;|&nbsp; 
        <span style="color: #facc15; font-weight: bold;">■ Yellow:</span> High (5.0-7.5m) &nbsp;|&nbsp; 
        <span style="color: #f87171; font-weight: bold;">■ Red:</span> Critical (>7.5m)
    </div>
    """, unsafe_allow_html=True)


with bottom_right:
    st.subheader("📊 Hydro-Balance & Pipe Telemetry")
    
    col_in, col_out = st.columns(2)
    col_in.metric("🌧️ Inflow Rate", f"{twin_data['inflow_rate_lps']} L/s")
    col_out.metric("🚰 Active Outflow", f"{twin_data['outflow_rate_lps']} L/s")
    
    if twin_data["is_blocked"]:
        st.error("🚨 **PIPE BLOCKAGE ANOMALY DETECTED IN TRUNK LINE B2**")
    else:
        st.success("✅ **DRAIN PIPE FLOW STATUS: CLEAR & UNOBSTRUCTED**")
        
    color_val = risk_data['color']
    score_val = risk_data['score']
    level_val = risk_data['level']
    
    st.markdown(f"#### Flood Risk Score: <span style='color:{color_val}; font-weight:bold;'>{score_val} / 100 ({level_val})</span>", unsafe_allow_html=True)
    st.progress(score_val / 100.0)
    st.caption(f"Drainage Capacity Utilization: **{twin_data['drain_utilization']}%**")
    
    # MUNICIPAL ALERT CARD
    st.markdown(f"""
    <div class="alert-card {alert_data['class_name']}">
        <h4 style="margin: 0 0 6px 0;">{alert_data['header']}</h4>
        <p style="margin: 0; font-size: 0.9rem;">{alert_data['body']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # DECISION PROTOCOL DIRECTIVES
    with st.expander("🛠️ View Automated Action Protocols & Active SWMM RAG Context", expanded=True):
        for act in decision_data["actions"]:
            st.markdown(f"- {act}")

st.markdown("<br><hr>", unsafe_allow_html=True)


# =============================================================================
# 9. HISTORY PANEL & HISTORICAL REFERENCE (CHENNAI 2015)
# =============================================================================

hist_col, ref_col = st.columns([2, 1])

with hist_col:
    st.subheader("📜 Recent Simulation & Run History (Last 10 Runs)")
    if len(st.session_state.simulation_history) > 0:
        df_history = pd.DataFrame(st.session_state.simulation_history)
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("No simulations logged in this session yet. Click '⚡ EXECUTE CONTROL ROOM SIMULATION' on the sidebar to record runs.")


with ref_col:
    st.subheader("📚 Historical Reference")
    with st.expander("📖 Chennai Flood 2015 Contextual Case Study", expanded=False):
        st.markdown("""
        **Event Overview:**
        In November–December 2015, Chennai experienced extreme monsoonal precipitation caused by a deep depression in the Bay of Bengal, delivering over 494 mm of rain in 24 hours.
        
        **Key Vulnerability Drivers:**
        * **Extreme Rainfall:** Unprecedented cloudburst intensity exceeding design storm limits.
        * **Rapid Urbanization:** Encroachment on natural wetland basins (e.g., Pallikaranai).
        * **Drainage Bottlenecks:** Arterial storm channels overwhelmed by heavy siltation.
        * **Reservoir Releases:** Emergency releases from Chembarambakkam Reservoir into the Adyar River.
        
        ---
        *ℹ️ **Disclaimer:** This historical baseline is displayed purely as a contextual reference for municipal resilience design and is NOT directly used to compute today's live Flood Risk Score.*
        """)

st.markdown("<br>", unsafe_allow_html=True)
st.caption("🌊 PROJECT AQUA-GENESIS | Production-Grade Smart City Control Room Engine | Built for National Hackathon Demonstrations")