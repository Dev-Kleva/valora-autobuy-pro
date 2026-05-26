from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import json
import time
import hashlib
from dotenv import load_dotenv

# Load environment variables from root .env and backend/.env
backend_dir = os.path.dirname(__file__)
root_env = os.path.join(backend_dir, os.pardir, ".env")
backend_env = os.path.join(backend_dir, ".env")
load_dotenv(root_env)
load_dotenv(backend_env, override=True)

# ===================== KITE PASSPORT CONFIG =====================
KITE_PASSPORT_BASE_URL = os.getenv("KITE_PASSPORT_BASE_URL")

# ✅ FIX: inject Railway env JSON into real config file BEFORE Passport init
kite_passport_config_json = os.getenv("KITE_PASSPORT_CONFIG_JSON")

if kite_passport_config_json:
    try:
        config = json.loads(kite_passport_config_json)

        os.makedirs(os.path.expanduser("~/.kite-passport"), exist_ok=True)
        config_path = os.path.expanduser("~/.kite-passport/config.json")

        with open(config_path, "w") as f:
            json.dump(config, f)

        # critical for KitePassport loader
        os.environ["KITE_PASSPORT_CONFIG_PATH"] = config_path

        print(f"✅ Kite Passport config written to {config_path}")

    except Exception as e:
        raise RuntimeError(f"Failed to parse KITE_PASSPORT_CONFIG_JSON: {e}")
else:
    print("⚠️ KITE_PASSPORT_CONFIG_JSON not set, using local config fallback")


# ===================== VALORA CONFIG =====================
VALORA_TREASURY_ADDRESS = os.getenv("VALORA_TREASURY_ADDRESS")

pending_links_file = os.path.join(backend_dir, "pending_purchase_links.json")


def load_pending_purchase_links():
    if os.path.exists(pending_links_file):
        try:
            with open(pending_links_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"WARNING: Failed to load pending purchase links: {e}")
            return {}
    return {}


def save_pending_purchase_links():
    try:
        with open(pending_links_file, "w", encoding="utf-8") as f:
            json.dump(pending_purchase_links, f)
    except Exception as e:
        print(f"WARNING: Failed to save pending purchase links: {e}")


pending_purchase_links = load_pending_purchase_links()

# ===================== IMPORTS =====================
from .agent import decide_purchase
from .constraints import validate
from .subscriptions import (
    create_subscription, get_subscription, cancel_subscription,
    pause_subscription, resume_subscription, get_due_subscriptions,
    update_subscription_charge
)
from .kite_passport import get_passport
from .users import register_user, authenticate_user, get_user_by_token

from .kite_settlement import (
    record_attestation_on_kite, settle_payment_on_kite,
    verify_kite_attestation, get_user_attestations, kite_health_check
)
from .blockchain_payment import (
    payment_processor, MIN_STABLECOIN_CHARGE,
    STABLECOIN_ADDRESS, PAYMENT_TOKEN_SYMBOL, KITE_CHAIN_ID, KITE_RPC
)
from .kite import get_settlements
from web3 import Web3

# ===================== SAFETY CHECKS =====================
if not VALORA_TREASURY_ADDRESS:
    raise RuntimeError("VALORA_TREASURY_ADDRESS is required")

if not Web3.is_address(VALORA_TREASURY_ADDRESS):
    raise RuntimeError(f"Invalid VALORA_TREASURY_ADDRESS: {VALORA_TREASURY_ADDRESS}")


# ===================== APP =====================
app = FastAPI(title="AutoBuy Agent")


@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    if request.scope["path"].startswith("/api/"):
        request.scope["path"] = request.scope["path"][4:]
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== AUTH =====================
def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = authorization.replace("Bearer ", "")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@app.post("/register")
async def register(request: dict):
    username = request.get("username")
    password = request.get("password")

    user = register_user(username, password)
    if not user:
        raise HTTPException(status_code=409, detail="user exists")

    token = authenticate_user(username, password)
    return {"token": token}


@app.post("/login")
async def login(request: dict):
    token = authenticate_user(request.get("username"), request.get("password"))
    if not token:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"token": token}


@app.get("/me")
async def me(user=Depends(get_current_user)):
    return user


# ===================== PASSPORT =====================
@app.get("/passport/health")
async def passport_health(user=Depends(get_current_user)):
    passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
    return {
        "ready": True,
        "version": passport.get_version()
    }


@app.post("/passport/agent/register")
async def passport_register_agent(request: dict, user=Depends(get_current_user)):
    passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
    return passport.register_agent(
        request.get("name", "AutoBuy Agent"),
        request.get("description", "")
    )


@app.get("/passport/services")
async def passport_services(user=Depends(get_current_user), query: Optional[str] = None):
    passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
    return passport.discover_services(query=query)


@app.post("/passport/execute")
async def passport_execute(request: dict, user=Depends(get_current_user)):
    passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)

    return passport.execute_agent_request(
        service_query=request["service_id"],
        payment_amount=str(request["amount"]),
        payment_asset=PAYMENT_TOKEN_SYMBOL,
        recipient_address=VALORA_TREASURY_ADDRESS
    )


# ===================== BUY FLOW =====================
@app.post("/buy")
async def buy(request: dict, user=Depends(get_current_user)):
    decision = decide_purchase(request)

    if decision["status"] != "approved":
        return decision

    product = decision["product"]

    if product["price"] > request["budget"]:
        return {"status": "rejected", "reason": "over_budget"}

    return {
        "status": "payment_required",
        "product": product,
        "amount": product["price"]
    }


# ===================== CONFIRM PAYMENT =====================
@app.post("/confirm-payment")
async def confirm_payment(request: dict, user=Depends(get_current_user)):
    product = request["product"]
    wallet_address = request["wallet_address"]

    passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)

    result = passport.execute_agent_request(
        service_query=f"Buy {product['name']}",
        payment_amount=MIN_STABLECOIN_CHARGE,
        payment_asset=PAYMENT_TOKEN_SYMBOL,
        recipient_address=VALORA_TREASURY_ADDRESS,
        user_address=wallet_address
    )

    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail="Payment failed")

    settle_payment_on_kite(
        task_id=result.get("tx_hash", "unknown"),
        user_address=wallet_address,
        payment_amount_usdc=MIN_STABLECOIN_CHARGE,
        vendor_address=VALORA_TREASURY_ADDRESS
    )

    return {
        "status": "payment_completed",
        "tx": result,
        "product": product
    }


# ===================== HEALTH =====================
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "kite": kite_health_check()
    }