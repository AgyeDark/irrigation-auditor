import streamlit as st
import pandas as pd
import requests
import json
import plotly.graph_objects as go
import os
import time # Needed for the retry logic

# --- PAGE CONFIG ---
st.set_page_config(page_title="FAO-56 Irrigation Audit", page_icon="💧", layout="wide")

st.title("💧 FAO-56 Smart Irrigation Auditor")
st.markdown("**Precision Agriculture for Ghana** | Powered by Open-Meteo & FAO Data")

# --- 1. LOAD DATABASE ---
@st.cache_data
def load_crop_db():
    try:
        if not os.path.exists('fao_crops.json'):
            return {}
        with open('fao_crops.json', 'r') as f:
            return json.load(f)
    except Exception:
        return {}

crop_db = load_crop_db()

# --- SIDEBAR CONFIG ---
st.sidebar.header("1. Field Location")

schemes = {
    "Tono Dam (Navrongo)": {"lat": 10.866, "lon": -1.166},
    "Vea Dam (Bolgatanga)": {"lat": 10.85, "lon": -0.85},
    "Bontanga (Tamale)": {"lat": 9.57, "lon": -1.02},
    "Asutsuare (Banana Hub)": {"lat": 6.07, "lon": 0.22},
    "Kpong (Akuse)": {"lat": 6.10, "lon": 0.05},
    "Weija (Accra)": {"lat": 5.58, "lon": -0.35},
    "Twifo Praso (Central)": {"lat": 5.61, "lon": -1.55},
    "Custom Location": {"lat": 0.0, "lon": 0.0}
}
location_name = st.sidebar.selectbox("Select Scheme", list(schemes.keys()))

if location_name == "Custom Location":
    lat = st.sidebar.number_input("Latitude", value=6.67, format="%.4f")
    lon = st.sidebar.number_input("Longitude", value=-1.56, format="%.4f")
else:
    lat = schemes[location_name]["lat"]
    lon = schemes[location_name]["lon"]

# --- CROP SELECTOR ---
st.sidebar.divider()
st.sidebar.header("2. Crop Configuration")

crop_name = "Standard Crop"
kc = 1.0

if crop_db:
    category = st.sidebar.selectbox("Crop Category", list(crop_db.keys()))
    if category in crop_db:
        specific_crops = list(crop_db[category].keys())
        crop_name = st.sidebar.selectbox("Select Crop", specific_crops)
        
        stage_options = {
            "Initial (Planting/Seedling)": "init",
            "Mid-Season (Flowering/Fruiting)": "mid",
            "Late Season (Ripening/Harvest)": "end"
        }
        stage_label = st.sidebar.selectbox("Growth Stage", list(stage_options.keys()), index=1)
        stage_key = stage_options[stage_label]
        
        kc = crop_db[category][crop_name][stage_key]
        st.sidebar.info(f"**Kc Value:** {kc} ({stage_label})")
else:
    st.sidebar.warning("⚠️ Database 'fao_crops.json' not found. Using default Kc=1.0")

st.sidebar.divider()
st.sidebar.subheader("3. Pump Settings")
pump_capacity = st.sidebar.number_input("Pump Capacity (Liters/min)", value=200)
field_size = st.sidebar.number_input("Field Size (Acres)", value=1.0)

# --- WEATHER ENGINE (ROBUST & CACHED) ---
@st.cache_data(ttl=3600) # Cache data for 1 hour to prevent Error 429
def get_weather_data_safe(lat, lon):
    # Manual URL construction to prevent 'int+str' error
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=et0_fao_evapotranspiration,precipitation_sum&timezone=GMT&past_days=2&forecast_days=5"
    
    # Retry Logic: Try 3 times before giving up
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=10)
            
            # If server says "Too Many Requests" (429), trigger the retry logic
            if response.status_code == 429:
                response.raise_for_status()
                
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame({
                "Date": data['daily']['time'],
                "ETo": data['daily']['et0_fao_evapotranspiration'],
                "Rain": data['daily']['precipitation_sum']
            })
            
            # Safe Data Conversion
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Interpolate to fill small gaps (clouds), fill remaining NaNs with defaults
            df['ETo'] = pd.to_numeric(df['ETo'], errors='coerce').interpolate().fillna(3.5)
            df['Rain'] = pd.to_numeric(df['Rain'], errors='coerce').fillna(0.0)
            
            return df
            
        except requests.exceptions.RequestException as e:
            # If it's a 429 or connection error, wait and try again
            time.sleep(2 ** attempt) # Wait 1s, then 2s, then 4s
            continue
            
    # If all 3 attempts fail
    st.error("⚠️ Weather Satellite is busy. Please wait a minute and try again.")
    return pd.DataFrame()

# --- MAIN LOGIC ---
if st.button("Run Irrigation Audit", type="primary"):
    display_name = crop_name if crop_name else "Unknown Crop"
    
    with st.spinner(f"🛰️ Auditing {display_name} in {location_name}..."):
        # 1. Get Data
        df = get_weather_data_safe(lat, lon)
        
        if not df.empty:
            try:
                # 2. Calculate Balance
                df['Crop_Water_Need'] = df['ETo'] * float(kc)
                df['Irrigation_Req'] = (df['Crop_Water_Need'] - df['Rain']).clip(lower=0)
                
                # 3. Calculate Pump Time
                total_liters = df['Irrigation_Req'] * 4046.86 * float(field_size)
                df['Pump_Hours'] = total_liters / (int(pump_capacity) * 60)
                
                # --- DASHBOARD UI ---
                today = df.iloc[2]
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Today's Rain", f"{today['Rain']:.1f} mm")
                col2.metric("Crop Thirst (ETc)", f"{today['Crop_Water_Need']:.1f} mm")
                col3.metric("Irrigation Needed", f"{today['Irrigation_Req']:.1f} mm", 
                            delta="Deficit" if today['Irrigation_Req'] > 0 else "Balanced", delta_color="inverse")
                
                hrs = int(today['Pump_Hours'])
                mins = int((today['Pump_Hours'] % 1) * 60)
                col4.metric("Pump Runtime", f"{hrs}h {mins}m")

                st.divider()

                col_chart, col_advice = st.columns([2, 1])
                
                with col_chart:
                    st.subheader("7-Day Water Balance")
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=df['Date'], y=df['Rain'], name='Rainfall', marker_color='#3b82f6'))
                    fig.add_trace(go.Bar(x=df['Date'], y=df['Crop_Water_Need'], name='Crop Thirst', marker_color='#f97316', opacity=0.7))
                    fig.add_trace(go.Scatter(x=df['Date'], y=df['Irrigation_Req'], name='Irrigation Needed', 
                                           line=dict(color='#ef4444', width=3), mode='lines+markers'))
                    
                    # FIX: Convert Timestamp to String to prevent Pandas/Plotly math conflict
                    today_str = today['Date'].strftime('%Y-%m-%d')
                    
                    # Add the vertical line (no annotation here to avoid the bug)
                    fig.add_vline(x=today_str, line_dash="dash", line_color="green")
                    
                    # Add the annotation separately, positioned at the top of the plot
                    fig.add_annotation(
                        x=today_str,
                        y=1,  # Top of the plot
                        yref="paper",  # Relative to the entire figure height (0=bottom, 1=top)
                        text="Today",
                        showarrow=False,
                        font=dict(color="green", size=12),
                        align="center",
                        yanchor="bottom"  # Anchor below the text to avoid overlapping the top edge
                    )
                    
                    fig.update_layout(height=400, margin=dict(t=20, b=20), hovermode="x unified", legend=dict(orientation="h", y=1.1))
                    st.plotly_chart(fig, use_container_width=True)

                with col_advice:
                    st.subheader("📝 Recommendation")
                    if today['Irrigation_Req'] > 0:
                        st.error(f"""
                        **Status: WATER STRESS**
                        Plan: Run pump for **{hrs}h {mins}m**.
                        Apply **{int(total_liters.iloc[2])} Liters**.
                        """)
                    else:
                        st.success("**Status: ADEQUATE.** No irrigation needed.")
                    
                    with st.expander("Data Table"):
                        st.dataframe(df.style.format({
                            "ETo": "{:.2f}",
                            "Rain": "{:.1f}",
                            "Crop_Water_Need": "{:.1f}",
                            "Irrigation_Req": "{:.1f}",
                            "Pump_Hours": "{:.2f}"
                        }))

            except Exception as e:
                st.error(f"Calculation Error: {e}")

            st.divider()
st.markdown("<p style='text-align: center; color: #888888;'>© 2025 Agyei Darko | Smart Irrigation Auditor </p>", unsafe_allow_html=True)