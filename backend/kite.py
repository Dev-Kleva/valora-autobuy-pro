from datetime import datetime
from typing import Dict
import os
from dotenv import load_dotenv

backend_dir = os.path.dirname(__file__)
root_env = os.path.join(backend_dir, os.pardir, ".env")
backend_env = os.path.join(backend_dir, ".env")
load_dotenv(root_env)
load_dotenv(backend_env, override=True)

# Kite Mainnet Configuration
KITE_RPC_URL = os.getenv("KITE_RPC_URL", "https://rpc.gokite.ai/")
KITE_CHAIN_ID = os.getenv("KITE_CHAIN_ID", "2366")
KITE_FAUCET = os.getenv("KITE_FAUCET", "")

SETTLEMENT_EVENTS = []


def settle_usdc(tx_hash: str, vendor_address: str, amount: float, metadata: Dict):
    """Simulated Kite AI settlement endpoint.

    Production should call Kite API with credentials and handle final settlement receipt.
    """
    event = {
        "settlement_id": f"kite_{datetime.utcnow().timestamp()}",
        "tx_hash": tx_hash,
        "vendor": vendor_address,
        "amount": amount,
        "metadata": metadata,
        "settled_at": datetime.utcnow().isoformat(),
        "status": "settled"
    }
    SETTLEMENT_EVENTS.append(event)
    return event


def get_settlements():
    return SETTLEMENT_EVENTS
