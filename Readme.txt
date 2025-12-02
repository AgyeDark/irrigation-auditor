🌾 FAO-56 Smart Irrigation Auditor

Precision Agriculture Tool for Northern Ghana Irrigation Schemes.

🎯 Overview

Farmers in irrigation schemes like Tono and Vea often irrigate based on intuition or rigid schedules, leading to water wastage or crop stress. This application automates the FAO-56 Penman-Monteith method to calculate exact daily water requirements ($ET_c$) using live satellite weather data.

🚀 Features

Live Weather Data: Connects to the Open-Meteo API for real-time solar radiation, temperature, and humidity data.

Crop Database: Includes Kc (Crop Coefficients) for major Ghanaian crops (Maize, Rice, Tomato, Yam, Banana).

Pump Calculator: Converts "mm of water needed" into exact "Hours of Pumping" based on field size and pump capacity.

7-Day Audit: Visualizes the water balance (Rain vs. Evapotranspiration) to help farmers plan ahead.

🛠️ Installation

Clone the repository:

git clone [https://github.com/YOUR_USERNAME/irrigation-auditor.git](https://github.com/YOUR_USERNAME/irrigation-auditor.git)
cd irrigation-auditor


Install dependencies:

pip install -r requirements.txt


Run the App:

streamlit run irrigation_app.py


📊 The Science

The tool uses the standard FAO water balance equation:

$$ ET_c = ET_o \times K_c $$

Where:

$ET_o$: Reference Evapotranspiration (from Satellite).

$K_c$: Crop Coefficient (varies by growth stage).

📍 Supported Locations

Tono Dam (Navrongo)

Vea Dam (Bolgatanga)

Bontanga (Tamale)

Asutsuare (Banana Hub)

Custom Locations (Lat/Lon)

📄 License

Open Source for Agricultural Research.