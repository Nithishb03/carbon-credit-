import ezkl
import json
import asyncio
import os
import inspect
import pandas as pd
import numpy as np

# --- THE SMART WRAPPER ---
# Automatically handles both sync and async EZKL functions based on your installed version
async def safe_ezkl(func, *args, **kwargs):
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result

async def generate_zk_pipeline():
    # --- File Paths ---
    model_path = "carbon_validator.ezkl.onnx"
    compiled_circuit_path = "circuit.json"
    settings_path = "settings.json"
    data_path = "input.json"
    srs_path = "kzg.srs"
    vk_path = "vk.key"
    pk_path = "pk.key"
    witness_path = "witness.json"
    sol_code_path = "Verifier.sol"
    abi_path = "Verifier.abi"

    print("\n============================================================")
    print("CARBON VALIDATOR: MASTER ZK-SNARK PIPELINE")
    print("============================================================")

    # 1. Create Sample Input Data
    if not os.path.exists(data_path):
        print("\n[1/8] 📊 Preparing input data from CSV...")
        df = pd.read_csv("carbon_100k_ctgan.csv")
        sample = df[['power_kwh', 'vibration_hz', 'temp_c', 'humidity_pct', 'gps_lat', 'gps_long']].iloc[0].values
        
        mean = np.load("scaler_mean.npy")
        scale = np.load("scaler_scale.npy")
        sample_scaled = (sample - mean) / scale
        
        input_data = {"input_data": [sample_scaled.tolist()]}
        with open(data_path, "w") as f:
            json.dump(input_data, f)

    # 2. Generate Settings
    print("\n[2/8] ⚙️ Generating settings.json...")
    await safe_ezkl(ezkl.gen_settings, model_path, settings_path)

    # 3. Calibrate Settings
    print("\n[3/8] 📐 Calibrating settings (Target: resources)...")
    await safe_ezkl(ezkl.calibrate_settings, data_path, model_path, settings_path, "resources")

    # 4. Get SRS
    print("\n[4/8] 🔑 Verifying/Downloading SRS (kzg.srs)...")
    await safe_ezkl(ezkl.get_srs, srs_path=srs_path, settings_path=settings_path)

    # 5. Compile Circuit
    print("\n[5/8] 🔧 Compiling Circuit...")
    await safe_ezkl(
        ezkl.compile_circuit,
        model=model_path,
        compiled_circuit=compiled_circuit_path,
        settings_path=settings_path
    )

# 6. Generate Witness
    print("\n[6/8] 👁️ Generating Witness...")
    await safe_ezkl(
        ezkl.gen_witness,
        data_path,              # The input.json
        compiled_circuit_path,  # The circuit.json
        witness_path            # The output witness.json
    )

# 7. Setup (Keys Generation)
    print("\n[7/8] 🔐 Running Setup (Generating VK & PK)...")
    setup_success = False

    # We MUST catch BaseException because Rust PyO3 panics do not inherit from standard Python Exception
    
    # Strategy A: Compiled Circuit
    try:
        print("  -> Strategy A: Compiled Circuit...")
        await safe_ezkl(ezkl.setup, compiled_circuit_path, vk_path, pk_path, srs_path=srs_path)
        setup_success = True
    except BaseException as e:
        print(f"     [Failed Strategy A: {type(e).__name__}]")

    # Strategy B: ONNX Model
    if not setup_success:
        try:
            print("  -> Strategy B: ONNX Model...")
            await safe_ezkl(ezkl.setup, model_path, vk_path, pk_path, srs_path=srs_path)
            setup_success = True
        except BaseException as e:
            print(f"     [Failed Strategy B: {type(e).__name__}]")

    # Strategy C: Strict Positional
    if not setup_success:
        try:
            print("  -> Strategy C: Strict Positional...")
            await safe_ezkl(ezkl.setup, compiled_circuit_path, vk_path, pk_path, srs_path)
            setup_success = True
        except BaseException as e:
            print(f"     [Failed Strategy C: {type(e).__name__}]")

    # Strategy D: Include Settings Path (For specific mid-release versions)
    if not setup_success:
        try:
            print("  -> Strategy D: With Settings Path...")
            await safe_ezkl(ezkl.setup, compiled_circuit_path, vk_path, pk_path, srs_path=srs_path, settings_path=settings_path)
            setup_success = True
        except BaseException as e:
            print(f"     [Failed Strategy D: {type(e).__name__}]")

    if not setup_success:
        print(f"\n[!] ALL SETUP STRATEGIES FAILED.")
        print("CRITICAL: The EZKL engine cannot find a required file. Please ensure 'circuit.json' and 'kzg.srs' are in the root folder.")
        return
        
    print("  ✅ Setup Successful!")

if __name__ == "__main__":
    # Temporarily suppress the deprecation warnings for clean logs
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(generate_zk_pipeline())