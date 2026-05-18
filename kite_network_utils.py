#!/usr/bin/env python3
"""
Utility script to fetch test USDC faucet links and check balances on the KITE AI Testnet
"""

import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("RPC_URL", "https://rpc-testnet.gokite.ai/")
USDC_ADDRESS = os.getenv("USDC_ADDRESS", "0x833589fCD6eDb6e08f4c7C32D4f71b54bdA02913")

# USDC ERC20 ABI (minimal, just balance)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
]

def check_balances(address):
    """Check KITE and USDC balances for an address"""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        print("❌ Failed to connect to KITE AI Testnet RPC")
        return
    
    address = Web3.to_checksum_address(address)
    
    # Check KITE balance
    kite_balance = w3.eth.get_balance(address)
    kite_display = w3.from_wei(kite_balance, 'ether')
    
    # Check USDC balance
    contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=ERC20_ABI)
    try:
        usdc_balance = contract.functions.balanceOf(address).call()
        decimals = contract.functions.decimals().call()
        usdc_display = usdc_balance / (10 ** decimals)
        
        print(f"✅ Connected to KITE AI Testnet")
        print(f"\n📊 Balances for {address}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"KITE:  {kite_display:.4f} KITE")
        print(f"USDC:  {usdc_display:.2f} USDC")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    except Exception as e:
        print(f"⚠️  Could not fetch USDC balance: {e}")
        print(f"KITE Balance: {kite_display:.4f} KITE")

def print_faucet_links():
    """Print helpful faucet links for testnet"""
    print("\n🚰 KITE AI Testnet Faucets")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("1. KITE Faucet (for gas):")
    print("   https://faucet.gokite.ai/")
    print("\n2. KITE Faucet (for USDC):")
    print("   https://faucet.gokite.ai/")
    print("   - Use the KITE testnet option and request USDC")
    print("\n3. Block Explorer:")
    print("   https://testnet.kitescan.ai/")
    print("\n4. Documentation:")
    print("   https://docs.gokite.ai/")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def main():
    import sys
    
    print("🔗 KITE AI Testnet Utility")
    print("═══════════════════════════════════════════")
    
    if len(sys.argv) > 1:
        address = sys.argv[1]
        check_balances(address)
    else:
        print("\n⚠️  No address provided")
        print("Usage: python kite_network_utils.py <wallet_address>")
        print("\nExample:")
        print("  python kite_network_utils.py 0x1234567890123456789012345678901234567890")
    
    print_faucet_links()

if __name__ == "__main__":
    main()
