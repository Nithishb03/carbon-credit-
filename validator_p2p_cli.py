import onnxruntime as ort
import numpy as np
import requests
import random
import time
import math
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
# 🚨 PASTE YOUR EXACT CURRENT CONTRACT ADDRESS HERE:
STAKING_CONTRACT_ADDRESS = w3.to_checksum_address("0xa513E6E4b8f2a923D98304ec87F64353C4D5C853")

# Add this right below STAKING_CONTRACT_ADDRESS = ...
if w3.eth.get_code(STAKING_CONTRACT_ADDRESS) == b'':
    print(f"❌ FATAL ERROR: No contract exists at {STAKING_CONTRACT_ADDRESS}!")
    print("You must run 'python deploy_contracts.py' to deploy it to your running node.")
    exit()

MINIMAL_ABI = [
    {"inputs":[],"name":"getValidatorPool","outputs":[{"internalType":"address[]","name":"","type":"address[]"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"validators","outputs":[{"internalType":"uint256","name":"nodeReputation","type":"uint256"},{"internalType":"bool","name":"isRegistered","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"_reportHash","type":"bytes32"},{"internalType":"bool","name":"_isValid","type":"bool"},{"internalType":"uint256","name":"_co2Calculated","type":"uint256"}],"name":"settleEscrow","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

staking_contract = w3.eth.contract(address=STAKING_CONTRACT_ADDRESS, abi=MINIMAL_ABI)

print("⚙️  Loading shared P2P ONNX Machine Learning model into host memory...")
scaler_mean = np.load("scaler_mean.npy")
scaler_scale = np.load("scaler_scale.npy")
ort_session = ort.InferenceSession("carbon_validator.onnx")
input_name = ort_session.get_inputs()[0].name

def run_local_model_inference(records):
    """Executes normalization transforms and scores payloads locally"""
    fraud_detected = False
    total_co2 = 0
    
    print(f"\n🧠 INITIATING ML DIAGNOSTICS ON {len(records)} ROWS OF TARGET DATA...")
    for idx, row in enumerate(records):
        # 1. Show the user exactly what the script is reading
        print(f"\n   [Row {idx}] Extracting Raw Telemetry: Power={row.get('power_kwh', 0)}kWh, Vib={row.get('vibration_hz', 0)}Hz, Temp={row.get('temp_c', 0)}C")
        
        features = np.array([[
            float(row.get('power_kwh', 0)), float(row.get('vibration_hz', 0)), 
            float(row.get('temp_c', 0)), float(row.get('humidity_pct', 0)), 
            float(row.get('gps_lat', 0)), float(row.get('gps_long', 0))
        ]])
        
        # 2. Normalize and run ONNX inference
        scaled = ((features - scaler_mean) / scaler_scale).astype(np.float32)
        outputs = ort_session.run(None, {input_name: scaled})
        logit = float(np.squeeze(outputs[0]))
        
        # 3. Sigmoid probability transform
        probability = 1 / (1 + math.exp(-max(min(logit, 10), -10)))
        print(f"   [Row {idx}] AI Inference Complete -> Anomaly Probability: {probability*100:.2f}%")
        
        if probability >= 0.5:
            fraud_detected = True
        else:
            total_co2 += 500
            
    return not fraud_detected, total_co2

if __name__ == "__main__":
    print("\n🟢 Institutional P2P Validator Console Connected.")
    print("📡 Polling global network pool for unvalidated compliance events...\n")
    
    while True:
        try:
            pool = requests.get("http://127.0.0.1:5000/pool/pending").json()
            if pool:
                for report_hash, data_item in list(pool.items()):
                    print("="*70)
                    print(f"🚨 ALERT: Unvalidated File Detected in Network Mempool!")
                    print(f"📦 Cryptographic Hash: 0x{report_hash}")
                    print(f"📍 Storage CID: {data_item['storage_uri']}")
                    print("="*70)
                    
                    # 1. Validator Election
                    pool_nodes = staking_contract.functions.getValidatorPool().call()
                    weights = [staking_contract.functions.validators(n).call()[0] for n in pool_nodes]
                    elected_node = random.choices(pool_nodes, weights=weights, k=1)[0]
                    
                    print(f"🗳️  RPoS Election Completed. Elected Evaluation Signer: {elected_node}")
                    print("\n🛑 PAUSED: Waiting for human authorization to begin ML scan.")
                    input(f"👉 Press [ENTER] to execute AI Verification on local node...")
                    
                    # 2. ML Verification (This proves the script reads the file)
                    is_valid, final_co2 = run_local_model_inference(data_item["records"])
                    
                    print(f"\n📊 DIAGNOSTICS COMPLETE.")
                    print(f"    Verdict: {'LEGITIMATE (Mint Credits)' if is_valid else 'FRAUDULENT (Execute Slashing)'}")
                    print(f"    Calculated Carbon Offset: {final_co2} tCO2")
                    
                    input("\n👉 Press [ENTER] to sign the verdict and commit settlement to the Ledger...")
                    
                    # 3. Escrow Settlement
                    contract_safe_hash = "0x" + report_hash
                    tx_hash = staking_contract.functions.settleEscrow(
                        w3.to_bytes(hexstr=contract_safe_hash), is_valid, final_co2
                    ).transact({'from': w3.eth.accounts[0]})
                    w3.eth.wait_for_transaction_receipt(tx_hash)
                    
                    print(f"✅ Escrow Settle Transaction Confirmed! Tx Hash: {tx_hash.hex()}")
                    
                    # 4. Clear Mempool
                    requests.post(f"http://127.0.0.1:5000/pool/remove/{report_hash}")
                    print("🧹 Local mempool cleared. Returning to network scan loop...\n")
                    break
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ Network exception: {e}. Retrying in 5s...")
            time.sleep(5)