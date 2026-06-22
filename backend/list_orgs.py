from web3 import Web3
import json

# Connect to Hardhat
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# Use the EXACT OrgRegistry address from your current deployment
org_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

# Load the ABI so Python knows how to talk to the contract
with open("../artifacts/contracts/OrgRegistry.sol/OrgRegistry.json") as f:
    org_abi = json.load(f)["abi"]

org_contract = w3.eth.contract(address=org_address, abi=org_abi)

def get_all_registered_orgs():
    try:
        # Check if the contract actually exists at that address
        code = w3.eth.get_code(org_address)
        if code == b'\x00' or code == b'':
            print(f"ERROR: No contract found at {org_address}. Did you redeploy?")
            return

        count = org_contract.functions.orgCount().call()
        print(f"\n--- Registered Organizations: {count} ---")
        
        for i in range(1, count + 1):
            # Calling the getOrganization function from OrgRegistry.sol [cite: 20]
            org = org_contract.functions.getOrganization(i).call()
            # org returns: [id, name, wallet] [cite: 14, 15]
            print(f"ID: {org[0]} | Name: {org[1]} | Wallet: {org[2]}")
        
        print("-------------------------------------------\n")
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    get_all_registered_orgs()