#!/usr/bin/env python3
"""
Deploy AutoBuy contract on the KITE AI Testnet
"""

import os
from web3 import Web3
from solcx import compile_source
from dotenv import load_dotenv

load_dotenv()

# KITE AI Testnet configuration
RPC_URL = os.getenv("KITE_RPC_URL", "https://rpc-testnet.gokite.ai/")
CHAIN_ID = int(os.getenv("KITE_CHAIN_ID", "2368"))
USDC_ADDRESS = os.getenv("USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

# Read contract source
with open("../contracts/AutoBuy.sol", "r") as f:
    contract_source = f.read()

def deploy_contract():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    assert w3.is_connected(), "Not connected to KITE AI Testnet"

    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise ValueError("PRIVATE_KEY not set in .env")

    account = w3.eth.account.from_key(private_key)

    # Compile contract
    compiled_sol = compile_source(contract_source, solc_version="0.8.0")
    contract_interface = compiled_sol['<stdin>:AutoBuy']

    # Build transaction
    contract = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
    tx = contract.constructor(USDC_ADDRESS).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 2000000,
        "gasPrice": w3.eth.gas_price,
        "chainId": CHAIN_ID
    })

    # Sign and send
    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"Deployment tx hash: {tx_hash.hex()}")

    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Contract deployed at: {receipt.contractAddress}")

    return receipt.contractAddress

if __name__ == "__main__":
    deploy_contract()