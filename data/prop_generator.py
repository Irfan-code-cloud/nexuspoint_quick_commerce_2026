import pandas as pd
import numpy as np
import random
import os

def generate_properties():
    # 1. Configuration
    center_lat = 24.86
    center_lon = 67.05
    spread = 0.20
    num_properties = 300
    
    data = []
    
    # 2. Generate Data
    for i in range(num_properties):
        prop_id = f"PROP-{i+1:03d}"
        lat = center_lat + random.uniform(-spread, spread)
        lon = center_lon + random.uniform(-spread, spread)
        rent = random.randint(50000, 150000)
        sq_ft = random.randint(500, 5000)
        max_orders = sq_ft // 2
        
        data.append({
            "Property_ID": prop_id,
            "Latitude": lat,
            "Longitude": lon,
            "Rent_PKR": rent,
            "Square_Footage": sq_ft,
            "Max_Daily_Orders": max_orders
        })
        
    # 3. Create DataFrame
    df = pd.DataFrame(data)

    # 4. Export to CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "properties.csv")
    df.to_csv(output_path, index=False)

    print(f"Success! Generated {len(df)} properties and saved them to {output_path}")

if __name__ == "__main__":
    generate_properties()
