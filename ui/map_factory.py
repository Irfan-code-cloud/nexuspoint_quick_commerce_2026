import folium
from folium.plugins import HeatMap
import requests
import os
import streamlit as st
import numpy as np
from dotenv import load_dotenv

load_dotenv()


@st.cache_data(show_spinner=False)
def get_isochrone(lat, lon):
    api_key = os.getenv("ORS_API_KEY")
    if not api_key:
        return None

    url = "https://api.openrouteservice.org/v2/isochrones/driving-car"
    headers = {"Authorization": api_key}
    payload = {"locations": [[lon, lat]], "range": [600]}

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"ORS API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"ORS Request Failed: {e}")
        return None


def generate_cluster_map(orders_df, store_locations):
    """
    Generates a Folium map visualizing order demand density and proposed dark store locations.
    """
    import folium
    from folium.plugins import HeatMap
    import math
    import numpy as np

    # Initialize a completely fresh map every time
    m = folium.Map(location=[24.8607, 67.0011], zoom_start=12, tiles="OpenStreetMap")
    
    # Inject the dark mode CSS directly into the map's internal HTML structure
    dark_mode_css = """
    <style>
    .leaflet-tile-pane {
        filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%);
    }
    .leaflet-control-attribution {
        filter: invert(100%) brightness(80%);
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(dark_mode_css))

    # 2. Add Demand Layer (HeatMap)
    if orders_df is not None and not orders_df.empty:
        heat_data = orders_df[["Latitude", "Longitude"]].values.tolist()
        HeatMap(heat_data, radius=12, blur=10).add_to(m)

    # 3. Add Supply Layer (Dark Stores)
    if store_locations:
        # THE FIX: Iterate as a standard list, NO .iterrows()
        for store in store_locations:

            # THE FIX: Bulletproof data extraction using .get()
            lat = store.get("Lat", store.get("Latitude"))
            lon = store.get("Lon", store.get("Longitude"))
            store_id = store.get("Store_ID", "Unknown")

            prop_id = store.get("Property_ID", "Unknown")
            rent = store.get("Rent_PKR", "Unknown")

            location_name = store.get("Location_Name", "Unknown Location")
            sq_ft = store.get("Square_Footage", "Unknown")
            max_orders = store.get("Max_Daily_Orders", "Unknown")

            rent_str = f"{rent:,.0f}" if isinstance(rent, (int, float)) else str(rent)

            # Extract new KPI variables
            expected_volume = (
                len(orders_df[orders_df["Cluster_ID"] == store_id])
                if "Cluster_ID" in orders_df.columns
                else "Unknown"
            )
            proj_profit = store.get("Projected_Monthly_Profit", 0)
            profit_str = (
                f"{proj_profit:,.0f}"
                if isinstance(proj_profit, (int, float))
                else str(proj_profit)
            )
            threat_level = store.get("Competitor_Threat", "Unknown")

            # YOUR ORIGINAL CUSTOM UI CARD (Untouched!)
            # YOUR CUSTOM UI CARD WITH FULL HTML WRAPPER
            # YOUR CUSTOM UI CARD (Clean, Native, and Formatted)
            store_html = f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 5px; min-width: 220px;">
                <div style="background-color: #2e7d32; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-bottom: 8px; display: inline-block; letter-spacing: 0.5px;">
                    <i class="fa fa-bolt" style="margin-right: 4px;"></i> PROPOSED HUB
                </div>
                <h4 style="margin-top: 0; margin-bottom: 8px; color: #333; font-size: 15px;">Dark Store {store_id}</h4>
                <div style="border-top: 1px solid #eee; padding-top: 8px;">
                    <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Location:</b> {location_name}</p>
                    
                    <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Capacity:</b> {sq_ft:,} sq ft</p>
                    <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Expected Volume:</b> {expected_volume:,} Orders</p>
                    
                    <p style="margin: 4px 0; font-size: 13px; color: #2e7d32; font-weight: 600;"><b>Rent:</b> PKR {rent_str}</p>
                    <p style="margin: 4px 0; font-size: 13px; color: #2e7d32; font-weight: 600;"><b>Proj. Profit:</b> PKR {profit_str}</p>
                    <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Threat Level:</b> {threat_level}</p>
                </div>
            </div>
            """

            # --- THE POLYGON FIX: Smart Isochrones with Circle Fallback ---
            # Attempt to get real driving distance polygons (10-minute drive time)
            iso_data = get_isochrone(lat, lon)

            if iso_data:
                # If the API works, draw a beautiful real-world delivery zone
                folium.GeoJson(
                    iso_data,
                    style_function=lambda x: {
                        "fillColor": "#ff0000",
                        "color": "#ff0000",
                        "weight": 2,
                        "fillOpacity": 0.15,
                    },
                ).add_to(m)
            else:
                # Fallback: Draw a perfect 1.5km radius circle if the API is missing/fails
                folium.Circle(
                    location=[lat, lon],
                    radius=1500,  # 1.5km in meters
                    color="red",
                    fill_color="red",  # Explicitly declaring fill_color fixes Folium rendering bugs!
                    weight=2,
                    fill=True,
                    fill_opacity=0.15,
                ).add_to(m)

            # Add a distinct marker for the Dark Store
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(store_html, max_width=300),
                tooltip="Click for Property Details",
                icon=folium.Icon(color="red", icon="star"),
            ).add_to(m)

        # Auto-Zoom to fit all generated stars perfectly
        try:
            m.fit_bounds(m.get_bounds())
        except:
            pass

    return m

    geojson_data = None
    try:
        # Attempt to fetch live isochrone from OpenRouteService
        geojson_data = get_isochrone(lat, lon)
    except Exception as e:
        print(f"Failed to fetch isochrone: {e}")

    if geojson_data:
        # Live Isochrone via ORS API
        folium.GeoJson(
            geojson_data,
            style_function=lambda feature: {
                "fillColor": "#FF5733",
                "color": "red",
                "weight": 1,
                "fillOpacity": 0.2,
            },
        ).add_to(m)
    else:
        # Offline Fallback: Compute a 2km spatial buffer using geospatial math
        # This prevents the dashboard from crashing or missing coverage areas if the API rate-limits
        radius_km = 2.0
        num_points = 60
        angles = np.linspace(0, 2 * math.pi, num_points)

        # 1 degree of latitude is approximately 111.32 km
        # 1 degree of longitude is approximately 40075 * cos(lat) / 360 km
        lat_offsets = (radius_km / 111.32) * np.sin(angles)
        lon_offsets = (
            radius_km / ((40075 * math.cos(math.radians(lat))) / 360)
        ) * np.cos(angles)

        polygon_locations = []
        for dlat, dlon in zip(lat_offsets, lon_offsets):
            polygon_locations.append([lat + dlat, lon + dlon])

        folium.Polygon(
            locations=polygon_locations,
            color="#FF5733",
            fill=True,
            fill_color="#FF5733",
            fill_opacity=0.2,
            weight=2,
        ).add_to(m)

    m.fit_bounds(m.get_bounds())
    return m


def add_competitor_layer(m, store_locations):
    """
    Plots competitor locations on the map and calculates the actual distance
    to the nearest proposed dark store.
    """
    from src.engine import load_competitor_data
    import folium
    import math

    comp_df = load_competitor_data()

    # Mathematical formula to calculate real distance between GPS coordinates in km
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0  # Earth radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    for _, row in comp_df.iterrows():
        brand = row["Brand"]
        name = row["Name"]
        c_lat = row["Latitude"]
        c_lon = row["Longitude"]

        # Calculate distance to the closest proposed dark store
        min_distance = min(
            [haversine(c_lat, c_lon, s["Lat"], s["Lon"]) for s in store_locations]
        )

        # Extract or Mock Strategic Intelligence Metrics
        sla = row.get("Est_Delivery_SLA", "15-20 mins")
        market_share = row.get("Local_Market_Share", "~35%")
        radius_overlap = row.get("Radius_Overlap", "High - 60% zone collision")

        # Enhanced Enterprise Threat Intel Popup
        popup_html = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 5px; min-width: 220px;">
            <div style="background-color: #ff9800; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-bottom: 8px; display: inline-block; letter-spacing: 0.5px;">
                <i class="fa fa-exclamation-triangle" style="margin-right: 4px;"></i> KNOWN COMPETITOR
            </div>
            <h4 style="margin-top: 0; margin-bottom: 8px; color: #333; font-size: 15px;">{brand}</h4>
            <div style="border-top: 1px solid #eee; padding-top: 8px;">
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Branch:</b> {name}</p>
                <p style="margin: 4px 0; font-size: 13px; color: #d32f2f; font-weight: 600;"><b>Status:</b> Active Threat</p>
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Distance to Our Hub:</b> {min_distance:.1f} km</p>
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Est. Delivery SLA:</b> {sla}</p>
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Local Market Share:</b> {market_share}</p>
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Radius Overlap:</b> {radius_overlap}</p>
            </div>
        </div>
        """

        folium.Marker(
            location=[c_lat, c_lon],
            popup=folium.Popup(popup_html, max_width=400),
            tooltip=f"Competitor Threat: {brand}",
            icon=folium.Icon(color="black", icon="crosshairs", prefix="fa"),
        ).add_to(m)

    return m


def add_anomaly_layer(m, anomalies_df):
    """
    Plots spatial ML anomalies (surges) on the map instantly.
    Removes the slow Nominatim API to prevent UI freezing.
    """
    import folium

    for _, row in anomalies_df.iterrows():
        lat = row["Latitude"]
        lon = row["Longitude"]

        # 1. Instantly load the location name from the engine's dataframe
        # (This entirely bypasses the 15-second OpenStreetMap delay!)
        location_name = row.get("Simulated_Neighborhood", f"{lat:.4f}, {lon:.4f}")

        # 2. Load the Real Live Weather data we fetched in the engine
        reason = row.get("Surge_Reason", "Unusual demand density")
        source = row.get("Data_Source", "ML Algorithm")

        # Extract or Mock Operational Impact Metrics
        surge_intensity = row.get("Surge_Intensity", "+42% Order Velocity")
        sla_impact = row.get("SLA_Impact", "High - +10 min delay (Low Visibility)")
        action_text = row.get(
            "Action_Text", "Deploy 5 standby riders & activate hazard protocol"
        )

        # Enterprise-styled Anomaly HTML Card
        anomaly_html = f"""
        <div style="font-family: 'Google Sans', 'Poppins', sans-serif; padding: 5px; min-width: 240px;">
            <div style="background-color: #d32f2f; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-bottom: 8px; display: inline-block; letter-spacing: 0.5px;">
                <i class="fa fa-exclamation-circle" style="margin-right: 4px;"></i> AI SURGE DETECTED
            </div>
            <h4 style="margin-top: 0; margin-bottom: 8px; color: #333; font-size: 15px;">Live Context Analysis</h4>
            <div style="border-top: 1px solid #eee; padding-top: 8px;">
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Location:</b> {location_name}</p>
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Root Cause:</b> {reason}</p>
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>Surge Intensity:</b> {surge_intensity}</p>
                <p style="margin: 4px 0; font-size: 13px; color: #444;"><b>SLA Impact:</b> {sla_impact}</p>
                <p style="margin: 4px 0; font-size: 11px; color: #888;"><i>Detected via {source}</i></p>
                <p style="margin: 8px 0 0 0; font-size: 13px; color: #d32f2f; font-weight: bold;">Action: {action_text}</p>
            </div>
        </div>
        """

        # Add a high-contrast pulsing circle marker for the anomaly
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color="#FF0000",
            weight=2,
            fill=True,
            fill_color="#FF0000",
            fill_opacity=0.8,
            tooltip=f"Surge: {reason}",
            popup=folium.Popup(anomaly_html, max_width=300),
        ).add_to(m)

    return m
