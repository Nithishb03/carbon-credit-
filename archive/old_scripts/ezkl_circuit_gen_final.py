import torch
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path

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
    """
    print(f"Loading sample data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    features = ['power_kwh', 'vibration_hz', 'temp_c', 'humidity_pct', 'gps_lat', 'gps_long']
    sample_data = df[features].head(num_samples).values.tolist()
    
    print(f"✓ Prepared {num_samples} sample(s)")
    print(f"  Shape: {len(sample_data)} × {len(features)}")
    
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
    
    print("Generating settings with ezkl.gen_settings()...")
    ezkl.gen_settings(
        model=onnx_path,
        output=settings_path
    )
    
    print(f"✓ Settings generated: {settings_path}")
    return settings_path


# ---------------------------------------------------------
# 3. CALIBRATE SETTINGS
# ---------------------------------------------------------
def calibrate_settings(onnx_path="carbon_validator.onnx",
                       settings_path="settings.json",
                       input_json_path="input.json"):
    """
    Calibrate settings for the model
    """
    print("\n" + "="*60)
    print("STEP 2: Calibrating settings")
    print("="*60)
    
    print("Calibrating settings with ezkl.calibrate_settings()...")
    ezkl.calibrate_settings(
        data=input_json_path,
        model=onnx_path,
        settings=settings_path,
        target="resources"
    )
    
    print(f"✓ Settings calibrated")
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
    
    print("Compiling circuit with ezkl.compile_circuit()...")
    ezkl.compile_circuit(
        model=onnx_path,
        compiled_circuit=compiled_path,
        settings_path=settings_path
    )
    
    print(f"✓ Circuit compiled: {compiled_path}")
    return compiled_path


# ---------------------------------------------------------
# 5. SETUP (GENERATE VK and PK)
# ---------------------------------------------------------
def setup(onnx_path="carbon_validator.onnx",
         settings_path="settings.json",
         input_json_path="input.json"):
    """
    Generate verification key and proving key
    """
    print("\n" + "="*60)
    print("STEP 4: Generating keys (vk and pk)")
    print("="*60)
    
    vk_path = "verification_key.vk"
    pk_path = "proving_key.pk"
    witness_path = "witness.json"
    
    print("Generating witness...")
    ezkl.gen_witness(
        data=input_json_path,
        model=onnx_path,
        output=witness_path
    )
    print(f"✓ Witness generated: {witness_path}")
    
    print("Setting up keys (vk and pk)...")
    ezkl.setup(
        model=onnx_path,
        vk_path=vk_path,
        pk_path=pk_path,
        witness_path=witness_path
    )
    
    print(f"✓ Verification key: {vk_path}")
    print(f"✓ Proving key: {pk_path}")
    
    return vk_path, pk_path, witness_path


# ---------------------------------------------------------
# 6. CREATE PROOF
# ---------------------------------------------------------
def create_proof(onnx_path="carbon_validator.onnx",
                pk_path="proving_key.pk",
                witness_path="witness.json"):
    """
    Create a ZK proof
    """
    print("\n" + "="*60)
    print("STEP 5: Creating ZK proof")
    print("="*60)
    
    proof_path = "proof.json"
    
    print("Generating proof with ezkl.prove()...")
    ezkl.prove(
        witness=witness_path,
        model=onnx_path,
        pk_path=pk_path,
        proof_path=proof_path
    )
    
    print(f"✓ Proof created: {proof_path}")
    return proof_path


# ---------------------------------------------------------
# 7. CREATE EVM VERIFIER
# ---------------------------------------------------------
def create_evm_verifier(vk_path="verification_key.vk",
                       settings_path="settings.json"):
    """
    Create EVM verifier contract
    """
    print("\n" + "="*60)
    print("STEP 6: Creating EVM Verifier Contract")
    print("="*60)
    
    verifier_sol_path = "Verifier.sol"
    verifier_abi_path = "Verifier_ABI.json"
    
    print("Generating EVM verifier with ezkl.create_evm_verifier()...")
    ezkl.create_evm_verifier(
        vk_path=vk_path,
        settings_path=settings_path,
        sol_code_path=verifier_sol_path,
        abi_path=verifier_abi_path,
        reusable=True
    )
    
    print(f"✓ EVM Verifier generated:")
    print(f"  - Solidity Contract: {verifier_sol_path}")
    print(f"  - ABI File: {verifier_abi_path}")
    
    # Display contract preview
    if os.path.exists(verifier_sol_path):
        with open(verifier_sol_path, 'r') as f:
            sol_content = f.read()
        print(f"\n📄 Verifier.sol (first 700 chars):")
        print(sol_content[:700])
        print("...\n")
    
    # Display ABI
    if os.path.exists(verifier_abi_path):
        with open(verifier_abi_path, 'r') as f:
            abi_content = json.load(f)
        print(f"✓ ABI contains {len(abi_content)} items")
    
    return verifier_sol_path, verifier_abi_path


# ---------------------------------------------------------
# MAIN ORCHESTRATION
# ---------------------------------------------------------
def main():
    """
    Complete ZK circuit generation pipeline
    """
    print("\n" + "="*80)
    print(" "*20 + "CARBON VALIDATOR - ZK-SNARK CIRCUIT GENERATION")
    print("="*80)
    
    # Check prerequisites
    if not os.path.exists("carbon_validator.onnx"):
        print("\n❌ ERROR: carbon_validator.onnx not found!")
        print("   Run 'python train.py' first.")
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
        compile_circuit(settings_path=settings_path)
        
        # Step 5: Setup (generate keys)
        print("\n🔑 Step 5/6: Generating verification & proving keys...")
        vk_path, pk_path, witness_path = setup(settings_path=settings_path)
        
        # Step 6a: Create proof
        print("\n✍️ Step 6a/6: Creating ZK proof...")
        proof_path = create_proof(onnx_path="carbon_validator.onnx",
                                 pk_path=pk_path,
                                 witness_path=witness_path)
        
        # Step 6b: Create EVM Verifier
        print("\n🔐 Step 6b/6: Creating EVM Verifier...")
        verifier_sol, verifier_abi = create_evm_verifier(
            vk_path=vk_path,
            settings_path=settings_path
        )
        
        # Summary
        print("\n" + "="*80)
        print(" "*25 + "✅ ZK CIRCUIT GENERATION COMPLETE!")
        print("="*80)
        
        print("\n📦 Generated Files:")
        files = [
            ("input.json", "Sample input data"),
            ("settings.json", "Circuit configuration"),
            ("circuit.json", "Compiled ZK circuit"),
            ("witness.json", "Computation witness"),
            ("verification_key.vk", "Verification key"),
            ("proving_key.pk", "Proving key (keep secret)"),
            ("proof.json", "Example ZK proof"),
            ("Verifier.sol", "Smart contract for verification"),
            ("Verifier_ABI.json", "Contract ABI"),
        ]
        
        for i, (filename, desc) in enumerate(files, 1):
            status = "✓" if os.path.exists(filename) else "✗"
            size = os.path.getsize(filename) if os.path.exists(filename) else 0
            size_str = f"{size/1024:.1f}KB" if size > 0 else ""
            print(f"   {status} {i}. {filename:<25} {desc:<30} {size_str}")
        
        print("\n🚀 DEPLOYMENT GUIDE:")
        print("   1. Copy Verifier.sol to your Ethereum project")
        print("   2. Deploy to network (Ethereum / Polygon / Arbitrum)")
        print("   3. Use proof.json data to call verify() function")
        print("   4. Smart contract confirms computation on-chain")
        
        print("\n💡 KEY INSIGHTS:")
        print("   • Proof size: ~1KB (fixed, not dependent on data)")
        print("   • Verification: ~1M gas on Ethereum")
        print("   • No data disclosure: Only cryptographic proof verified")
        print("   • Model: Neural network with 6 inputs → 1 output (anomaly/normal)")
        
        print("\n⚠️ IMPORTANT NOTES:")
        print("   • Keep proving_key.pk private (needed only for proof generation)")
        print("   • Verification key (vk) is embedded in Verifier.sol")
        print("   • All arithmetic uses fixed-point (deterministic on-chain)")
        print("   • Settings.json must match between proof generation and verification")
        
        print("\n📚 TECHNICAL DETAILS:")
        print("   • ZK System: Halo2")
        print("   • Backend: Ethereum Compatible")
        print("   • Proof Type: Non-interactive ZK-SNARK")
        print("   • Model Type: ONNX Neural Network")
        
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
