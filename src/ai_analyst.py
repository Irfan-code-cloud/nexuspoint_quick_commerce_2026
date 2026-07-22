import streamlit as st
import google.generativeai as genai


def generate_store_strategy(
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
):
    """
    Generates a Quick Commerce location strategy using Gemini 2.5 Flash.
    Enforces strict Markdown formatting and sentence constraints for readability.
    """
    # Configure the free API key directly from Streamlit secrets
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # Initialize the model using the new library
    model = genai.GenerativeModel("gemini-3.6-flash")

    # Dynamic Competitor Threat Prompt Injection
    threat_instruction = ""
    if competitor_threat == "High":
        threat_instruction = "CRITICAL ALERT: This location has a HIGH Competitor Threat (nearest rival is within 1.5km). You MUST provide an aggressive, hyper-local marketing and operational strategy designed to cannibalize their market share and acquire their customers."
    else:
        threat_instruction = f"Competitor Threat Level: {competitor_threat}. Provide standard competitive positioning."

    # THE FIX: Explicitly pass the exact Location Name so it never hallucinates
    prompt = f"""
    Act as a Quick Commerce Supply Chain Expert in Karachi, Pakistan.
    We are evaluating a potential dark store location at: {location_name} (Latitude {lat}, Longitude {lon}).
    This cluster currently handles {order_count} orders, and the top-selling category is '{top_category}'.
    
    Financial Context: This location has an estimated Total Monthly Cost of PKR {total_cost:,.0f} and a Projected Monthly Profit of PKR {projected_profit:,.0f}.
    Cost Per Order: PKR {cost_per_order:,.0f} and Break-Even Point: {break_even_orders:,.0f} orders.
    Hourly Demand Forecast (next 24 hours): {forecast_data}
    
    {threat_instruction}
    
    Please provide your strategic analysis using EXACTLY the following FIVE Markdown headers. 
    
    CRITICAL CONSTRAINTS:
    1. NO PREAMBLE OR GREETINGS. Do NOT say "Good morning," do NOT introduce the analysis, and do NOT write any text before the first header. Start immediately with the first Markdown header.
    2. You must write a single, highly detailed, data-dense paragraph (3-4 sentences) under each header. 
    3. Provide actionable, enterprise-grade insights specific to Karachi's logistics and the provided metrics. 
    4. Do NOT use bullet points under any circumstances. Write with the analytical rigor of a Chief Operating Officer.

    ### :material/place: Location & Market Justification
    (Explain why this is lucrative based on the data and Karachi's context)

    ### :material/payments: Financial Economics & ROI
    (Analyze the provided financial metrics: Profit, CPO, and Break-Even)

    ### :material/local_shipping: Hyper-Local Workforce Scheduling
    (Provide peak-hour strategies based on the time-series forecast data)

    ### :material/gpp_maybe: Operational Risk Mitigation
    (Address potential risks like traffic or bottlenecks typical for this area)

    ### :material/rocket_launch: Competitor Cannibalization Strategy
    (Provide a hyper-specific, aggressive strategy to steal market share from the nearest competitor, based on the threat level provided)
    """

    response = model.generate_content(prompt)
    return response.text
