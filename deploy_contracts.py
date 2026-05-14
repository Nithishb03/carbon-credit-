import json
import os
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

if not w3.is_connected():
    raise Exception(" Could not connect to Hardhat node. Ensure 'npx hardhat node' is running.")

print(" Connected to Hardhat network. Commencing infrastructure deployment...")

admin_account = w3.eth.accounts[0]
VERIFIER_PATH = 'carbon-blockchain/artifacts/contracts/Verifier.sol/Verifier.json'
STAKING_PATH = 'carbon-blockchain/artifacts/contracts/CarbonStaking.sol/CarbonStaking.json'

# Deploy Verifier
with open(VERIFIER_PATH, 'r') as f:
    verifier_json = json.load(f)
VerifierContract = w3.eth.contract(abi=verifier_json['abi'], bytecode=verifier_json['bytecode'])
tx_hash_v = VerifierContract.constructor().transact({'from': admin_account})
receipt_v = w3.eth.wait_for_transaction_receipt(tx_hash_v)
print(f" Verifier deployed at: {receipt_v.contractAddress}")

# Deploy CarbonStaking
with open(STAKING_PATH, 'r') as f:
    staking_json = json.load(f)
StakingContract = w3.eth.contract(abi=staking_json['abi'], bytecode=staking_json['bytecode'])
tx_hash_s = StakingContract.constructor().transact({'from': admin_account})
receipt_s = w3.eth.wait_for_transaction_receipt(tx_hash_s)
print(f" CarbonStaking deployed at: {receipt_s.contractAddress}")

# Seed P2P Network Validator Nodes immediately inside deployment step
print("\n Registering designated P2P Validator Nodes to Escrow Registry...")
staking_instance = w3.eth.contract(address=receipt_s.contractAddress, abi=staking_json['abi'])

for idx, node in enumerate([w3.eth.accounts[2], w3.eth.accounts[3], w3.eth.accounts[4]], start=1):
    tx = staking_instance.functions.registerValidatorNode(node).transact({'from': admin_account})
    w3.eth.wait_for_transaction_receipt(tx)
    print(f"  └─ Validator Node #{idx} Authorized: {node}")

print("\n Network setup complete.")
print(f" COPY THIS ADDRESS INTO YOUR oracle_api.py: {receipt_s.contractAddress}\n")