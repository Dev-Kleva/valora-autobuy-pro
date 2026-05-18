"""
Blockchain Requirements & Wallet Setup Service
Ensures users have KITE AI blockchain configured and all required tokens
"""

import os
from web3 import Web3
from dotenv import load_dotenv

backend_dir = os.path.dirname(__file__)
root_env = os.path.join(backend_dir, os.pardir, ".env")
backend_env = os.path.join(backend_dir, ".env")
load_dotenv(root_env)
load_dotenv(backend_env, override=True)

# KITE AI Mainnet Configuration
KITE_RPC = os.getenv("KITE_RPC_URL", "https://rpc.gokite.ai/")
KITE_CHAIN_ID = 2366
STABLECOIN_ADDRESS = os.getenv(
    "STABLECOIN_ADDRESS",
    os.getenv("USDC_ADDRESS", "0x7aB6f3ed87C42eF0aDb67Ed95090f8bF5240149e")  # USDC.e on KITE AI Mainnet
)
PAYMENT_TOKEN_SYMBOL = os.getenv("STABLECOIN_SYMBOL", "USDC")
MIN_KITE_FOR_GAS = 0.1  # Minimum KITE for gas fees
MIN_STABLECOIN_FOR_PURCHASE = 1.0  # Minimum stablecoin to make a purchase

# Stablecoin ERC20 ABI (compatible with USDC/USDT/PYUSD)
ERC20_ABI = [
    {
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
        "constant": True,
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
        "constant": True,
    },
    {
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transferFrom",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    }
]

# KITE AI Network Configuration for frontend
KITE_NETWORK_CONFIG = {
    "chainId": "0x94e",  # 2366 in hex
    "chainName": "KITE AI Mainnet",
    "nativeCurrency": {
        "name": "KITE",
        "symbol": "KITE",
        "decimals": 18,
    },
    "rpcUrls": [KITE_RPC],
    "blockExplorerUrls": ["https://kitescan.ai/"],
}

# Stablecoin Token Configuration for frontend
STABLECOIN_TOKEN_CONFIG = {
    "address": STABLECOIN_ADDRESS,
    "symbol": PAYMENT_TOKEN_SYMBOL,
    "decimals": 6,
    "image": "https://assets.coingecko.com/coins/images/13196/large/USD_Coin_icon.png",
}


class WalletRequirements:
    """Check and manage wallet requirements for blockchain transactions"""

    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(KITE_RPC))
        self.stablecoin_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(STABLECOIN_ADDRESS),
            abi=ERC20_ABI
        )

    def is_connected(self) -> bool:
        """Check if RPC is connected"""
        try:
            return self.w3.is_connected()
        except Exception as e:
            print(f"❌ RPC Connection Error: {e}")
            return False

    def validate_address(self, address: str) -> bool:
        """Validate Ethereum address format"""
        try:
            return Web3.is_address(address)
        except Exception:
            return False

    def get_kite_balance(self, address: str) -> dict:
        """Get KITE balance (native gas token) for an address"""
        try:
            if not self.validate_address(address):
                return {"error": "Invalid address format", "balance": 0}

            address = Web3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(address)
            balance_kite = self.w3.from_wei(balance_wei, "ether")

            return {
                "balance": float(balance_kite),
                "balance_wei": str(balance_wei),
                "sufficient": float(balance_kite) >= MIN_KITE_FOR_GAS,
                "minimum_required": MIN_KITE_FOR_GAS,
                "needs": max(0, MIN_KITE_FOR_GAS - float(balance_kite)),
            }
        except Exception as e:
            return {"error": str(e), "balance": 0, "sufficient": False}

    def get_stablecoin_balance(self, address: str) -> dict:
        """Get stablecoin balance for an address"""
        try:
            if not self.validate_address(address):
                return {"error": "Invalid address format", "balance": 0}

            address = Web3.to_checksum_address(address)
            balance_raw = self.stablecoin_contract.functions.balanceOf(address).call()
            decimals = self.stablecoin_contract.functions.decimals().call()
            balance_token = balance_raw / (10 ** decimals)

            return {
                "balance": float(balance_token),
                "balance_raw": str(balance_raw),
                "decimals": decimals,
                "sufficient": float(balance_token) >= MIN_STABLECOIN_FOR_PURCHASE,
                "minimum_required": MIN_STABLECOIN_FOR_PURCHASE,
                "needs": max(0, MIN_STABLECOIN_FOR_PURCHASE - float(balance_token)),
            }
        except Exception as e:
            return {"error": str(e), "balance": 0, "sufficient": False}

    def check_wallet_requirements(self, address: str) -> dict:
        """
        Comprehensive wallet requirements check
        Returns status of network, KITE (gas), and stablecoin payment
        """
        kite_balance = self.get_kite_balance(address)
        stablecoin_balance = self.get_stablecoin_balance(address)

        return {
            "address": address,
            "network": {
                "name": "KITE AI Mainnet",
                "chainId": KITE_CHAIN_ID,
                "config": KITE_NETWORK_CONFIG,
            },
            "kite": {
                "balance": kite_balance.get("balance", 0),
                "sufficient": kite_balance.get("sufficient", False),
                "needs": kite_balance.get("needs", 0),
                "minimum": MIN_KITE_FOR_GAS,
            },
            "stablecoin": {
                "balance": stablecoin_balance.get("balance", 0),
                "sufficient": stablecoin_balance.get("sufficient", False),
                "needs": stablecoin_balance.get("needs", 0),
                "minimum": MIN_STABLECOIN_FOR_PURCHASE,
                "config": STABLECOIN_TOKEN_CONFIG,
            },
            "ready_to_purchase": (
                kite_balance.get("sufficient", False) and
                stablecoin_balance.get("sufficient", False)
            ),
            "issues": self._get_issues(kite_balance, stablecoin_balance),
        }

    @staticmethod
    def _get_issues(kite_data: dict, stablecoin_data: dict) -> list:
        """Identify wallet issues"""
        issues = []

        if not kite_data.get("sufficient", False):
            issues.append({
                "type": "insufficient_kite",
                "severity": "critical",
                "message": f"❌ Insufficient KITE for gas fees. You have {kite_data.get('balance', 0):.8f} KITE, need minimum 0.001 KITE",
                "needs": kite_data.get("needs", 0),
                "action": "Fund your wallet on KiteAI Mainnet (exchange, bridge, or transfer)",
            })

        if not stablecoin_data.get("sufficient", False):
            issues.append({
                "type": "insufficient_stablecoin",
                "severity": "critical",
                "message": f"❌ Insufficient {PAYMENT_TOKEN_SYMBOL} for payment. You have {stablecoin_data.get('balance', 0):.6f} {PAYMENT_TOKEN_SYMBOL}, need minimum {MIN_STABLECOIN_FOR_PURCHASE:.2f} {PAYMENT_TOKEN_SYMBOL}",
                "needs": stablecoin_data.get("needs", 0),
                "action": f"Fund your wallet with {PAYMENT_TOKEN_SYMBOL} on KiteAI Mainnet (exchange, bridge, or transfer)",
            })

        return issues

    def estimate_transaction_cost(self) -> dict:
        """Estimate gas costs for a typical stablecoin transfer"""
        try:
            # Estimate gas for stablecoin transfer
            gas_price = self.w3.eth.gas_price
            estimated_gas = 100000  # Standard estimate for stablecoin transfer

            total_wei = gas_price * estimated_gas
            total_kite = self.w3.from_wei(total_wei, "ether")

            return {
                "gas_limit": estimated_gas,
                "gas_price_gwei": self.w3.from_wei(gas_price, "gwei"),
                "estimated_cost_kite": float(total_kite),
                "estimated_cost_usd": float(total_kite) * 0.01,  # Approximate KITE price
            }
        except Exception as e:
            return {"error": str(e)}

    def get_faucet_info(self) -> dict:
        """Mainnet: no public faucet available. Provide funding guidance and explorer."""
        return {
            "kite_faucet": None,
            "stablecoin_faucet": None,
            "funding_guidance": "No public faucet on KiteAI Mainnet. Fund wallets via exchange, bridge, or direct transfer.",
            "block_explorer": {
                "name": "Kitescan",
                "url": "https://kitescan.ai/",
                "description": "View transactions and verify settlements on KiteAI Mainnet",
            },
        }



# Initialize service
wallet_service = WalletRequirements()
