import onnxruntime as ort
import numpy as np
import pandas as pd
import requests
import random
import time
import math
import os
import tempfile
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
#  PASTE YOUR EXACT CURRENT CONTRACT ADDRESS HERE:
STAKING_CONTRACT_ADDRESS = w3.to_checksum_address("0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512")

# Add this right below STAKING_CONTRACT_ADDRESS = ...
if w3.eth.get_code(STAKING_CONTRACT_ADDRESS) == b'':
    print(f" FATAL ERROR: No contract exists at {STAKING_CONTRACT_ADDRESS}!")
    print("You must run 'python deploy_contracts.py' to deploy it to your running node.")
    exit()

MINIMAL_ABI = [
    {"inputs":[],"name":"getValidatorPool","outputs":[{"internalType":"address[]","name":"","type":"address[]"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"validators","outputs":[{"internalType":"uint256","name":"nodeReputation","type":"uint256"},{"internalType":"bool","name":"isRegistered","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"_reportHash","type":"bytes32"},{"internalType":"bool","name":"_isValid","type":"bool"},{"internalType":"uint256","name":"_co2Calculated","type":"uint256"}],"name":"settleEscrow","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

staking_contract = w3.eth.contract(address=STAKING_CONTRACT_ADDRESS, abi=MINIMAL_ABI)
HUMAN_APPROVAL_REQUIRED = False

print("  Loading shared P2P ONNX Machine Learning model into host memory...")
scaler_mean = np.load("scaler_mean.npy")
scaler_scale = np.load("scaler_scale.npy")
ort_session = ort.InferenceSession("carbon_validator.onnx")
input_name = ort_session.get_inputs()[0].name

def calculate_carbon_credits(csv_path, existing_wallet_credits, emission_factor=0.82):
    df = pd.read_csv(csv_path)
    df = df.dropna()

    total_power_kwh = df['power_kwh'].sum()
    present_emission_kg = total_power_kwh * emission_factor
    allowed_emission_kg = existing_wallet_credits * 1000
    emission_reduced_kg = allowed_emission_kg - present_emission_kg

    if emission_reduced_kg < 0:
        emission_reduced_kg = 0

    new_credits = emission_reduced_kg / 1000

    updated_wallet_credits = existing_wallet_credits + new_credits

    return {
        "Total Power (kWh)": float(round(total_power_kwh, 2)),
        "Allowed Emission (kg CO2)": float(round(allowed_emission_kg, 2)),
        "Present Emission (kg CO2)": float(round(present_emission_kg, 2)),
        "Emission Reduced (kg CO2)": float(round(emission_reduced_kg, 2)),
        "New Credits Earned": float(round(new_credits, 4)),
        "Base Carbon Credit": float(round(existing_wallet_credits, 4)),
        "Updated Wallet Credits": float(round(updated_wallet_credits, 4))
    }

def resolve_csv_path_for_audit(data_item, report_hash):
    """Returns a CSV path for the audit, using stored upload paths or materialized records."""
    for key in ("csv_path", "file_path", "local_path", "downloaded_csv_path"):
        csv_path = data_item.get(key)
        if csv_path and os.path.exists(csv_path):
            return csv_path

    records = data_item.get("records", [])
    temp_dir = os.path.join(tempfile.gettempdir(), "carbon_validator_audits")
    os.makedirs(temp_dir, exist_ok=True)
    csv_path = os.path.join(temp_dir, f"{report_hash}.csv")
    pd.DataFrame(records).to_csv(csv_path, index=False)
    return csv_path

def print_carbon_credit_audit_report(results):
    print("\n========== CARBON CREDIT AUDIT REPORT ==========\n")

    label_width = max(len(key) for key in results.keys())
    value_width = max(len(str(value)) for value in results.values())
    border = "+" + "-" * (label_width + 2) + "+" + "-" * (value_width + 2) + "+"

    print(border)
    print(f"| {'Metric'.ljust(label_width)} | {'Value'.ljust(value_width)} |")
    print(border)

    for key, value in results.items():
        print(f"| {key.ljust(label_width)} | {str(value).ljust(value_width)} |")

    print(border)

    green_bold = "\033[1;32m"
    reset = "\033[0m"
    print(
        f"\n{green_bold}>>> NEW CREDITS EARNED: "
        f"{results['New Credits Earned']} <<<"
        f"{reset}\n"
    )
    print("================================================\n")

def publish_carbon_credit_audit(report_hash, results):
    payload = {
        "status": "approved",
        "report_hash": report_hash,
        "results": results,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        requests.post("http://127.0.0.1:5000/audit/latest", json=payload, timeout=3)
        print(" Audit report published to frontend dashboard.")
    except Exception as exc:
        print(f"Could not publish audit report to frontend dashboard: {exc}")

def clear_carbon_credit_audit(report_hash):
    payload = {
        "status": "rejected",
        "report_hash": report_hash,
        "results": None,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        requests.post("http://127.0.0.1:5000/audit/latest", json=payload, timeout=3)
        print("Fraudulent report detected. Frontend audit dashboard cleared.")
    except Exception as exc:
        print(f"Could not clear frontend audit dashboard: {exc}")

def wait_for_operator(message):
    if HUMAN_APPROVAL_REQUIRED:
        input(message)

def run_local_model_inference(records):
    """Executes normalization transforms and scores payloads locally with Batch Consensus"""
    fraud_count = 0
    total_co2 = 0
    total_rows = len(records)
    
    print(f"\n INITIATING ML DIAGNOSTICS ON {total_rows} ROWS OF TARGET DATA...")
    for idx, row in enumerate(records):
        
        power = float(row.get('power_kwh', 0))
        vib = float(row.get('vibration_hz', 0))
        temp = float(row.get('temp_c', 0))
        hum = float(row.get('humidity_pct', 0))
        lat = float(row.get('gps_lat', 0))
        lon = float(row.get('gps_long', 0))
        
        features = np.array([[power, vib, temp, hum, lat, lon]])
        
        scaled = ((features - scaler_mean) / scaler_scale).astype(np.float32)
        outputs = ort_session.run(None, {input_name: scaled})
        logit = float(np.squeeze(outputs[0]))
        
        probability = 1 / (1 + math.exp(-max(min(logit, 10), -10)))
        
        # Only print rows that are suspiciously high to keep the terminal clean
        if probability >= 0.5:
            print(f"   [Row {idx}]  High Anomaly Probability: {probability*100:.2f}%")
            fraud_count += 1
        else:
            total_co2 += 500
    
    # Calculate the overall fraud percentage of the batch
    fraud_percentage = (fraud_count / total_rows) * 100
    
    print(f"\n BATCH ANALYSIS COMPLETE:")
    print(f"   Total Rows Processed: {total_rows}")
    print(f"   Anomalies Detected: {fraud_count} ({fraud_percentage:.2f}% of batch)")
    
    # SYSTEM RULE: If more than 20% of the data is fraudulent, slash the enterprise.
    # Otherwise, it's statistical noise, accept it as Legitimate.
    is_valid = fraud_percentage <= 20.0
            
    return is_valid, total_co2

if __name__ == "__main__":
    print("\n Institutional P2P Validator Console Connected.")
    print(" Polling global network pool for unvalidated compliance events...\n")
    
    while True:
        try:
            pool = requests.get("http://127.0.0.1:5000/pool/pending").json()
            if pool:
                for report_hash, data_item in list(pool.items()):
                    print("="*70)
                    print(f" ALERT: Unvalidated File Detected in Network Mempool!")
                    print(f" Cryptographic Hash: 0x{report_hash}")
                    print(f" Storage CID: {data_item['storage_uri']}")
                    print("="*70)
                    
                    # 1. Validator Election
                    pool_nodes = staking_contract.functions.getValidatorPool().call()
                    weights = [staking_contract.functions.validators(n).call()[0] for n in pool_nodes]
                    elected_node = random.choices(pool_nodes, weights=weights, k=1)[0]
                    
                    print(f"  RPoS Election Completed. Elected Evaluation Signer: {elected_node}")
                    if HUMAN_APPROVAL_REQUIRED:
                        print("\n PAUSED: Waiting for human authorization to begin ML scan.")
                    wait_for_operator(f" Press [ENTER] to execute AI Verification on local node...")
                    
                    # 2. ML Verification (This proves the script reads the file)
                    is_valid, final_co2 = run_local_model_inference(data_item["records"])
                    
                    print(f"\n DIAGNOSTICS COMPLETE.")
                    print(f"    Verdict: {'LEGITIMATE (Mint Credits)' if is_valid else 'FRAUDULENT (Execute Slashing)'}")
                    print(f"    Calculated Carbon Offset: {final_co2} tCO2")

                    if is_valid:
                        audit_csv_path = resolve_csv_path_for_audit(data_item, report_hash)
                        carbon_credit_results = calculate_carbon_credits(
                            csv_path=audit_csv_path,
                            existing_wallet_credits=50
                        )
                        print_carbon_credit_audit_report(carbon_credit_results)
                        publish_carbon_credit_audit(report_hash, carbon_credit_results)
                    else:
                        clear_carbon_credit_audit(report_hash)
                    
                    wait_for_operator("\n Press [ENTER] to sign the verdict and commit settlement to the Ledger...")
                    
                    # 3. Escrow Settlement
                    contract_safe_hash = "0x" + report_hash
                    tx_hash = staking_contract.functions.settleEscrow(
                        w3.to_bytes(hexstr=contract_safe_hash), is_valid, final_co2
                    ).transact({'from': w3.eth.accounts[0]})
                    w3.eth.wait_for_transaction_receipt(tx_hash)
                    
                    print(f" Escrow Settle Transaction Confirmed! Tx Hash: {tx_hash.hex()}")
                    
                    # 4. Clear Mempool
                    requests.post(f"http://127.0.0.1:5000/pool/remove/{report_hash}")
                    print(" Local mempool cleared. Returning to network scan loop...\n")
                    break
            time.sleep(3)
        except Exception as e:
            print(f" Network exception: {e}. Retrying in 5s...")
            time.sleep(5)
