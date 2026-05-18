import os
from dotenv import load_dotenv
from web3 import Web3

backend_dir = os.path.dirname(__file__)
root_env = os.path.join(backend_dir, os.pardir, ".env")
backend_env = os.path.join(backend_dir, ".env")
load_dotenv(root_env)
load_dotenv(backend_env, override=True)

RPC_URL = os.getenv("RPC_URL", os.getenv("KITE_RPC_URL", "https://rpc.gokite.ai/"))
STABLECOIN_ADDRESS = Web3.to_checksum_address(
    os.getenv("STABLECOIN_ADDRESS", os.getenv("USDC_ADDRESS", "0x7aB6f3ed87C42eF0aDb67Ed95090f8bF5240149e"))
)

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))


def send_stablecoin(private_key, to, amount):
    account = w3.eth.account.from_key(private_key)
    contract = w3.eth.contract(address=STABLECOIN_ADDRESS, abi=ERC20_ABI)

    tx = contract.functions.transfer(
        Web3.to_checksum_address(to),
        int(amount * 1e6)
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 100000,
        "gasPrice": w3.to_wei("2", "gwei")
    })

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    return tx_hash.hex()
