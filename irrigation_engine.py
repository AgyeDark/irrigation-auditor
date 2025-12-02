import requests
import pandas as pd
import matplotlib.pyplot as plt


# Location: Tono Irrigation Dam, Navrongo, Ghana
LOCATION = {"name": "Navrongo (Tono Dam)", "lat": 10.866, "lon": -1.166}

# Crop Dictionary (FAO-56 Typical Values)
# Kc values vary by stage: [Initial, Mid-Season, Late-Season]
CROPS = {
    "Maize": {"kc": 1.1, "stage_name": "Mid-Season (Flowering)"}, 
    "Rice":  {"kc": 1.2, "stage_name": "Mid-Season (Flooding)"},
    "Tomato": {"kc": 0.8, "stage_name": "Mid-Season (Fruiting)"},
    "Onion": {"kc": 1.0, "stage_name": "Bulb Formation"}
}

# Select your crop here
CURRENT_CROP = "Maize"

print(f"🚜 Starting Irrigation Audit for {CURRENT_CROP} in {LOCATION['name']}...")

# ---  (Open-Meteo API) ---
# We fetch: ET0 (Evapotranspiration) and Rain
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": LOCATION["lat"],
    "longitude": LOCATION["lon"],
    "daily": ["et0_fao_evapotranspiration", "precipitation_sum", "temperature_2m_max"],
    "timezone": "GMT",
    "past_days": 3,  # Look back 3 days
    "forecast_days": 5 # Look forward 5 days
}

try:
    response = requests.get(url, params=params)
    data = response.json()
    
    # Organize the messy JSON into a clean Table (DataFrame)
    daily = data['daily']
    df = pd.DataFrame({
        "Date": daily['time'],
        "Temp_Max": daily['temperature_2m_max'],
        "Rain (mm)": daily['precipitation_sum'],
        "ETo (mm)": daily['et0_fao_evapotranspiration']
    })
    
    #  CALCULATE CROP WATER NEED (ETc) ---
    kc_value = CROPS[CURRENT_CROP]["kc"]
    
    # ETc = ETo * Kc
    df["Crop_Need (mm)"] = df["ETo (mm)"] * kc_value
    
    #  CALCULATE IRRIGATION REQUIREMENT ---
    # Irrigation Needed = Crop Need - Rain
    # If rain > need, irrigation is 0 (we don't suck water out of the ground!)
    df["Irrigation_Needed (mm)"] = df["Crop_Need (mm)"] - df["Rain (mm)"]
    df["Irrigation_Needed (mm)"] = df["Irrigation_Needed (mm)"].clip(lower=0) # No negative numbers

    # DISPLAY RESULTS ---
    print("\n📊 WEEKLY WATER AUDIT")
    print("-" * 60)
    print(f"Crop: {CURRENT_CROP} (Kc: {kc_value})")
    print(df[["Date", "Rain (mm)", "Crop_Need (mm)", "Irrigation_Needed (mm)"]].to_string(index=False))
    
    #  VISUALIZATION ---
    plt.figure(figsize=(10, 6))
    
    # Bar chart for water balance
    indices = range(len(df))
    width = 0.4
    
    plt.bar([i - width/2 for i in indices], df["Crop_Need (mm)"], width=width, label='Crop Thirst (ETc)', color='orange', alpha=0.7)
    plt.bar([i + width/2 for i in indices], df["Rain (mm)"], width=width, label='Rainfall', color='blue', alpha=0.7)
    
    # Highlight the "Deficit" (What you need to irrigate)
    plt.plot(indices, df["Irrigation_Needed (mm)"], color='red', marker='o', linewidth=2, label='ADD WATER (Irrigation)')
    
    plt.xticks(indices, df["Date"], rotation=45)
    plt.ylabel("Water (mm)")
    plt.title(f"Smart Irrigation Schedule: {LOCATION['name']}\nCrop: {CURRENT_CROP}")
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig("Irrigation_Plan.png")
    print(f"\n💾 Chart saved as 'Irrigation_Plan.png'")
    plt.show()

except Exception as e:
    print(f"❌ Error fetching weather data: {e}")