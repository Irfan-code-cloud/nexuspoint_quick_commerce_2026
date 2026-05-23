import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import time
import json
import datetime
from streamlit_folium import st_folium

# --- FIX 1: Page Config MUST be the very first Streamlit command ---
st.set_page_config(
    layout="wide",
    page_title="Nexus Point | Quick Commerce Optimization",
    page_icon=":material/place:",
)

# --- FIX 2: All temp files must be saved to /tmp/ instead of data/ ---
LOCK_FILE = "/tmp/api_lock.json"


def get_quota_status():
    today = str(datetime.date.today())
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                data = json.load(f)
                if data.get("last_reset_date") != today:
                    return {"clicks": 0, "last_reset_date": today}
                return data
        except:
            pass
    return {"clicks": 0, "last_reset_date": today}


def save_quota_status(clicks, last_reset_date):
    with open(LOCK_FILE, "w") as f:
        json.dump({"clicks": clicks, "last_reset_date": last_reset_date}, f)


def validate_and_load_csv(uploaded_file, required_columns):
    try:
        df = pd.read_csv(uploaded_file)
        if not all(col in df.columns for col in required_columns):
            return (
                None,
                f"Missing required columns. Expected: {', '.join(required_columns)}",
            )
        if len(df) > 50000:
            return (
                None,
                "⚠️ Dataset exceeds optimization limit (50,000 rows). Please upload a smaller dataset.",
            )
        elif len(df) > 20000:
            df = df.sample(n=20000, random_state=42)
        return df, "Success"
    except Exception as e:
        return None, f"Invalid file format: {e}"


# Import our custom modules
from src.engine import find_optimal_locations
from ui.map_factory import generate_cluster_map, add_competitor_layer
from src.ai_analyst import generate_store_strategy

# Bulletproof Session State Initialization
if "user_ai_clicks" not in st.session_state:
    st.session_state.user_ai_clicks = 0
if "ai_click_count" not in st.session_state:
    st.session_state.ai_click_count = 0
if "ai_last_click_time" not in st.session_state:
    st.session_state.ai_last_click_time = 0.0
if "orders_df" not in st.session_state:
    st.session_state.orders_df = None
if "properties_df" not in st.session_state:
    st.session_state.properties_df = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# --- FIX 2: Read from /tmp/ ---
if st.session_state.orders_df is None and os.path.exists("/tmp/.temp_orders.csv"):
    st.session_state.orders_df = pd.read_csv("/tmp/.temp_orders.csv")

if st.session_state.properties_df is None and os.path.exists(
    "/tmp/.temp_properties.csv"
):
    st.session_state.properties_df = pd.read_csv("/tmp/.temp_properties.csv")

with open("ui/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Main Header
st.title("Nexus Point | Quick Commerce Optimization")
st.markdown(
    "Mission Control Dashboard Dynamically optimize and visualize dark store locations based on demand density."
)

# Sidebar UI
st.sidebar.header("Control Panel")
st.sidebar.subheader("Data Source")

if st.session_state.orders_df is None:
    orders_file = st.sidebar.file_uploader(
        "Upload Demand (Orders CSV)",
        type=["csv"],
        key=f"orders_{st.session_state.uploader_key}",
    )
    if orders_file is not None:
        df, status = validate_and_load_csv(orders_file, ["Latitude", "Longitude"])
        if df is not None:
            # --- FIX 2: Write to /tmp/ ---
            df.to_csv("/tmp/.temp_orders.csv", index=False)
            st.session_state.orders_df = df
            st.rerun()
        else:
            st.sidebar.error(status)
else:
    with st.sidebar.container(border=True):
        st.markdown("**:material/lock: Demand Data Locked**")

if st.session_state.properties_df is None:
    properties_file = st.sidebar.file_uploader(
        "Upload Supply (Properties CSV)",
        type=["csv"],
        key=f"props_{st.session_state.uploader_key}",
    )
    if properties_file is not None:
        df, status = validate_and_load_csv(
            properties_file, ["Property_ID", "Latitude", "Longitude", "Rent_PKR"]
        )
        if df is not None:
            # --- FIX 2: Write to /tmp/ ---
            df.to_csv("/tmp/.temp_properties.csv", index=False)
            st.session_state.properties_df = df
            st.rerun()
        else:
            st.sidebar.error(status)
else:
    with st.sidebar.container(border=True):
        st.markdown("**:material/lock: Supply Data Locked**")

if (
    st.session_state.orders_df is not None
    and st.session_state.properties_df is not None
):
    st.sidebar.success(
        f"Loaded {len(st.session_state.orders_df)} total orders & {len(st.session_state.properties_df)} properties."
    )


@st.dialog("Confirm Deletion")
def confirm_clear_data():
    st.warning(
        "Are you sure you want to clear everything? This will permanently delete the uploaded session data and cannot be undone.",
        icon="⚠️",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", type="secondary", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Delete Data", type="primary", use_container_width=True):
            # --- FIX 2: Delete from /tmp/ ---
            if os.path.exists("/tmp/.temp_orders.csv"):
                os.remove("/tmp/.temp_orders.csv")
            if os.path.exists("/tmp/.temp_properties.csv"):
                os.remove("/tmp/.temp_properties.csv")
            st.session_state.orders_df = None
            st.session_state.properties_df = None
            st.session_state.uploader_key += 1
            st.cache_resource.clear()
            st.rerun()


if st.sidebar.button("Clear All Data", type="primary"):
    confirm_clear_data()

st.sidebar.markdown("---")

if (
    st.session_state.orders_df is not None
    and st.session_state.properties_df is not None
):
    orders_df = st.session_state.orders_df.copy()
    properties_df = st.session_state.properties_df.copy()

    st.sidebar.subheader(":material/filter_alt: Order Filters")
    if "Category" in orders_df.columns:
        available_categories = sorted(orders_df["Category"].dropna().unique())
        selected_categories = st.sidebar.multiselect(
            "Order Categories", options=available_categories, default=[]
        )
        if selected_categories:
            orders_df = orders_df[orders_df["Category"].isin(selected_categories)]
    st.sidebar.markdown("---")
else:
    st.info(
        "Please upload both Demand (orders.csv) and Supply (properties.csv) to continue."
    )
    st.stop()

st.sidebar.markdown("### :material/domain: Network Expansion")
target_facilities = st.sidebar.slider(
    "Target Active Facilities", min_value=1, max_value=10, value=3, step=1
)

st.sidebar.markdown("### :material/tune: Sensitivity Analysis")
aov = st.sidebar.slider(
    "Average Order Value",
    min_value=500,
    max_value=3000,
    value=1500,
    step=50,
    format="PKR %d",
)
rider_fee = st.sidebar.slider(
    "Rider Delivery Fee",
    min_value=50,
    max_value=300,
    value=100,
    step=10,
    format="PKR %d",
)
fixed_opex = st.sidebar.slider(
    "Fixed Store OPEX",
    min_value=100000,
    max_value=1000000,
    value=300000,
    step=50000,
    format="PKR %d",
)
deliveries_per_hour = st.sidebar.slider(
    "Deliveries per Rider (per Hour)", min_value=1, max_value=8, value=3, step=1
)


@st.cache_resource(show_spinner=False)
def get_cached_locations(
    orders_df, properties_df, target_facilities, aov, rider_fee, fixed_opex
):
    return find_optimal_locations(
        orders_df, properties_df, target_facilities, aov, rider_fee, fixed_opex
    )


with st.spinner("Calculating optimal spatial clusters..."):
    if len(orders_df) == 0:
        st.error("No orders found for the selected filters.")
        st.stop()
    safe_target = min(target_facilities, len(orders_df))
    store_locations, clustered_df = get_cached_locations(
        orders_df, properties_df, safe_target, aov, rider_fee, fixed_opex
    )

locations_df = pd.DataFrame(store_locations)

st.markdown("### Executive Network KPIs")
st.info(
    "Nexus Point leverages K-Means clustering and AI forecasting to maximize network efficiency. The metrics below represent the real-time financial and operational health of your delivery ecosystem, calculated after factoring in product COGS, rider fees, and fixed store OPEX."
)

total_network_profit = locations_df["Projected_Monthly_Profit"].sum()
blended_cost_per_order = locations_df["Cost_Per_Order"].mean()
total_daily_capacity = locations_df["Max_Daily_Orders"].sum()
total_break_even = locations_df["Break_Even_Orders"].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Projected Profit",
        f"PKR {total_network_profit:,.0f}",
        delta="14% vs Market Average",
        help="Net earnings after all expenses.",
    )
with col2:
    st.metric(
        "Blended Cost/Order",
        f"PKR {blended_cost_per_order:,.2f}",
        delta="-12 PKR vs Competitor",
        delta_color="inverse",
        help="Average logistics cost to fulfill one order.",
    )
with col3:
    st.metric(
        "Total Daily Capacity",
        f"{total_daily_capacity:,.0f} Orders",
        delta="Optimized Volume",
        help=f"Maximum orders the current {target_facilities}-hub network can handle.",
    )
with col4:
    st.metric(
        "Network Break-Even",
        f"{total_break_even:,.0f} Orders/Month",
        delta="-5% Efficiency Gain",
        delta_color="inverse",
        help="Minimum monthly orders required to cover all fixed costs.",
    )

st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

with st.expander(":material/checklist: Simple Network Planner (Checklist)"):
    st.write(
        "Toggle facilities on or off and adjust expected daily orders to see how it impacts the selected network."
    )
    live_network_profit = 0
    live_break_even = 0
    live_daily_capacity = 0
    gross_profit_per_order = aov * 0.25
    dynamic_margin = gross_profit_per_order - rider_fee
    base_fixed_costs = fixed_opex

    for idx, row in locations_df.iterrows():
        c1, c2, c3 = st.columns([1, 3, 2])
        with c1:
            is_active = st.checkbox("Active", value=True, key=f"active_{idx}")
        with c2:
            st.markdown(f"**{row['Location_Name']}** (ID: {row['Store_ID']})")
        with c3:
            daily_orders = st.number_input(
                "Daily Orders",
                value=500,
                step=50,
                key=f"orders_{idx}",
                label_visibility="collapsed",
            )

        if is_active:
            fixed_costs = row["Rent_PKR"] + base_fixed_costs
            monthly_orders = daily_orders * 30
            store_profit = (monthly_orders * dynamic_margin) - fixed_costs
            live_network_profit += store_profit
            live_break_even += fixed_costs / dynamic_margin if dynamic_margin > 0 else 0
            live_daily_capacity += daily_orders

    def neutral_metric_card(label, value):
        return f"""
        <div style="border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 15px; background-color: transparent; margin-bottom: 20px;">
            <p style="font-size: 14px; color: #a1a1aa; margin: 0; padding-bottom: 5px;">{label}</p>
            <h3 style="font-size: 24px; color: white; margin: 0; font-weight: 600;">{value}</h3>
        </div>
        """

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            neutral_metric_card(
                "Live Network Profit", f"PKR {live_network_profit:,.0f}"
            ),
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            neutral_metric_card(
                "Live Break-Even", f"{live_break_even:,.0f} Orders/Month"
            ),
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            neutral_metric_card(
                "Live Daily Capacity", f"{live_daily_capacity:,.0f} Orders"
            ),
            unsafe_allow_html=True,
        )

col_map1, col_map2 = st.columns([0.8, 0.2])
with col_map1:
    st.markdown("### :material/radar: AI Spatial Anomaly Detection")
with col_map2:
    detect_anomalies = st.toggle("Activate AI Surge Detection", value=False)

if detect_anomalies:
    st.error(
        "AI Alert: Localized demand anomalies detected. High probability of flash surge.",
        icon=":material/warning:",
    )

m = generate_cluster_map(clustered_df, store_locations)
m = add_competitor_layer(m, store_locations)

if detect_anomalies:
    from src.engine import detect_spatial_anomalies
    from ui.map_factory import add_anomaly_layer

    anomalies_df = detect_spatial_anomalies(clustered_df)
    m = add_anomaly_layer(m, anomalies_df)

with st.container(border=True):
    st.markdown(
        """
    **Quick Guide:**
    * **The Colors (Heatmap):** Shows where the most orders are coming from right now. Red means very busy.
    * **The Stars:** The smartest places to open a delivery hub based on where the customers are.
    * **The Red Outlines:** Shows exactly how far a rider can travel from the hub in just a few minutes.
    """
    )

st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
st_folium(m, use_container_width=True, height=550, returned_objects=[])

st.markdown("### Operations & Risk Analytics")
tab1, tab2 = st.tabs(
    [
        ":material/location_on: Proposed Facility Coordinates",
        ":material/security: Threat Assessment",
    ]
)

with tab1:
    st.caption(
        "These locations represent the exact geometric center of highest local demand (K-Means Centroids)."
    )
    display_df = locations_df[
        [
            "Store_ID",
            "Location_Name",
            "Rent_PKR",
            "Total_Monthly_Cost",
            "Projected_Monthly_Profit",
            "Cost_Per_Order",
            "Break_Even_Orders",
            "Competitor_Threat",
        ]
    ].copy()
    display_df["Rent_PKR"] = display_df["Rent_PKR"].apply(lambda x: f"PKR {x:,.0f}")
    display_df["Total_Monthly_Cost"] = display_df["Total_Monthly_Cost"].apply(
        lambda x: f"PKR {x:,.0f}"
    )
    display_df["Projected_Monthly_Profit"] = display_df[
        "Projected_Monthly_Profit"
    ].apply(lambda x: f"PKR {x:,.0f}")
    display_df["Cost_Per_Order"] = display_df["Cost_Per_Order"].apply(
        lambda x: f"PKR {x:,.2f}"
    )
    display_df["Break_Even_Orders"] = display_df["Break_Even_Orders"].apply(
        lambda x: f"{x:,.0f} Orders"
    )
    display_df.columns = [
        "Store_ID",
        "Location",
        "Rent",
        "Monthly Cost",
        "Proj. Profit",
        "Cost/Order",
        "Break-Even",
        "Competitor Threat",
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab2:
    st.info(
        ":material/gpp_maybe: **Threat View Active:** Evaluating local competitor risks and market coverage"
    )
    from src.engine import calculate_defection_risk, load_competitor_data

    comp_df = load_competitor_data()
    risk_df = calculate_defection_risk(clustered_df, store_locations, comp_df)
    st.dataframe(risk_df, use_container_width=True, hide_index=True)

st.markdown("### :material/lightbulb: AI Location Insights")
store_options = [f"Store {store['Store_ID']}" for store in store_locations]
selected_store_name = st.selectbox("Select a Dark Store to analyze", store_options)

if selected_store_name:
    store_id = int(selected_store_name.split()[1])
    selected_store = next(s for s in store_locations if s["Store_ID"] == store_id)
    location_name = selected_store["Location_Name"]
    lat = selected_store["Lat"]
    lon = selected_store["Lon"]

    cluster_data = clustered_df[clustered_df["Cluster_ID"] == store_id]
    order_count = len(cluster_data)
    top_category = (
        cluster_data["Category"].mode()[0] if not cluster_data.empty else "Unknown"
    )
    projected_profit = selected_store["Projected_Monthly_Profit"]
    total_cost = selected_store["Total_Monthly_Cost"]
    cost_per_order = selected_store["Cost_Per_Order"]
    break_even_orders = selected_store["Break_Even_Orders"]
    competitor_threat = selected_store["Competitor_Threat"]

    quota = get_quota_status()
    global_clicks = quota.get("clicks", 0)
    user_clicks = st.session_state.user_ai_clicks

    if global_clicks >= 100:
        st.error(
            ":material/hourglass_bottom: Daily Global API Limit Reached. Please try again tomorrow."
        )
        st.button("Generate Strategy Card", disabled=True)
    elif user_clicks >= 5:
        st.warning(":material/lock: Personal Preview Limit Reached.")
        st.button("Generate Strategy Card", disabled=True)
    else:
        if st.button("Generate Strategy Card"):
            from src.engine import generate_hourly_forecast

            forecast_data = generate_hourly_forecast()
            with st.spinner("Consulting AI Expert..."):
                try:
                    strategy = generate_store_strategy(
                        location_name,
                        lat,
                        lon,
                        order_count,
                        top_category,
                        projected_profit,
                        total_cost,
                        cost_per_order,
                        break_even_orders,
                        forecast_data,
                        competitor_threat,
                    )
                    st.success(":material/task_alt: AI Analysis Complete!")
                    with st.container(border=True):
                        st.markdown(strategy)
                    quota["clicks"] += 1
                    st.session_state.user_ai_clicks += 1
                    save_quota_status(quota["clicks"], quota["last_reset_date"])
                except Exception as e:
                    st.error(f"Error calling Vertex AI: {e}")

col_chart1, col_chart2 = st.columns([0.8, 0.2])
with col_chart1:
    st.markdown("### :material/moped: Operations: Hourly Rider Fleet Scheduling")
with col_chart2:
    ai_forecast_enabled = st.toggle("Enable AI 24-Hour Forecast", value=False)

from src.engine import generate_hourly_forecast, generate_predictive_forecast
import numpy as np

with st.container(border=True):
    st.markdown(
        """
    **Quick Guide:**
    * **Bar Chart (Standard Mode):** Shows exactly how many delivery riders we usually need each hour based on past data.
    * **Line Chart (AI Mode):** Predicts how many orders we will get tomorrow, so we can plan our staffing ahead of time.
    * **Shaded Area:** Shows the "safe zone" even if orders suddenly spike, they will likely stay within this shaded range.
    """
    )

with st.container(border=True):
    if ai_forecast_enabled:
        from ui.chart_factory import render_predictive_forecast_chart

        predictive_df = generate_predictive_forecast(aov, day_of_week="Monday")
        st.plotly_chart(
            render_predictive_forecast_chart(predictive_df), use_container_width=True
        )
    else:
        forecast_data = generate_hourly_forecast()
        forecast_df = pd.DataFrame(
            list(forecast_data.items()), columns=["Hour", "Predicted Orders"]
        ).set_index("Hour")
        forecast_df["Required_Riders"] = np.ceil(
            forecast_df["Predicted Orders"] / deliveries_per_hour
        )
        import plotly.express as px

        fig = px.bar(
            forecast_df.reset_index(),
            x="Hour",
            y="Required_Riders",
            template="plotly_dark",
            labels={
                "Hour": "Time of Day",
                "Required_Riders": "Required Delivery Riders",
            },
        )
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>Required Riders: %{y}<extra></extra>"
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E0E0E0"),
            margin=dict(l=40, r=40, t=40, b=40),
            hoverlabel=dict(bgcolor="#262730", font_size=14, font_family="Segoe UI"),
        )
        st.plotly_chart(fig, use_container_width=True)

if "Category" in orders_df.columns:
    st.markdown("")
    st.write("")
    st.markdown("### :material/category: Product Category Analysis")
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "Strategic Inventory & Revenue Audit: Compare unit velocity (Bar) against revenue weight (Pie). If a category has high volume but low revenue contribution, it indicates a need for premium upsells or price adjustments."
    )
    import plotly.express as px

    col1, col2 = st.columns(2)
    category_colors = {
        "Grocery": "#636EFA",
        "Personal Care": "#00CC96",
        "Pharmacy": "#19D3F3",
        "Snacks": "#AB63FA",
    }

    with col1:
        with st.container(border=True):
            st.markdown("### Order Volume by Category")
            category_counts = orders_df["Category"].value_counts().reset_index()
            category_counts.columns = ["Category", "Order Count"]
            fig_cat = px.bar(
                category_counts,
                y="Category",
                x="Order Count",
                orientation="h",
                template="plotly_dark",
                color_discrete_sequence=["#00CC96"],
                category_orders={
                    "Category": ["Grocery", "Personal Care", "Pharmacy", "Snacks"]
                },
                hover_data=["Order Count"],
            )
            fig_cat.update_traces(
                marker_line_color="rgb(8,48,107)",
                marker_line_width=1.5,
                hovertemplate="<b>%{y}</b><br>Total Orders: %{x}<extra></extra>",
            )
            fig_cat.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E0E0E0"),
                margin=dict(t=40, b=40, l=20, r=20),
                showlegend=False,
                bargap=0.4,
                height=400,
                yaxis_title=None,
                hoverlabel=dict(
                    bgcolor="#262730", font_size=14, font_family="Segoe UI"
                ),
            )
            fig_cat.update_xaxes(showgrid=False)
            st.plotly_chart(fig_cat, use_container_width=True)
            st.markdown(
                "<p style='font-size: 12px; color: #888;'>Note: Volume metrics represent total successful transactions per category cluster.</p>",
                unsafe_allow_html=True,
            )

    with col2:
        with st.container(border=True):
            st.markdown("### Revenue Distribution (%)")
            if "Order_Value_PKR" in orders_df.columns:
                revenue_counts = (
                    orders_df.groupby("Category")["Order_Value_PKR"].sum().reset_index()
                )
                val_col = "Order_Value_PKR"
            else:
                revenue_counts = category_counts
                val_col = "Order Count"
            fig_pie = px.pie(
                revenue_counts,
                names="Category",
                values=val_col,
                hole=0,
                template="plotly_dark",
                color="Category",
                color_discrete_map=category_colors,
                hover_data=[val_col],
            )
            fig_pie.update_traces(
                hovertemplate="<b>%{label}</b><br>Revenue: PKR %{value:,.0f}<br>Share: %{percent}<extra></extra>"
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E0E0E0"),
                margin=dict(t=40, b=80, l=20, r=20),
                height=400,
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5
                ),
                hoverlabel=dict(
                    bgcolor="#262730", font_size=14, font_family="Segoe UI"
                ),
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown(
                "<p style='font-size: 12px; color: #888;'>Note: Percentages reflect gross revenue share before operating costs and rider fees.</p>",
                unsafe_allow_html=True,
            )

st.markdown(
    """
<div class="footer-container">
    <p>&copy; 2026 Nexus Point | Engineered by Irfan Khattak</p>
    <div class="footer-icons">
        <a href="mailto:ifnkhatta@outlook.com" class="footer-icon-link" target="_blank" rel="noopener noreferrer" title="Email">
            <svg viewBox="0 0 24 24"><path d="M20 4H4C2.9 4 2.01 4.9 2.01 6L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
        </a>
        <a href="https://github.com/Irfan-code-cloud" class="footer-icon-link" target="_blank" rel="noopener noreferrer" title="GitHub">
            <svg viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
        </a>
        <a href="https://www.linkedin.com/in/irfan-khattak-00b847251/" class="footer-icon-link" target="_blank" rel="noopener noreferrer" title="LinkedIn">
            <svg viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
        </a>
    </div>
</div>
""",
    unsafe_allow_html=True,
)
