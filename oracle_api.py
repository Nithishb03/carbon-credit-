from flask import Flask, request, jsonify
from flask_cors import CORS
from web3 import Web3
import traceback
import hashlib
import json
import csv
import io

app = Flask(__name__)
CORS(app)

w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
# MAKE SURE THIS MATCHES YOUR CURRENT DEPLOYMENT:
STAKING_CONTRACT_ADDRESS = w3.to_checksum_address("0xa513E6E4b8f2a923D98304ec87F64353C4D5C853")

MINIMAL_ABI = [
    {"inputs":[],"name":"registerEnterprise","outputs":[],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"address","name":"_node","type":"address"}],"name":"registerValidatorNode","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"_reportHash","type":"bytes32"},{"internalType":"string","name":"_storageURI","type":"string"}],"name":"commitReport","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"bytes32","name":"_reportHash","type":"bytes32"},{"internalType":"bool","name":"_isValid","type":"bool"},{"internalType":"uint256","name":"_co2Calculated","type":"uint256"}],"name":"settleEscrow","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"enterprises","outputs":[{"internalType":"uint256","name":"stakedAmount","type":"uint256"},{"internalType":"uint256","name":"reputationScore","type":"uint256"},{"internalType":"uint256","name":"totalCreditsMinted","type":"uint256"},{"internalType":"bool","name":"isActive","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getValidatorPool","outputs":[{"internalType":"address[]","name":"","type":"address[]"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"validators","outputs":[{"internalType":"uint256","name":"nodeReputation","type":"uint256"},{"internalType":"bool","name":"isRegistered","type":"bool"}],"stateMutability":"view","type":"function"}
]

staking_contract = w3.eth.contract(address=STAKING_CONTRACT_ADDRESS, abi=MINIMAL_ABI)
pending_network_pool = {}

@app.route('/identity/generate', methods=['GET'])
def generate_identity():
    account = w3.eth.account.create()
    return jsonify({"address": account.address, "private_key": account.key.hex()}), 200

@app.route('/identity/onboard', methods=['POST'])
def onboard_identity():
    try:
        user_address = w3.to_checksum_address(request.json.get("address"))
        user_pk = request.json.get("private_key")

        funding_tx = w3.eth.send_transaction({
            'from': w3.eth.accounts[0], 'to': user_address, 'value': w3.to_wei(1.5, 'ether')
        })
        w3.eth.wait_for_transaction_receipt(funding_tx)

        nonce = w3.eth.get_transaction_count(user_address)
        tx = staking_contract.functions.registerEnterprise().build_transaction({
            'from': user_address, 'nonce': nonce, 'value': w3.to_wei(1, 'ether'),
            'gas': 400000, 'gasPrice': w3.eth.gas_price
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=user_pk)
        tx_sent = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_sent)

        return jsonify({"message": "Node onboarding tx complete.", "tx_hash": tx_sent.hex()}), 200
    except Exception as e:
        print(f"❌ ERROR IN /IDENTITY/ONBOARD: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/state/<address>', methods=['GET'])
def get_enterprise_state(address):
    try:
        chk_addr = w3.to_checksum_address(address)
        data = staking_contract.functions.enterprises(chk_addr).call()
        return jsonify({
            "stake": str(w3.from_wei(data[0], 'ether')),
            "reputation": int(data[1]),
            "credits": int(data[2]),
            "isActive": bool(data[3])
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/report/upload', methods=['POST'])
def handle_report_upload():
    try:
        user_address = w3.to_checksum_address(request.form.get("address"))
        user_pk = request.form.get("private_key")
        file_obj = request.files.get("file")

        if not file_obj:
            return jsonify({"error": "No file stream payload parsed."}), 400

        filename = file_obj.filename.lower()
        file_content_bytes = file_obj.read()
        
        # utf-8-sig automatically destroys hidden Windows BOM characters (\ufeff)
        file_content_str = file_content_bytes.decode("utf-8-sig") 

        # Generate hash and format as strict 0x Hex String for Web3 bytes32
        raw_hash = hashlib.sha256(file_content_bytes).hexdigest()
        contract_safe_hash = "0x" + raw_hash 

        parsed_records = []
        if filename.endswith('.csv'):
            reader = csv.DictReader(io.StringIO(file_content_str))
            for row in reader:
                if not any(row.values()): continue # Skip empty trailing newlines
                clean_row = {}
                for k, v in row.items():
                    if k and v:
                        try:
                            clean_row[k.strip()] = float(str(v).strip())
                        except ValueError:
                            clean_row[k.strip()] = 0.0 # Safe fallback instead of crashing
                if clean_row:
                    parsed_records.append(clean_row)
        elif filename.endswith('.json'):
            parsed_records = json.loads(file_content_str)
            if isinstance(parsed_records, dict):
                parsed_records = [parsed_records]
        else:
            return jsonify({"error": "Unsupported compliance file extension."}), 400

        pending_network_pool[raw_hash] = {
            "owner": user_address,
            "records": parsed_records,
            "storage_uri": f"ipfs://{raw_hash[:32]}"
        }

        # Broadcast strict hex hash to the smart contract
        nonce = w3.eth.get_transaction_count(user_address)
        tx = staking_contract.functions.commitReport(
            contract_safe_hash,
            pending_network_pool[raw_hash]["storage_uri"]
        ).build_transaction({
            'from': user_address, 'nonce': nonce, 'gas': 500000, 'gasPrice': w3.eth.gas_price
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=user_pk)
        tx_sent = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_sent)

        return jsonify({"message": "File hash written to ledger.", "hash": raw_hash, "tx_hash": tx_sent.hex()}), 200
    except Exception as e:
        print(f"❌ ERROR IN /REPORT/UPLOAD: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/pool/pending', methods=['GET'])
def get_pending_pool():
    return jsonify(pending_network_pool), 200

@app.route('/pool/remove/<report_hash>', methods=['POST'])
def remove_from_pool(report_hash):
    if report_hash in pending_network_pool:
        del pending_network_pool[report_hash]
    return jsonify({"status": "cleared"}), 200

@app.route('/network/blocks', methods=['GET'])
def get_blocks_explorer():
    try:
        blocks = []
        latest_block_num = w3.eth.block_number
        start = max(0, latest_block_num - 7)
        for idx in range(latest_block_num, start - 1, -1):
            blk = w3.eth.get_block(idx, full_transactions=False)
            blocks.append({
                "number": int(blk.number),
                "hash": str(blk.hash.hex()),
                "parentHash": str(blk.parentHash.hex()),
                "timestamp": int(blk.timestamp),
                "tx_count": len(blk.transactions)
            })
        return jsonify(blocks), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)