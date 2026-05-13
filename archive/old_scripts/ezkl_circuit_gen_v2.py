import torch
import pandas as pd
import numpy as np
import json
import os
import subprocess
from pathlib import Path

# Try to import ezkl - if it fails, provide helpful error
try:
    import ezkl
except ImportError:
    print("ERROR: ezkl not installed. Run: pip install ezkl")
    exit(1)

# ---------------------------------------------------------
# 1. PREPARE INPUT DATA FROM CSV
# ---------------------------------------------------------
def prepare_input_data(csv_path="carbon_100k_ctgan.csv", num_samples=1):
    """
    Load a small sample from the CSV and prepare as input.json for ezkl
    
    Note: EZKL expects input in specific format with proper scaling
    """
    print(f"Loading sample data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Select features in the same order as training
    features = ['power_kwh', 'vibration_hz', 'temp_c', 'humidity_pct', 'gps_lat', 'gps_long']
    
    # Take first N samples
    sample_data = df[features].head(num_samples).values.tolist()
    
    print(f"✓ Prepared {num_samples} sample(s) for input")
    print(f"  Shape: {len(sample_data)} rows × {len(features)} features")
    
    # Save as input.json
    with open("input.json", "w") as f:
        json.dump(sample_data, f)
    
    print("✓ Saved input.json")
    return sample_data


# ---------------------------------------------------------
# 2. GENERATE SETTINGS
# ---------------------------------------------------------
def generate_settings(onnx_path="carbon_validator.onnx"):
    """
    Generate settings.json for the ezkl circuit
    """
    print("\n" + "="*60)
    print("STEP 1: Generating settings.json")
    print("="*60)
    
    settings_path = "settings.json"
    
    # Use ezkl CLI to generate settings
    print("Generating settings with ezkl...")
    
    cmd = [
        "ezkl", "gen-settings",
        "-M", onnx_path,
        "-O", settings_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✓ Settings generated: {settings_path}")
        if result.stdout:
            print(f"  Output: {result.stdout[:200]}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Warning: {e.stderr}")
        # Continue anyway - settings might still exist
    
    return settings_path


# ---------------------------------------------------------
# 3. CALIBRATE SETTINGS
# ---------------------------------------------------------
def calibrate_settings(onnx_path="carbon_validator.onnx", 
                       settings_path="settings.json",
                       input_json_path="input.json"):
    """
    Calibrate settings for optimal performance
    """
    print("\n" + "="*60)
    print("STEP 2: Calibrating settings")
    print("="*60)
    
    print("Calibrating settings with ezkl...")
    
    cmd = [
        "ezkl", "calibrate-settings",
        "-M", onnx_path,
        "-D", input_json_path,
        "--settings-path", settings_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✓ Settings calibrated")
        if result.stdout:
            print(f"  Output: {result.stdout[:200]}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Warning: {e.stderr}")
    
    return settings_path


# ---------------------------------------------------------
# 4. COMPILE CIRCUIT
# ---------------------------------------------------------
def compile_circuit(onnx_path="carbon_validator.onnx",
                    settings_path="settings.json"):
    """
    Compile the circuit
    """
    print("\n" + "="*60)
    print("STEP 3: Compiling circuit")
    print("="*60)
    
    compiled_path = "circuit.json"
    
    print("Compiling circuit with ezkl...")
    
    cmd = [
        "ezkl", "compile-circuit",
        "-M", onnx_path,
        "-O", compiled_path,
        "--settings-path", settings_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✓ Circuit compiled: {compiled_path}")
        if result.stdout:
            print(f"  Output: {result.stdout[:200]}")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e.stderr}")
        raise
    
    return compiled_path


# ---------------------------------------------------------
# 5. GENERATE PROVING KEY
# ---------------------------------------------------------
def generate_proving_key(compiled_path="circuit.json",
                        settings_path="settings.json"):
    """
    Generate proving key
    """
    print("\n" + "="*60)
    print("STEP 4: Generating proving key")
    print("="*60)
    
    pk_path = "proving_key.key"
    
    print("Generating proving key with ezkl...")
    
    cmd = [
        "ezkl", "gen-pk",
        "--compiled-circuit", compiled_path,
        "-O", pk_path,
        "--settings-path", settings_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        print(f"✓ Proving key generated: {pk_path}")
        if result.stdout:
            print(f"  Output: {result.stdout[:200]}")
    except subprocess.TimeoutExpired:
        print("⚠️ Key generation timed out (taking longer than expected)")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e.stderr}")
        raise
    
    return pk_path


# ---------------------------------------------------------
# 6. CREATE PROOF
# ---------------------------------------------------------
def create_proof(compiled_path="circuit.json",
                settings_path="settings.json",
                pk_path="proving_key.key",
                input_json_path="input.json"):
    """
    Create a ZK proof
    """
    print("\n" + "="*60)
    print("STEP 5: Creating ZK proof")
    print("="*60)
    
    proof_path = "proof.json"
    
    print("Generating proof with ezkl...")
    
    cmd = [
        "ezkl", "prove",
        "-D", input_json_path,
        "--compiled-circuit", compiled_path,
        "-O", proof_path,
        "--pk-path", pk_path,
        "--settings-path", settings_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
        print(f"✓ Proof created: {proof_path}")
        if result.stdout:
            print(f"  Output: {result.stdout[:200]}")
    except subprocess.TimeoutExpired:
        print("⚠️ Proof generation timed out")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e.stderr}")
        raise
    
    return proof_path


# ---------------------------------------------------------
# 7. CREATE EVM VERIFIER
# ---------------------------------------------------------
def create_evm_verifier(compiled_path="circuit.json",
                       settings_path="settings.json"):
    """
    Create EVM verifier contract (Verifier.sol) and its ABI
    """
    print("\n" + "="*60)
    print("STEP 6: Creating EVM Verifier Contract")
    print("="*60)
    
    verifier_sol_path = "Verifier.sol"
    verifier_abi_path = "Verifier_ABI.json"
    
    print("Generating EVM verifier with ezkl...")
    
    cmd = [
        "ezkl", "create-evm-verifier",
        "--compiled-circuit", compiled_path,
        "--settings-path", settings_path,
        "-O", verifier_sol_path,
        "--abi-path", verifier_abi_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✓ EVM Verifier generated:")
        print(f"  - Solidity Contract: {verifier_sol_path}")
        print(f"  - ABI File: {verifier_abi_path}")
        
        # Display contract preview
        if os.path.exists(verifier_sol_path):
            with open(verifier_sol_path, 'r') as f:
                sol_content = f.read()
            print(f"\n📄 Verifier.sol Preview (first 600 chars):")
            print(sol_content[:600])
            print("...\n")
        
        # Display ABI preview
        if os.path.exists(verifier_abi_path):
            with open(verifier_abi_path, 'r') as f:
                abi_content = json.load(f)
            print(f"✓ ABI contains {len(abi_content)} items")
            print(f"ABI Preview (first item):")
            print(json.dumps(abi_content[0], indent=2))
        
        if result.stdout:
            print(f"\n  Output: {result.stdout[:200]}")
            
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e.stderr}")
        raise
    
    return verifier_sol_path, verifier_abi_path


# ---------------------------------------------------------
# MAIN ORCHESTRATION
# ---------------------------------------------------------
def main():
    """
    Main function to orchestrate the entire ZK circuit generation pipeline
    
    IMPORTANT: Fixed-Point Arithmetic
    EZKL uses fixed-point arithmetic for ZK proofs. The input scale
    in settings.json must align with your neural network's expected
    input range to ensure deterministic proofs on-chain.
    """
    print("\n" + "="*80)
    print(" "*20 + "CARBON VALIDATOR - ZK-SNARK CIRCUIT GENERATION")
    print("="*80)
    
    # Check if ONNX model exists
    if not os.path.exists("carbon_validator.onnx"):
        print("\n❌ ERROR: carbon_validator.onnx not found!")
        print("   Run 'python train.py' first to generate the ONNX model.")
        return False
    
    try:
        # Step 1: Prepare input data
        print("\n📊 Step 1/6: Preparing input data...")
        prepare_input_data(num_samples=1)
        
        # Step 2: Generate settings
        print("\n⚙️ Step 2/6: Generating settings...")
        settings_path = generate_settings()
        
        # Step 3: Calibrate settings
        print("\n📐 Step 3/6: Calibrating settings...")
        calibrate_settings(settings_path=settings_path)
        
        # Step 4: Compile circuit
        print("\n🔧 Step 4/6: Compiling circuit...")
        compiled_path = compile_circuit(settings_path=settings_path)
        
        # Step 5: Generate proving key
        print("\n🔑 Step 5/6: Generating proving key...")
        pk_path = generate_proving_key(compiled_path=compiled_path, settings_path=settings_path)
        
        # Step 6: Create proof
        print("\n✍️ Step 6a/6: Creating ZK proof...")
        proof_path = create_proof(compiled_path=compiled_path, 
                                 settings_path=settings_path,
                                 pk_path=pk_path)
        
        # Step 7: Create EVM Verifier
        print("\n🔐 Step 6b/6: Creating EVM Verifier...")
        verifier_sol, verifier_abi = create_evm_verifier(
            compiled_path=compiled_path,
            settings_path=settings_path
        )
        
        # Summary
        print("\n" + "="*80)
        print(" "*25 + "✅ ZK-SNARK CIRCUIT GENERATION COMPLETE!")
        print("="*80)
        
        print("\n📦 Generated Files:")
        files = [
            ("input.json", "Sample input data (1 row × 6 features)"),
            ("settings.json", "Circuit settings with fixed-point precision"),
            ("circuit.json", "Compiled ZK circuit"),
            ("proving_key.key", "Key for generating proofs"),
            ("proof.json", "Example zero-knowledge proof"),
            ("Verifier.sol", "Smart contract for on-chain verification"),
            ("Verifier_ABI.json", "Contract ABI for blockchain integration"),
        ]
        
        for i, (filename, desc) in enumerate(files, 1):
            status = "✓" if os.path.exists(filename) else "✗"
            print(f"   {status} {i}. {filename:<20} - {desc}")
        
        print("\n🚀 DEPLOYMENT GUIDE:")
        print("   1. Deploy Verifier.sol to Ethereum / Polygon / Arbitrum")
        print("   2. Call verify(proof) with your proof.json data")
        print("   3. Smart contract confirms computation without revealing inputs")
        
        print("\n⚠️ IMPORTANT NOTES:")
        print("   • Ensure input_scale in settings.json matches your scaler precision")
        print("   • All on-chain verification uses fixed-point arithmetic")
        print("   • Proofs are specific to this circuit configuration")
        print("   • Keep proving_key.key private (not for blockchain)")
        
        print("\n📚 For more info:")
        print("   - EZKL Docs: https://docs.ezkl.ai/")
        print("   - ZK Basics: https://blog.cryptographyengineering.com/")
        
        print("\n" + "="*80 + "\n")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
