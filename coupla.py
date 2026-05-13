import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_5k_seed_dataset(output_file="carbon_seed_data.csv"):
    print("Initializing Vectorized Gaussian Copula Generator for 5K Seed...")
    
    n_total = 5000
    n_normal = int(n_total * 0.85)  # 4,250 rows (85%)
    n_anomaly = int(n_total * 0.15) # 750 rows (15%)
    
    start_time = datetime(2023, 1, 1)
    
    # ---------------------------------------------------------
    # 1. GENERATE NORMAL DATA (4,250 Rows)
    # ---------------------------------------------------------
    # Means: [Power(kWh), Vibration(Hz), Temp(C), Humidity(%), CO2(ppm)]
    means_normal = [450.0, 55.0, 24.0, 45.0, 1250.0]
    
    # Covariance Matrix: Binds Power, Vibration, and CO2 together mathematically
    cov_normal = [
        [400.0,  50.0,   2.0,  -5.0,  550.0],  # Power
        [ 50.0,  10.0,   0.5,  -1.0,   80.0],  # Vibration
        [  2.0,   0.5,   5.0, -10.0,    5.0],  # Temp
        [ -5.0,  -1.0, -10.0,  20.0,   -2.0],  # Humidity
        [550.0,  80.0,   5.0,  -2.0,  900.0]   # CO2
    ]
    
    normal_data = np.random.multivariate_normal(means_normal, cov_normal, n_normal)
    df_normal = pd.DataFrame(normal_data, columns=['power_kwh', 'vibration_hz', 'temp_c', 'humidity_pct', 'reported_co2_ppm'])
    
    # Set Baseline GPS and Label for Normal Data
    df_normal['label'] = 0
    df_normal['Status Note'] = "Normal - Physics Aligned"
    df_normal['gps_lat'] = 34.0522
    df_normal['gps_long'] = -118.2437

    # ---------------------------------------------------------
    # 2. GENERATE ANOMALY DATA (750 Rows)
    # ---------------------------------------------------------
    # Keep Power and Vibration high (Factory is active)
    means_anomaly_mech = [450.0, 55.0]
    cov_anomaly_mech = [[400.0, 50.0], [50.0, 10.0]]
    anomaly_mech = np.random.multivariate_normal(means_anomaly_mech, cov_anomaly_mech, n_anomaly)
    
    df_anomaly = pd.DataFrame(anomaly_mech, columns=['power_kwh', 'vibration_hz'])
    
    # Split anomalies: 60% Bagged Sensor, 40% Moved Sensor (Location Spoofing)
    anomaly_types = np.random.choice(['bagged', 'moved'], size=n_anomaly, p=[0.6, 0.4])
    
    # Inject Environmental & GPS context based on anomaly type
    df_anomaly['temp_c'] = np.where(anomaly_types == 'moved', np.random.normal(21, 0.5, n_anomaly), np.random.normal(25, 2, n_anomaly))
    df_anomaly['humidity_pct'] = np.where(anomaly_types == 'moved', np.random.normal(30, 2, n_anomaly), np.random.normal(46, 3, n_anomaly))
    
    # INJECT GPS ANOMALIES (This is crucial for the GAN)
    df_anomaly['gps_lat'] = np.where(anomaly_types == 'moved', 36.1627, 34.0522)
    df_anomaly['gps_long'] = np.where(anomaly_types == 'moved', -115.1398, -118.2437)
    
    # Choke the CO2 mathematically (The "Analog Hole")
    df_anomaly['reported_co2_ppm'] = np.random.normal(405, 8, n_anomaly) 
    
    df_anomaly['label'] = 1
    df_anomaly['Status Note'] = np.where(anomaly_types == 'moved', "Anomaly - Location Spoof", "Anomaly - Sensor Bagged")

    # ---------------------------------------------------------
    # 3. MERGE & CLEANUP
    # ---------------------------------------------------------
    df_final = pd.concat([df_normal, df_anomaly], ignore_index=True)
    
    # Shuffle
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Add Timestamps
    timestamps = [int((start_time + timedelta(minutes=15 * i)).timestamp()) for i in range(n_total)]
    df_final['timestamp'] = timestamps
    
    # Clean up formatting
    df_final = df_final.round({'power_kwh': 1, 'vibration_hz': 1, 'temp_c': 1, 'humidity_pct': 1, 'reported_co2_ppm': 0})
    
    # Enforce correct Schema Order
    cols = ['timestamp', 'gps_lat', 'gps_long', 'power_kwh', 'vibration_hz', 'temp_c', 'humidity_pct', 'reported_co2_ppm', 'label', 'Status Note']
    df_final = df_final[cols]
    
    df_final.to_csv(output_file, index=False)
    
    print(f"\n--- 5K SEED GENERATION COMPLETE ---")
    print(f"Total Rows: {len(df_final)}")
    print(f"Normal Rows (Label 0): {len(df_final[df_final['label'] == 0])} (85%)")
    print(f"Anomaly Rows (Label 1): {len(df_final[df_final['label'] == 1])} (15%)")
    print(f"File saved as: {output_file}")
    
    return df_final

if __name__ == "__main__":
    generate_5k_seed_dataset()