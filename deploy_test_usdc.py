#!/usr/bin/env python3
"""
Deploy a test USDC token on Kite testnet for Valora AutoBuy Agent testing
"""

import os
from web3 import Web3
from web3.middleware import geth_poa_middleware
import json

# Kite testnet configuration
RPC_URL = "https://rpc-testnet.gokite.ai/"
CHAIN_ID = 2368

# Simple ERC-20 contract bytecode and ABI
ERC20_BYTECODE = "608060405234801561001057600080fd5b506040516105b03803806105b0833981810160405281019061003291906100b5565b8160016000336101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055508060028190555080600360006101000a81548160ff02191690831515021790555080600460006101000a81548160ff0219169083151502179055505050506101c5565b6000815190506100af81610100565b92915050565b6000602082840312156100c757600080fd5b60006100d5848285016100a0565b91505092915050565b6104c0806101166000396000f3fe608060405234801561001057600080fd5b50600436106100cf5760003560e01c8063313ce5671161008c57806370a082311161006657806370a082311461019557806395d89b41146101c5578063a9059cbb146101e5578063dd62ed3e14610215576100cf565b8063313ce5671461012d578063395093511461014b57806370a0823114610177576100cf565b806306fdde03146100d4578063095ea7b3146100f257806318160ddd14610122575b600080fd5b6100dc610245565b60408051918252519081900360200190f35b61011e6004803603604081101561010857600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff021916602001909291908035906020019092919050505061024b565b005b6100dc6102b5565b6101356102bb565b6040805160ff9092168252519081900360200190f35b6101576004803603604081101561014157600080fd5b81019080803590602001909291905050506102c0565b005b6101816004803603602081101561016d57600080fd5b81019080803590602001909291905050506102f0565b005b61019f600480360360208110156101ab57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff0219166020019092919050505050610305565b005b6101cf610322565b60408051918252519081900360200190f35b6101ef610328565b60408051918252519081900360200190f35b61021f6004803603604081101561020b57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff0219166020019092919080359060200190929190505050610335565b005b6102476004803603604081101561023d57600080fd5b81019080803590602001909291905050506103a5565b005b6100dc6103c2565b60008054905090565b600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1681565b600260009054906101000a900460ff1681565b600360009054906101000a900460ff1681565b60003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205482111561033d57600080fd5b61034e826103c2565b610359826103c2565b600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254039250508190555081600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055505050565b60008082116103b357600080fd5b8181036000819055505050565b6000602082019050919050565b600081600080828060200190518101906103e0919061041c565b919050565b600073ffffffffffffffffffffffffffffffffffffffff168273ffffffffffffffffffffffffffffffffffffffff160361044857600080fd5b6000826000819055505050565b6000819050919050565b61041a816103f5565b82525050565b60006020828403121561043257600080fd5b60006104408482850161040b565b9150509291505056fe"

ERC20_ABI = [
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address"
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "spender",
                "type": "address"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256"
            }
        ],
        "name": "Approval",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "from",
                "type": "address"
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256"
            }
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "owner",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "spender",
                "type": "address"
            }
        ],
        "name": "allowance",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "spender",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "approve",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "account",
                "type": "address"
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [
            {
                "internalType": "uint8",
                "name": "",
                "type": "uint8"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "spender",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "subtractedValue",
                "type": "uint256"
            }
        ],
        "name": "decreaseAllowance",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "spender",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "addedValue",
                "type": "uint256"
            }
        ],
        "name": "increaseAllowance",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "type"
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "recipient",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "transfer",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "sender",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "recipient",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "transferFrom",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def deploy_test_usdc():
    """Deploy a test USDC token on Kite testnet"""

    # Connect to Kite testnet
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    if not w3.is_connected():
        print("❌ Cannot connect to Kite testnet")
        return None

    print(f"✅ Connected to Kite testnet (Chain ID: {w3.eth.chain_id})")

    # You'll need to set your private key
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        print("❌ Set PRIVATE_KEY environment variable with your wallet private key")
        print("Example: export PRIVATE_KEY=0x...")
        return None

    # Create account from private key
    account = w3.eth.account.from_key(private_key)
    print(f"📝 Deploying from address: {account.address}")

    # Check balance
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"💰 Account balance: {balance_eth} KITE")

    if balance < w3.to_wei(0.01, 'ether'):
        print("❌ Insufficient balance for deployment (need at least 0.01 KITE)")
        print("Get test KITE from: https://faucet.gokite.ai")
        return None

    # Deploy contract
    TestUSDC = w3.eth.contract(abi=ERC20_ABI, bytecode=ERC20_BYTECODE)

    # Build transaction
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    # Estimate gas
    try:
        gas_estimate = TestUSDC.constructor().estimate_gas({'from': account.address})
        print(f"⛽ Estimated gas: {gas_estimate}")
    except Exception as e:
        print(f"⚠️  Gas estimation failed: {e}")
        gas_estimate = 2000000  # Fallback

    transaction = TestUSDC.constructor().build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': gas_estimate,
        'gasPrice': gas_price,
        'chainId': CHAIN_ID
    })

    # Sign and send transaction
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

    print(f"🚀 Deployment transaction sent: {tx_hash.hex()}")

    # Wait for receipt
    print("⏳ Waiting for confirmation...")
    try:
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        contract_address = tx_receipt.contractAddress

        print(f"✅ Test USDC deployed at: {contract_address}")
        print(f"🔗 View on explorer: https://testnet.kitescan.ai/address/{contract_address}")

        # Update the backend config
        print("\n📝 Update your backend/kite_settlement.py with:")
        print(f"USDC_ADDRESS = '{contract_address}'")

        return contract_address

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Deploying Test USDC on Kite Testnet")
    print("=" * 50)

    contract_address = deploy_test_usdc()

    if contract_address:
        print("\n🎉 Success! You can now import this token in MetaMask:")
        print(f"Address: {contract_address}")
        print("Symbol: USDC")
        print("Decimals: 6")
    else:
        print("\n❌ Deployment failed. Check the errors above.")