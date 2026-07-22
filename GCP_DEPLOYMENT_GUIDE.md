# ☁️ Google Cloud Platform (GCP) Deployment Guide

This guide outlines the necessary steps and code modifications required to migrate the Nexus Point architecture back to a fully managed Google Cloud Platform (GCP) environment. 

This migration transitions the AI engine from the free-tier Google AI Studio API back to **Vertex AI**, utilizing enterprise-grade service account authentication.

> 🛡️ **Security Note for Junior & Beginner Developers:** 
> This repository is structured as an architectural proof-of-concept and it is my personal project anyone can learn and clone and play with this application on his locall machine. Notice that configuration files containing sensitive API keys (such as `.env` and `.streamlit/secrets.toml`) are completely excluded from the codebase and are listed in the `.gitignore` file. In professional software engineering, **raw API keys and service account credentials must never be pushed to a public GitHub repository** to prevent unauthorized access and credential leakage. Always utilize environment variables or secure vault managers for secret injection.

---

## 🔐 Prerequisites: Authentication Files

To execute this deployment, I will need the two authentication files currently stored safely on my local machine:

1. **`credentials.json`**: The GCP Service Account key containing my project's IAM permissions.
2. **`.env`**: The environment variables file containing my GCP Project ID and Region.

> [!NOTE] 
> This NOTICE is for beginners who are deploying the projects on google cloud or push the code to github.
> **⚠️ Security Warning:** Never commit `credentials.json` or `.env` to GitHub. Ensure both are explicitly listed in your `.gitignore` file before proceeding.

### `.env` File Structure
Ensure your local `.env` file contains the following parameters:
```env
# GCP Vertex AI Configuration
GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"
GCP_PROJECT_ID="your-gcp-project-id"
GCP_REGION="us-central1"
```

# Other Required APIs
```env
ORS_API_KEY="your_openrouteservice_api_key"
OPENWEATHER_API_KEY="your_openweather_api_key"
```
## 🔗 Live Architecture
**Target GCP Project:** `Fleet-AI-Project` (`fleet-ai-project`)
**Live Cloud Run URL:** [Google Cloud RUN URL](https://nexuspoint-quick-commerce-2026-521715121219.us-central1.run.app/)

---

## 🛠️ Step 1: Reverting the Python Dependencies

Before triggering the deployment pipeline, I need to replace the lightweight generative AI SDK with the enterprise Google Cloud SDK, and restore the `python-dotenv` library so the container can read my environment variables.

I would need to Update my `requirements.txt` by swapping out `google-generativeai`:

```text
# Remove this:
# google-generativeai

# Add these:
google-cloud-aiplatform
python-dotenv
```
## 💻 Step 2: Restoring the Vertex AI Engine (`src/ai_analyst.py`)

Replace the Streamlit secrets logic with the original Vertex AI initialization block.
Update the contents of `src/ai_analyst.py` with the following code snippet:

```Python, ai_analyst.py
import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# Load environment variables from the .env file
load_dotenv()

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
    Generates a Quick Commerce location strategy using Vertex AI (Gemini Flash).
    Authenticates via local credentials.json and .env variables.
    """
    
    # Initialize Vertex AI using variables from the .env file
    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("GCP_REGION")
    vertexai.init(project=project_id, location=location)
    
    # Initialize the enterprise model
    model = GenerativeModel("gemini-1.5-flash")

    # Dynamic Competitor Threat Prompt Injection
    threat_instruction = ""
    if competitor_threat == "High":
        threat_instruction = "CRITICAL ALERT: This location has a HIGH Competitor Threat (nearest rival is within 1.5km). You MUST provide an aggressive, hyper-local marketing and operational strategy designed to cannibalize their market share and acquire their customers."
    else:
        threat_instruction = f"Competitor Threat Level: {competitor_threat}. Provide standard competitive positioning."

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
```
## 🚀 Step 3: CI/CD Reactivation (The Magic)

Because the repository is already configured with an automated build pipeline connected to Google Cloud, manual deployment commands are unnecessary.

1. **Attach Billing:** Log into the Google Cloud Console and attach an active billing account to the `fleet-ai-project` project.

2. **Push Code:** Commit the changes to `requirements.txt` and `src/ai_analyst.py` and push them to the `main` branch on GitHub.

3. **Monitor the Build:** Navigate to your GitHub repository's **Commits** tab. The queued status indicator (orange dot) next to the commit will automatically begin processing.

4. **Go Live:** Once the build process finishes, the indicator will turn into a green checkmark. Your Docker container will be automatically built and deployed, and the original Cloud Run link will be fully operational again.

*Engineered by Backend and Cloud Architect Irfan Khattak*