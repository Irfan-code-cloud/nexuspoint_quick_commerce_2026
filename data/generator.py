import pandas as pd
import numpy as np
import random
import os
from datetime import datetime, timedelta  # <-- ADDED for time generation

def generate_orders():
    # 1. Configuration
    zones = [
        {"name": "Clifton", "lat": 24.8220, "lon": 67.0320},
        {"name": "Gulshan-e-Iqbal", "lat": 24.9180, "lon": 67.0971},
        {"name": "North Nazimabad", "lat": 24.9372, "lon": 67.0425}
    ]
    
    std_dev = 0.015
    orders_per_zone = 15000
    categories = ['Grocery', 'Pharmacy', 'Snacks', 'Personal Care']
    
    data = []
    order_counter = 1

    # 2. Generate Spatial Data
    for zone in zones:
        # Generate random latitudes and longitudes around the center
        lats = np.random.normal(loc=zone["lat"], scale=std_dev, size=orders_per_zone)
        lons = np.random.normal(loc=zone["lon"], scale=std_dev, size=orders_per_zone)
        
        for i in range(orders_per_zone):
            order_id = f"ORD-{order_counter:04d}"
            order_value = random.randint(500, 6500)
            category = random.choice(categories)
            
            data.append({
                "Order_ID": order_id,
                "Latitude": lats[i],
                "Longitude": lons[i],
                "Order_Value_PKR": order_value,
                "Category": category
            })
            order_counter += 1

    # 3. Create Base DataFrame
    df = pd.DataFrame(data)

    # 4. --- NEW: Generate Historical Timestamps for Prophet ---
    num_orders = len(df)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90) # 90 days of history

    # Generate random days
    random_days = np.random.randint(0, 90, size=num_orders)

    # Generate realistic hours weighted towards Lunch (13:00) and Dinner (20:00)
    hours = np.arange(24)
    probabilities = [0.01, 0.01, 0.01, 0.00, 0.00, 0.00, 0.01, 0.02, 0.04, 0.05, 
                     0.06, 0.08, 0.12, 0.15, 0.08, 0.05, 0.04, 0.05, 0.08, 0.15, 
                     0.18, 0.10, 0.05, 0.02]
    probabilities = np.array(probabilities) / sum(probabilities) # Normalize
    
    random_hours = np.random.choice(hours, size=num_orders, p=probabilities)
    random_minutes = np.random.randint(0, 60, size=num_orders)

    # Combine into final timestamps
    timestamps = []
    for day, hour, minute in zip(random_days, random_hours, random_minutes):
        order_time = start_date + timedelta(days=int(day))
        order_time = order_time.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        timestamps.append(order_time)

    # Attach the new time column to the dataframe
    df['Order_Timestamp'] = timestamps

    # 5. Export to CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "orders.csv")
    
    df.to_csv(output_path, index=False)

    # 6. Success Message
    print(f"Success! Generated {len(df)} orders with 90-day historical timestamps and saved to {output_path}")

if __name__ == "__main__":
    generate_orders()