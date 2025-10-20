# frontend/app.py
import streamlit as st
import requests
import folium
import pandas as pd
from streamlit_folium import st_folium

# ---- Configuration ----
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Strava Segment Tracker", layout="wide")
st.title("🚴 My Strava Segment Tracker")
st.caption("Visualize your best PRs and all segment attempts from Strava data")

# ---- Sidebar ----
with st.sidebar:
    st.header("⚙️ Options")
    data_type = st.radio("Show data:", ["My Best PRs", "All Attempts"])
    if st.button("🔁 Update segments from Strava"):
        with st.spinner("Fetching data from Strava..."):
            resp = requests.post(f"{BACKEND_URL}/update_segments", params={"limit": 2})
            if resp.status_code == 200:
                st.success(resp.json().get("message"))
            else:
                st.error("Failed to update from backend.")

# ---- Fetch data ----
if data_type == "My Best PRs":
    endpoint = f"{BACKEND_URL}/segments"
else:
    endpoint = f"{BACKEND_URL}/debug/db"  # for all attempts we’ll extend below

try:
    if data_type == "My Best PRs":
        response = requests.get(f"{BACKEND_URL}/segments")
        data = response.json()
        df = pd.DataFrame(data)
    else:
        # temporary route to get attempts
        response = requests.get(f"{BACKEND_URL}/debug/db")
        db_stats = response.json()
        st.write("Current DB stats:", db_stats)
        st.stop()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

if len(df) == 0:
    st.warning("No records found yet. Run an update first!")
    st.stop()

# ---- Compute map center ----
avg_lat = df["start_lat"].mean()
avg_lng = df["start_lng"].mean()

m = folium.Map(location=[avg_lat, avg_lng], zoom_start=12, tiles="OpenStreetMap")

# ---- Add Markers ----
for _, row in df.iterrows():
    popup_html = f"""
    <b>{row['name']}</b><br>
    Distance: {row['distance']:.0f} m<br>
    Your PR: {row['pr_time']:.1f} s<br>
    KOM: {row['kom_time'] if row['kom_time'] else 'N/A'} s<br>
    Gap: {row['difference'] if row['difference'] else 'N/A'} s
    """
    color = "green" if row["difference"] and row["difference"] < 30 else "orange"
    folium.Marker(
        location=[row["start_lat"], row["start_lng"]],
        popup=popup_html,
        icon=folium.Icon(color=color, icon="bicycle", prefix="fa")
    ).add_to(m)

# ---- Display map ----
st_folium(m, width=1200, height=700)
