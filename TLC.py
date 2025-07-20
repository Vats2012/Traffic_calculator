import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# ------------------ CONFIGURATION ------------------
OPENWEATHER_API_KEY = "618c7fd2f96a71d99cacc4b1b905ecc5"

# ------------------ SETUP ------------------
st.set_page_config(layout="wide")
st_autorefresh(interval=300000, key="trafficdatarefresh")  # every 5 min
st.title("🛣️ Custom Location Traffic + Weather Forecast")

# ------------------ USER COORDINATE INPUT ------------------
st.sidebar.header("📌 Location Selector")

default_lat = 28.6139
default_lon = 77.2090

lat = st.sidebar.number_input("Latitude", value=default_lat, format="%.4f")
lon = st.sidebar.number_input("Longitude", value=default_lon, format="%.4f")
get_data = st.sidebar.button("Get Forecast")

# ------------------ FETCH LOCATION NAME ------------------
@st.cache_data(show_spinner=False)
def get_location_name(lat, lon):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "DelhiTrafficApp/1.0"}
        )
        data = response.json()
        return data.get("display_name", "Unknown Location")
    except:
        return "Unknown Location"

if get_data:
    st.session_state["coords"] = (lat, lon)

# Use current or session-stored coordinates
if "coords" in st.session_state:
    lat, lon = st.session_state["coords"]
else:
    lat, lon = default_lat, default_lon

location = get_location_name(lat, lon)
st.subheader(f"📍 Location: {location}")
st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))

# ------------------ LAST UPDATED ------------------
if "last_updated" not in st.session_state:
    st.session_state["last_updated"] = datetime.now()

time_diff = datetime.now() - st.session_state["last_updated"]
st.markdown(f"🕒 **Last updated: {int(time_diff.total_seconds() // 60)} minute(s) ago**")
st.session_state["last_updated"] = datetime.now()

# ------------------ WEATHER FETCH ------------------
def get_weather_data(lat, lon, api_key):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return []
        return response.json()["list"]
    except Exception:
        st.error("❌ Could not fetch weather data.")
        return []

# ------------------ SIMULATED TRAFFIC FUNCTION ------------------
def simulate_traffic(hour, day_of_week, weather_desc):
    peak_hours = 8 <= hour <= 11 or 17 <= hour <= 20
    moderate_hours = 6 <= hour < 8 or 20 < hour <= 22

    # Base traffic
    if peak_hours:
        traffic = 80 + hour % 10
    elif moderate_hours:
        traffic = 50 + hour % 5
    else:
        traffic = 20 + hour % 5

    if traffic > 20 and "rain" in weather_desc.lower():
        traffic += 15

    if day_of_week >= 5:
        traffic -= 10

    return max(traffic, 0)

# ------------------ DURATION SLIDER ------------------
duration = st.slider("⏱️ Forecast Duration (Hours)", 3, 24, 12, step=3)

# ------------------ FETCH FORECAST & SIMULATE ------------------
forecast = get_weather_data(lat, lon, OPENWEATHER_API_KEY)

hours = []
traffic = []
temperatures = []

for i in range(duration):
    current_time = datetime.now() + timedelta(hours=i)
    hour_str = current_time.strftime("%H:%M")
    hours.append(hour_str)

    weather_desc = "clear"
    temp = None

    if forecast:
        try:
            closest = min(forecast, key=lambda x: abs(datetime.fromtimestamp(x["dt"]) - current_time))
            temp = closest["main"]["temp"]
            weather_desc = closest["weather"][0]["description"]
        except Exception:
            weather_desc = "clear"
            temp = None

    temperatures.append(temp)
    traffic_level = simulate_traffic(current_time.hour, current_time.weekday(), weather_desc)
    traffic.append(traffic_level)

# ------------------ PLOTTING ------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=hours,
    y=traffic,
    mode="lines+markers",
    name="Traffic Level",
    line=dict(color="red", width=3)
))

fig.add_trace(go.Scatter(
    x=hours,
    y=temperatures,
    mode="lines+markers",
    name="Temperature (°C)",
    line=dict(color="blue", width=3),
    yaxis="y2"
))

fig.update_layout(
    title="🚗 Traffic & 🌡️ Temperature Forecast",
    xaxis_title="Time (Hour)",
    yaxis=dict(
        title=dict(text="Traffic Level", font=dict(color="red")),
        tickfont=dict(color="red")
    ),
    yaxis2=dict(
        title=dict(text="Temperature (°C)", font=dict(color="blue")),
        tickfont=dict(color="blue"),
        overlaying="y",
        side="right"
    ),
    width=1300,
    height=550,
    margin=dict(l=40, r=40, t=60, b=40),
    legend=dict(x=0.01, y=0.99)
)

st.plotly_chart(fig, use_container_width=True)
