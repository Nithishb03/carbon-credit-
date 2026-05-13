from web3 import Web3
import onnxruntime as ort
import numpy as np
import time

# --- 1. CONFIGURATION & CONNECTION ---
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

if not w3.is_connected():
    raise Exception("❌ Failed to connect to Hardhat node. Is 'npx hardhat node' running?")

print("🟢 Python Oracle Node Booted. Connected to Hardhat.")

# The Checksummed Contract Address
STAKING_CONTRACT_ADDRESS = w3.to_checksum_address("0xe7f1725e7734ce288f8367e1bb143e90bb3f0512")

MINIMAL_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "enterpriseAddr", "type": "address"},
            {"internalType": "bytes", "name": "proof", "type": "bytes"},
            {"internalType": "uint256[]", "name": "pubInputs", "type": "uint256[]"},
            {"internalType": "uint256", "name": "co2Calculated", "type": "uint256"}
        ],
        "name": "submitValidation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "enterprises",
        "outputs": [
            {"internalType": "uint256", "name": "stakedAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "reliabilityScore", "type": "uint256"},
            {"internalType": "uint256", "name": "totalCreditsMinted", "type": "uint256"},
            {"internalType": "bool", "name": "isActive", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

staking_contract = w3.eth.contract(address=STAKING_CONTRACT_ADDRESS, abi=MINIMAL_ABI)
enterprise_address = w3.eth.accounts[1]
validator_address = w3.eth.accounts[2]

# --- 2. LOAD MACHINE LEARNING ARTIFACTS ---
print("⚙️ Loading ML Artifacts (ONNX + Scalers)...")
scaler_mean = np.load("scaler_mean.npy")
scaler_scale = np.load("scaler_scale.npy")
ort_session = ort.InferenceSession("carbon_validator.onnx")
input_name = ort_session.get_inputs()[0].name

# --- 3. THE MACHINE LEARNING BRIDGE ---
def run_ml_inference(payload):
    print(f"\n🧠 ML Ingesting Data: Power={payload['power_kwh']}kWh, Vib={payload['vibration_hz']}Hz")
    
    # 1. Format the 6 features exactly as the model expects
    raw_features = np.array([[
        payload['power_kwh'],
        payload['vibration_hz'],
        payload['temp_c'],
        payload['humidity_pct'],
        payload['gps_lat'],
        payload['gps_long']
    ]])
    
    # 2. Normalize the data using the exact scalers from training
    scaled_features = (raw_features - scaler_mean) / scaler_scale
    scaled_features = scaled_features.astype(np.float32)
    
    # 3. Run ONNX Inference
    outputs = ort_session.run(None, {input_name: scaled_features})
    
    # 4. Interpret the output (Assuming Sigmoid output where >= 0.5 is Fraud)
    # Note: Output shape varies slightly by PyTorch export version. Usually it's outputs[0][0][0] or outputs[0][0]
    probability = float(np.squeeze(outputs[0])) 
    
    if probability >= 0.5:
        print(f"🚨 ML Output: FRAUD DETECTED (Anomaly Confidence: {probability*100:.2f}%)")
        return False, 0
    else:
        print(f"✅ ML Output: NORMAL OPERATION (Anomaly Confidence: {probability*100:.2f}%)")
        return True, 500 # Simulating 500 CO2 for standard emission

# --- 4. THE BLOCKCHAIN EXECUTION ---
def submit_to_blockchain(is_valid, expected_co2):
    proof = b'\x01' if is_valid else b'\x00'
    pub_inputs = [] 
    
    print(f"⛓️  Building Transaction... Proof: {proof.hex()}")
    
    tx = staking_contract.functions.submitValidation(
        enterprise_address,
        proof,
        pub_inputs,
        expected_co2
    ).build_transaction({
        'from': validator_address,
        'nonce': w3.eth.get_transaction_count(validator_address),
        'gas': 500000,
        'gasPrice': w3.eth.gas_price
    })
    
    tx_hash = w3.eth.send_transaction({
        'to': STAKING_CONTRACT_ADDRESS,
        'from': validator_address,
        'data': tx['data'],
        'gas': tx['gas'],
        'gasPrice': tx['gasPrice']
    })
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✅ Transaction Mined in Block {receipt.blockNumber} | Hash: {tx_hash.hex()}")
    
    state = staking_contract.functions.enterprises(enterprise_address).call()
    print(f"📊 Enterprise Updated State -> Stake: {w3.from_wei(state[0], 'ether')} ETH, Score: {state[1]}\n")

# --- 5. EXECUTION LOOP ---
if __name__ == "__main__":
    state = staking_contract.functions.enterprises(enterprise_address).call()
    print(f"\nInitial Enterprise State -> Stake: {w3.from_wei(state[0], 'ether')} ETH, Score: {state[1]}")
    
    # CYCLE 1: Legitimate Data
    print("\n--- CYCLE 1: Processing Legitimate Data ---")
    payload_1 = {
        "power_kwh": 450.5, 
        "vibration_hz": 55.2, 
        "temp_c": 24.5, 
        "humidity_pct": 46.0, 
        "gps_lat": 34.05, 
        "gps_long": -118.24
    }
    is_valid, co2 = run_ml_inference(payload_1)
    submit_to_blockchain(is_valid, co2)
    
    time.sleep(2)
    
    # CYCLE 2: Fraudulent Data (e.g., GPS Spoofing to air-conditioned office)
    print("--- CYCLE 2: Processing Tampered Data ---")
    payload_2 = {
        "power_kwh": 460.0, 
        "vibration_hz": 56.5, 
        "temp_c": 20.0,  # Unnaturally cold for factory
        "humidity_pct": 30.0, # Unnaturally dry
        "gps_lat": 36.16, # GPS moved to Vegas
        "gps_long": -115.13
    }
    is_valid, co2 = run_ml_inference(payload_2)
    submit_to_blockchain(is_valid, co2)