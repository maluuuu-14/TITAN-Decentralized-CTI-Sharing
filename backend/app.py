from flask import Flask, jsonify, request, render_template
from web3 import Web3
from flask_cors import CORS
import json
from supabase import create_client, Client

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Supabase Setup ---
SUPABASE_URL = "https://vfdcvciyvcqoqbmqnngm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZmZGN2Y2l5dmNxb3FibXFubmdtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ1MTg0OTQsImV4cCI6MjA5MDA5NDQ5NH0.6qdYijJSPO5D48Nb_wYMWm7YC3d6ABEnRv88Dg4vjhg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Connect to Hardhat node
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
print("Connected to Hardhat:", w3.is_connected())

# Dynamically fetch ALL available public addresses from the Hardhat node
available_accounts = w3.eth.accounts
current_wallet_index = 1
print(f"Dynamically loaded {len(available_accounts)} accounts from Hardhat.")

org_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
cti_address = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"
rep_address = "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0"

# Load ABIs
with open("../artifacts/contracts/OrgRegistry.sol/OrgRegistry.json") as f:
    org_abi = json.load(f)["abi"]
with open("../artifacts/contracts/CTIRegistry.sol/CTIRegistry.json") as f:
    cti_abi = json.load(f)["abi"]
with open("../artifacts/contracts/Reputation.sol/Reputation.json") as f:
    rep_abi = json.load(f)["abi"]

# Create Contract Objects
org_contract = w3.eth.contract(address=org_address, abi=org_abi)
cti_contract = w3.eth.contract(address=cti_address, abi=cti_abi)
rep_contract = w3.eth.contract(address=rep_address, abi=rep_abi)


# ---------------- ROUTES ---------------- #
@app.route("/test")
def test_route():
    return "The backend is working!"
# 1. GET count of CTI records
@app.route("/count", methods=["GET"])
def get_count():
    count = cti_contract.functions.ctiCount().call()
    return jsonify({"cti_count": count})

# 2. POST register organization (THIS WAS MISSING)
@app.route("/orgs", methods=["POST"])
def register_org():
    data = request.get_json()
    org_name = data.get("name")

    if not org_name:
        return jsonify({"error": "Organization name is required"}), 400

    try:
        # --- NEW: Prevent Duplicate Names ---
        count = org_contract.functions.orgCount().call()
        for i in range(1, count + 1):
            existing_org = org_contract.functions.getOrganization(i).call()
            existing_name = existing_org[1]  # The name is usually at index 1 of the returned data
            
            # We use .lower() so people can't register "Tata" and "tata" as different orgs
            if existing_name.lower() == org_name.lower():
                return jsonify({"error": f"Registration Denied: '{existing_name}' is already registered."}), 400
        
        # 1. The Bulletproof Wallet Finder
        new_wallet = None
        
        # Loop through all 20 Hardhat accounts
        for account in w3.eth.accounts:
            # Ask the blockchain: Does this wallet have an ID yet?
            org_id = org_contract.functions.walletToOrgId(account).call()
            
            if org_id == 0:  # 0 means this wallet is completely unregistered!
                new_wallet = account
                break  # Stop looking, we found a fresh one
                
        # 2. Prevent crashing if you actually used all 20
        if not new_wallet:
            return jsonify({"error": "All 20 Hardhat accounts are already registered!"}), 400

        # 3. Send the transaction USING that specific fresh wallet
        # (Remember to match the function name to your Solidity file!)
        tx_hash = org_contract.functions.registerOrganization(org_name).transact({
            "from": new_wallet
        })

        return jsonify({
            "message": f"Successfully registered '{org_name}'!",
            "wallet_assigned": new_wallet
        }), 200

    except Exception as e:
        error_str = str(e)
        print(f"REGISTRATION ERROR: {error_str}")
        
        # Catch name duplicates cleanly
        if "Already registered" in error_str:
            return jsonify({"error": "Registration Failed: That organization name or wallet is already taken."}), 400
            
        return jsonify({"error": error_str}), 400

# 3. POST register CTI 
@app.route("/cti", methods=["POST"])
def register_cti():
    data = request.get_json()
    cti_text = data.get("cti_data")
    org_name_input = data.get("org_name")
    threat_type = data.get("threat_type")

    if not cti_text or not org_name_input:
        return jsonify({"error": "Missing required data"}), 400

    try:
        # 1. Verify Organization exists
        count = org_contract.functions.orgCount().call()
        sender_wallet = None

        for i in range(1, count + 1):
            org = org_contract.functions.getOrganization(i).call()
            if org[1] == org_name_input:
                sender_wallet = org[2]
                break

        if not sender_wallet:
            return jsonify({"error": "Organization not found."}), 404

        # 2. Blockchain Transaction (Store Hash)
        hash_value = w3.keccak(text=cti_text)
        cti_hash_hex = hash_value.hex() # Convert to string for database
        
        tx_hash = cti_contract.functions.registerCTI(hash_value).transact({
            "from": sender_wallet
        })

        # 3. Supabase Transaction (Store Full Payload)
        db_data = {
            "ctiHash": cti_hash_hex,
            "orgName": org_name_input,
            "threatType": threat_type,
            "payload": {"indicators": cti_text} # Stored as JSON
        }
        
        # Insert into Supabase table
        supabase.table("off_chain_storage").insert(db_data).execute()

        return jsonify({
            "message": "CTI secured on Blockchain & Supabase",
            "tx_hash": tx_hash.hex(),
            "cti_hash": cti_hash_hex
        })

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 400
    
# SECURE GET route: Requires verified org name to fetch feed
@app.route("/cti", methods=["GET"])
def get_all_cti():
    org_name_input = request.args.get("org_name")

    if not org_name_input:
        return jsonify({"error": "Organization name required to view feed"}), 400

    try:
        # 1. Verify Organization Access (Authentication)
        count = org_contract.functions.orgCount().call()
        is_registered = False

        for i in range(1, count + 1):
            org = org_contract.functions.getOrganization(i).call()
            if org[1] == org_name_input:
                is_registered = True
                break

        if not is_registered:
            return jsonify({"error": "Access Denied: Unregistered Organization."}), 403

        # 2. Fetch data from Supabase
        response = supabase.table("off_chain_storage").select("*").order("created_at", desc=True).execute()
        cti_records = response.data

        # 3. Integrity Check (The new logic)
        for record in cti_records:
            # Grab the current readable text from the database
            current_data = record["payload"].get("indicators", "")
            stored_hash = record["ctiHash"]

            # Recalculate the Keccak256 hash of the current text
            recalculated_hash = w3.keccak(text=current_data).hex()

            # Compare it! If it matches, the database hasn't been tampered with.
            if recalculated_hash == stored_hash:
                record["integrity_status"] = "Unchanged"
            else:
                record["integrity_status"] = "Changed"
                
            try:
                # Call the getAverageRating function we added to the contract
                cti_id = int(record["cti_id"])
                avg_score = rep_contract.functions.getAverageRating(cti_id).call()
                record["average_rating"] = avg_score
            except Exception as e:
                print(f"Could not fetch rating for ID {record.get('cti_id')}: {e}")
                record["average_rating"] = 0

        return jsonify(cti_records)

    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        return jsonify({"error": str(e)}), 400
    
# POST rate 
@app.route("/rate", methods=["POST"])
def submit_rating():
    data = request.get_json()
    rater_org_name = data.get("rater_org_name")
    cti_id = data.get("cti_id")  
    rating = data.get("rating")

    if not all([rater_org_name, str(cti_id), str(rating)]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # 1. Verify the Rater exists on the blockchain
        count = org_contract.functions.orgCount().call()
        rater_wallet = None

        for i in range(1, count + 1):
            org = org_contract.functions.getOrganization(i).call()
            if org[1] == rater_org_name:
                rater_wallet = org[2]
                break

        if not rater_wallet:
            return jsonify({"error": "Your organization is not registered."}), 404

        # 2. Check Supabase to prevent Self-Rating using the new cti_id
        response = supabase.table("off_chain_storage").select("orgName").eq("cti_id", cti_id).execute()
        
        if not response.data:
            return jsonify({"error": "CTI ID not found."}), 404
            
        original_submitter = response.data[0]["orgName"]

        if original_submitter == rater_org_name:
            return jsonify({"error": "Security Violation: You cannot rate your own intelligence data."}), 403

        # 3. Submit Rating to Blockchain (Reputation Contract)
        # Ensure 'reputation_contract' and 'rateCTI' match your Solidity setup exactly
        tx_hash = rep_contract.functions.submitRating(int(cti_id), int(rating)).transact({
            "from": rater_wallet
        })

        return jsonify({
            "message": f"Successfully rated {rating}/5 by {rater_org_name}",
            "tx_hash": tx_hash.hex()
        }), 200

    except Exception as e:
        error_str = str(e)
        print(f"RAW BLOCKCHAIN ERROR: {error_str}")
        
        # Intercept the specific Solidity 'require' message
        if "Cannot rate yourself" in error_str:
            return jsonify({"error": "Blockchain Security: You cannot rate your own intelligence data."}), 403
            
        # Catch any other raw errors cleanly
        return jsonify({"error": "Transaction failed on the blockchain. Check your inputs."}), 400

# GET reputation score 
@app.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    # 1. Grab the name of the person trying to view the leaderboard
    viewer_org_name = request.args.get("org_name")

    if not viewer_org_name:
        return jsonify({"error": "Organization name is required to view the leaderboard."}), 400

    try:
        count = org_contract.functions.orgCount().call()
        
        # 2. Verify the Viewer is a registered organization
        is_registered = False
        for i in range(1, count + 1):
            org = org_contract.functions.getOrganization(i).call()
            if org[1] == viewer_org_name:
                is_registered = True
                break

        # 3. Block access if they aren't registered
        if not is_registered:
            return jsonify({"error": "Access Denied: Your organization is not registered on the network."}), 403

        # 4. If verified, build the leaderboard
        leaderboard = []
        for i in range(1, count + 1):
            org = org_contract.functions.getOrganization(i).call()
            org_name = org[1]
            score = rep_contract.functions.getReputation(i).call()
            
            leaderboard.append({
                "id": i,
                "name": org_name,
                "score": score
            })

        # Sort the list so the highest score is at the top
        leaderboard = sorted(leaderboard, key=lambda x: x['score'], reverse=True)
        
        return jsonify(leaderboard), 200

    except Exception as e:
        print(f"LEADERBOARD ERROR: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)