from ctgan import CTGAN
import pandas as pd
import numpy as np

def synthesize_100k_ctgan(seed_path="carbon_seed_data.csv", output_path="carbon_100k_ctgan.csv"):
    print(f"Loading seed data from {seed_path}...")
    df_seed = pd.read_csv(seed_path)
    
    # 1. Explicitly tell the GAN which columns are strict categories/binary
    # This stops the GAN from treating labels like floating-point decimals
    discrete_columns = ['label', 'Status Note']

    # 2. Initialize the Conditional Tabular GAN
    # 300 epochs is standard to prevent mode collapse without overfitting
    print("Training Conditional Tabular GAN (CTGAN)... This may take 5-10 minutes.")
    ctgan = CTGAN(epochs=300, verbose=True)
    ctgan.fit(df_seed, discrete_columns)

    # 3. Generating Data (Oversampling to guarantee the exact 85/15 split)
    print("\nModel trained! Synthesizing raw data...")
    # We generate 200k rows to ensure we have enough anomalies to pick from
    raw_synthetic_data = ctgan.sample(200000)

    # 4. Slicing the exact target quantities
    print("Filtering and slicing exact 85/15 targets...")
    
    # Grab all generated anomalies
    anomalies = raw_synthetic_data[raw_synthetic_data['label'] == 1]
    # Grab all generated normal rows
    normals = raw_synthetic_data[raw_synthetic_data['label'] == 0]
    
    print(f"Generated {len(anomalies)} total anomalies in the raw batch.")
    
    if len(anomalies) < 15000:
        print("Warning: GAN didn't generate enough anomalies. Generating more...")
        extra_data = ctgan.sample(100000)
        anomalies = pd.concat([anomalies, extra_data[extra_data['label'] == 1]])
        normals = pd.concat([normals, extra_data[extra_data['label'] == 0]])

    # Take exactly 15,000 anomalies and 85,000 normal rows
    final_anomalies = anomalies.sample(n=15000, random_state=42)
    final_normals = normals.sample(n=85000, random_state=42)

    # 5. Merge, Shuffle, and Clean
    print("Merging and finalizing dataset...")
    df_final = pd.concat([final_normals, final_anomalies])
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    # Clean up formatting to match real sensors
    df_final['power_kwh'] = df_final['power_kwh'].clip(lower=0).round(1)
    df_final['vibration_hz'] = df_final['vibration_hz'].clip(lower=0).round(1)
    df_final['temp_c'] = df_final['temp_c'].round(1)
    df_final['humidity_pct'] = df_final['humidity_pct'].clip(lower=0, upper=100).round(1)
    df_final['reported_co2_ppm'] = df_final['reported_co2_ppm'].clip(lower=400).round(0)
    df_final['gps_lat'] = df_final['gps_lat'].round(4)
    df_final['gps_long'] = df_final['gps_long'].round(4)

    # Save to CSV
    df_final.to_csv(output_path, index=False)
    
    print(f"\n--- SYNTHESIS COMPLETE ---")
    print(f"Total Rows: {len(df_final)}")
    print(f"Normal Rows (Label 0): {len(df_final[df_final['label'] == 0])}")
    print(f"Anomaly Rows (Label 1): {len(df_final[df_final['label'] == 1])}")
    print(f"File saved as: {output_path}")

if __name__ == "__main__":
    synthesize_100k_ctgan()