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

# Valora treasury recipient for service charge payments
VALORA_TREASURY_ADDRESS = os.getenv("VALORA_TREASURY_ADDRESS")

# Kite Passport base URL for API calls
KITE_PASSPORT_BASE_URL = os.getenv("KITE_PASSPORT_BASE_URL")

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

# Existing imports
from .agent import decide_purchase
from .constraints import validate
from .subscriptions import (
    create_subscription, get_subscription, cancel_subscription,
    pause_subscription, resume_subscription, get_due_subscriptions,
    update_subscription_charge
)
from .kite_passport import get_passport
from .users import register_user, authenticate_user, get_user_by_token

# New imports
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

if not VALORA_TREASURY_ADDRESS:
    raise RuntimeError(
        "VALORA_TREASURY_ADDRESS is required. Set it in root .env or the environment before starting the backend."
    )

if not Web3.is_address(VALORA_TREASURY_ADDRESS):
    raise RuntimeError(
        f"VALORA_TREASURY_ADDRESS is invalid: {VALORA_TREASURY_ADDRESS}. "
        "Use a full checksum KITE wallet address like 0xDd1B81c0e23afb7a0307F5c03ad4b6a0b40787f1."
    )

app = FastAPI(title="AutoBuy Agent")

@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    if request.scope["path"].startswith("/api/"):
        request.scope["path"] = request.scope["path"][4:]
        raw_path = request.scope.get("raw_path")
        if raw_path is not None:
            request.scope["raw_path"] = raw_path[4:]
    return await call_next(request)

# Store pending product URLs until payment completes
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8001")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents


def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = authorization.replace("Bearer ", "")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


# ============ AUTH ENDPOINTS ============

@app.post("/register")
async def register(request: dict):
    username = request.get("username")
    password = request.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    user = register_user(username, password)
    if not user:
        raise HTTPException(status_code=409, detail="user already exists")
    token = authenticate_user(username, password)
    return {"status": "registered", "token": token}


@app.post("/login")
async def login(request: dict):
    username = request.get("username")
    password = request.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    token = authenticate_user(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"status": "authenticated", "token": token}


@app.get("/me")
async def me(user=Depends(get_current_user)):
    return {"username": user["username"], "id": user["id"]}


# ============ KITE CHAIN ENDPOINTS ============

@app.get("/kite/health")
async def kite_health():
    """Check Kite chain connectivity"""
    return kite_health_check()


@app.get("/passport/health")
async def passport_health(user=Depends(get_current_user)):
    """Check Kite Passport CLI availability and status."""
    try:
        passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
        version = passport.get_version()
        return {"ready": True, "version": version}
    except Exception as e:
        return {"ready": False, "error": str(e)}


@app.post("/passport/agent/register")
async def passport_register_agent(request: dict, user=Depends(get_current_user)):
    name = request.get("name", "Valora AutoBuy Agent")
    description = request.get("description", "AI agent for automated product purchases")
    try:
        passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
        return passport.register_agent(name, description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Passport agent registration failed: {str(e)}")


@app.get("/passport/agent/list")
async def passport_list_agents(user=Depends(get_current_user)):
    try:
        passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
        return passport.list_agents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Passport agent list failed: {str(e)}")


@app.post("/passport/session/create")
async def passport_create_session(request: dict, user=Depends(get_current_user)):
    raise HTTPException(
        status_code=410,
        detail="Passport no longer supports session-based API. Use agent-based execution via kpass agent model."
    )


@app.get("/passport/session/list")
async def passport_list_sessions(user=Depends(get_current_user)):
    raise HTTPException(
        status_code=410,
        detail="Passport no longer supports session-based API. Use agent-based execution via kpass agent model."
    )


@app.get("/passport/session/status/{session_id}")
async def passport_session_status(session_id: str, user=Depends(get_current_user)):
    raise HTTPException(
        status_code=410,
        detail="Passport no longer supports session-based API. Use agent-based execution via kpass agent model."
    )


@app.get("/passport/services")
async def passport_services(query: Optional[str] = None, payment_approach: Optional[str] = None, asset: Optional[str] = None, user=Depends(get_current_user)):
    try:
        passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
        return passport.discover_services(query=query, payment_approach=payment_approach, asset=asset, limit=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Passport service discovery failed: {str(e)}")


@app.post("/passport/execute")
async def passport_execute(request: dict, user=Depends(get_current_user)):
    service_id = request.get("service_id")
    amount = request.get("amount")
    parameters = request.get("parameters", {})

    if not service_id or not amount:
        raise HTTPException(status_code=400, detail="service_id and amount are required")

    try:
        passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
        return passport.execute_agent_request(service_id, str(amount), parameters=parameters)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Passport agent execution failed: {str(e)}")


@app.get("/kite/stablecoin-debug")
async def kite_stablecoin_debug():
    """Debug endpoint for configured KITE stablecoin (USDC) contract and detected decimals"""
    try:
        stablecoin_address_checksum = Web3.to_checksum_address(STABLECOIN_ADDRESS)
        contract_code = payment_processor.w3.eth.get_code(stablecoin_address_checksum).hex()
        code_size = len(contract_code) - 2
        contract_deployed = code_size > 0
    except Exception as e:
        contract_code = None
        code_size = 0
        contract_deployed = False
        code_error = str(e)
    else:
        code_error = None

    return {
        "connected": payment_processor.w3.is_connected(),
        "stablecoin_address": STABLECOIN_ADDRESS,
        "stablecoin_address_checksum": stablecoin_address_checksum if contract_deployed or code_error is None else None,
        "stablecoin_decimals": payment_processor.stablecoin_decimals,
        "contract_code_size": code_size,
        "contract_deployed": contract_deployed,
        "contract_code_error": code_error,
        "treasury_address": VALORA_TREASURY_ADDRESS,
        "chain_id": KITE_CHAIN_ID,
        "rpc_url": KITE_RPC,
        "note": f"{PAYMENT_TOKEN_SYMBOL} is the configured stablecoin contract. VALORA_TREASURY_ADDRESS must be the full KITE wallet address that receives service fees."
    }


@app.get("/kite/attestations/{user_id}")
async def get_kite_attestations(user_id: str, user=Depends(get_current_user)):
    """Get user's attestations on Kite"""
    if user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    attestations = get_user_attestations(user_id)
    return {
        "user": user_id,
        "attestation_count": len(attestations),
        "attestations": attestations
    }


@app.get("/kite/settlements")
async def get_kite_settlements(user=Depends(get_current_user)):
    """Get list of all simulated Kite settlements"""
    data = get_settlements()
    # optionally filter by user metadata
    own = [s for s in data if s.get("metadata", {}).get("user") == user["username"]]
    return {
        "user": user["username"],
        "settlement_count": len(own),
        "settlements": own
    }


# ============ ORIGINAL COMMERCE ENDPOINTS ============

@app.post("/buy")
async def buy(request: dict, user=Depends(get_current_user)):
    """Enhanced purchase with online product search capability"""
    search_online = request.get("search_online", False)

    decision = decide_purchase(request)
    if decision["status"] != "approved":
        return decision

    product = decision["product"]

    # Enforce budget caps and explicit range constraints (defensive guard)
    budget = float(request.get("budget", 0))

    from agent import parse_price_range
    min_price, max_price, _ = parse_price_range(request.get("query", ""), budget)
    max_price = min(max_price, budget)

    if product["price"] > budget or product["price"] > max_price:
        return {"status": "rejected", "reason": "over_budget"}

    valid, reason = validate(product, budget)
    if not valid:
        return {"status": "rejected", "reason": reason}

    # Recipient destination for purchase - ALWAYS Valora treasury for service fees
    recipient_address = VALORA_TREASURY_ADDRESS
    if not recipient_address:
        raise ValueError("VALORA_TREASURY_ADDRESS not configured")

    # Create product preview (without direct URL to prevent bypassing payment)
    product_preview = {
        "name": product["name"],
        "price": product["price"],
        "rating": product.get("rating"),
        "source": product.get("source", "Unknown"),
        "currency": product.get("currency", "USD")
        # Note: URL is intentionally excluded to enforce payment flow
    }

    # Preserve the real product URL for the later payment confirmation step
    purchase_token = hashlib.sha256(
        ((product.get("url") or product.get("name", "")) + str(product.get("price", 0)) + str(time.time())).encode()
    ).hexdigest()
    pending_purchase_links[purchase_token] = {
        "url": product.get("url"),
        "product": product,
        "created_at": time.time(),
        "expires_at": time.time() + 60 * 60  # expire protected link after 1 hour
    }
    save_pending_purchase_links()
    product_preview["purchase_token"] = purchase_token

    # Enhanced response with search metadata
    payment_info = {
        "status": "payment_required",
        "product": product_preview,  # Preview without URL
        "amount": product["price"],
        "currency": PAYMENT_TOKEN_SYMBOL,
        "source": decision.get("source", "local_catalog"),
        "x402": True,
        "message": f"Pay commission in {PAYMENT_TOKEN_SYMBOL} to access direct purchase link and complete transaction on Kite"
    }

    # Include search results if from online search (also without URLs)
    if "search_results" in decision:
        preview_results = []
        for result in decision["search_results"]:
            preview_results.append({
                "name": result["name"],
                "price": result["price"],
                "rating": result.get("rating"),
                "source": result.get("source"),
                "currency": result.get("currency", "USD")
                # URL excluded
            })
        payment_info["search_results"] = preview_results

    return JSONResponse(status_code=402, content=payment_info)


@app.get("/redeem/{product_token}")
async def redeem_product_link(product_token: str):
    """Redirect the secured product token to the real merchant URL."""
    token_info = pending_purchase_links.get(product_token)
    if not token_info:
        raise HTTPException(status_code=404, detail="Protected purchase link not found or expired")

    expires_at = token_info.get("expires_at")
    if expires_at and time.time() > expires_at:
        pending_purchase_links.pop(product_token, None)
        save_pending_purchase_links()
        raise HTTPException(status_code=404, detail="Protected purchase link has expired")

    target_url = token_info.get("url")
    if not target_url:
        raise HTTPException(status_code=500, detail="Protected purchase link target unavailable")

    return RedirectResponse(target_url, status_code=302)


@app.post("/confirm-payment")
async def confirm_payment(request: dict, user=Depends(get_current_user)):
    """
    Process confirmed payment using Kite Agent Passport.
    Executes payment through Passport agent execution workflow.
    """
    product = request.get("product")
    product_token = request.get("product_token")
    wallet_address = request.get("wallet_address")
    signature = request.get("signature")

    if not product or not wallet_address:
        raise HTTPException(status_code=400, detail="product and wallet_address required")

    # Validate and sanitize product name
    product_name = product.get("name", "").strip()
    if not product_name:
        raise HTTPException(status_code=400, detail="Product name is required")

    # Ensure product name is not too long (limit to 200 chars)
    if len(product_name) > 200:
        print(f"DEBUG: Product name too long ({len(product_name)} chars), truncating")
        product_name = product_name[:200] + "..."

    # Use Valora treasury as the recipient for all payments
    recipient_address = VALORA_TREASURY_ADDRESS
    if not recipient_address:
        raise HTTPException(status_code=500, detail="Treasury address not configured")
    print(f"💰 Valora Treasury Address: {recipient_address}")

    # Convert amount to stablecoin charge (service charge)
    amount_usd = float(product.get("price", 0))
    charge_stablecoin = MIN_STABLECOIN_CHARGE  # Fixed service charge

    print(f"DEBUG: Product price: ${amount_usd}")
    print(f"DEBUG: {PAYMENT_TOKEN_SYMBOL} charge: {charge_stablecoin}")

    # Verify signature if provided
    payment_payload = {
        'currency': PAYMENT_TOKEN_SYMBOL,
        'price': product.get('price'),
        'product_name': product_name
    }
    message = f"Autobuy payment confirmation {json.dumps(payment_payload, sort_keys=True, separators=(',', ':'))}"

    if signature:
        try:
            recovered_address = payment_processor.verify_signature(message, signature)
            if recovered_address.lower() != wallet_address.lower():
                raise HTTPException(status_code=401, detail="Invalid signature")
            print(f"✅ Signature verified for address: {recovered_address}")
        except Exception as e:
            print(f"ERROR: Signature verification failed: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")
    else:
        print("⚠️ No signature provided. Proceeding with Passport agent execution.")

    # Get the actual product URL (real retailer link) or fallback to redeem route
    product_url = None
    if product_token:
        link_entry = pending_purchase_links.get(product_token)
        if link_entry:
            product_url = link_entry.get("url")
            if not product_url:
                print(f"WARNING: No URL stored for product_token {product_token}")
        else:
            print(f"WARNING: product_token {product_token} not found in pending_purchase_links")

        if not product_url:
            product_url = f"{APP_BASE_URL}/redeem/{product_token}"

    # Initialize Kite Passport
    try:
        passport = get_passport(base_url=KITE_PASSPORT_BASE_URL)
        print("✅ Kite Passport initialized")
    except RuntimeError as e:
        error_msg = str(e)
        if "kpass CLI is not installed" in error_msg or "not found in PATH" in error_msg:
            print(f"ERROR: kpass CLI not found. Please install: curl -fsSL https://agentpassport.ai/install.sh | bash")
            raise HTTPException(
                status_code=503,
                detail="Kite Passport CLI (kpass) is not installed. Please install it first: curl -fsSL https://agentpassport.ai/install.sh | bash"
            )
        print(f"ERROR: Failed to initialize Kite Passport: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Passport initialization failed: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: Failed to initialize Kite Passport: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Passport service unavailable: {error_msg}")

    # Execute payment through Passport via agent-based execution.
    # The session-based Passport workflow is deprecated.
    session_id = None

    try:
        # Execute payment through Passport using the Passport wallet CLI.
        # Direct transfer is performed via kpass wallet send instead of the deprecated agent:execute flow.
        payment_result = passport.execute_agent_request(
            service_query=f"Transfer {charge_stablecoin} {PAYMENT_TOKEN_SYMBOL} to {recipient_address}",
            payment_amount=charge_stablecoin,
            payment_asset=PAYMENT_TOKEN_SYMBOL,
            recipient_address=recipient_address,
            user_address=wallet_address
        )

        if payment_result.get("status") != "success":
            raise Exception(
                f"Payment not completed: {payment_result.get('message')} (status={payment_result.get('status')})"
            )

        print(f"✅ Payment executed via Passport agent execution: {payment_result.get('tx_hash', 'unknown')}")

        # Record settlement in Kite settlement system
        settlement = settle_payment_on_kite(
            task_id=payment_result.get("tx_hash", f"passport_tx_{int(time.time())}"),
            user_address=wallet_address,
            payment_amount_usdc=charge_stablecoin,
            vendor_address=recipient_address
        )

        print(f"✅ Settlement recorded: {settlement}")

    except Exception as e:
        print(f"ERROR: Payment execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment execution failed: {str(e)}")

    return {
        "status": "payment_completed",
            "message": "Payment completed successfully through Kite Agent Passport execution with scoped controls.",
            "payment_status": "completed",
            "product_token": product_token,
            "product_url": product_url,
            "product_source": product.get("store") or product.get("source"),
            "payment_tx": payment_result,
            "payment_instructions": "Payment processed through Kite Agent Passport execution with scoped controls.",
            "session_id": None,  # No session-based API
            "recipient": recipient_address,
            "amount_stablecoin": charge_stablecoin,
            "product": {
                "name": product_name,
                "price": amount_usd,
                "url": product_url,
                "source": product.get("source"),
                "store": product.get("store")
            },
            "passport_details": {
                "agent_execution": True,
                "scoped_controls": payment_result.get("scoped_controls"),
                "budget_used": charge_stablecoin,
                "asset": PAYMENT_TOKEN_SYMBOL,
                "executed_via_passport_agent": True
            }
        }
    """Create subscription"""
    decision = decide_purchase(request)
    if decision["status"] != "approved":
        return decision

    product = decision["product"]
    valid, reason = validate(product, request["budget"])
    if not valid:
        return {"status": "rejected", "reason": reason}

    frequency = request.get("frequency_days", 30)
    sub = create_subscription(
        user_id=user["id"],
        product=product,
        budget=request["budget"],
        frequency_days=frequency
    )

    payment_info = {
        "status": "payment_required",
        "subscription": sub,
        "product": product,
        "amount": product["price"],
        "currency": PAYMENT_TOKEN_SYMBOL,
        "frequency_days": frequency
    }
    return JSONResponse(status_code=402, content=payment_info)


# ============ BLOCKCHAIN WALLET ENDPOINTS ============

from blockchain_requirements import wallet_service

@app.post("/wallet/check-requirements")
async def check_wallet_requirements(request: dict, user=Depends(get_current_user)):
    """
    Check if user's wallet has:
    1. KITE AI network configured
    2. Sufficient KITE for gas fees
    3. Sufficient stablecoin for purchases
    
    Returns setup instructions if needed
    """
    wallet_address = request.get("wallet_address")
    if not wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address required")

    requirements = wallet_service.check_wallet_requirements(wallet_address)
    
    return {
        "wallet": wallet_address,
        "requirements": requirements,
        "setup_required": not requirements["ready_to_purchase"],
        "issues": requirements["issues"],
    }


@app.get("/wallet/balances/{wallet_address}")
async def get_wallet_balances(wallet_address: str, user=Depends(get_current_user)):
    """Get real-time KITE and stablecoin balances from blockchain"""
    kite = wallet_service.get_kite_balance(wallet_address)
    stablecoin = wallet_service.get_stablecoin_balance(wallet_address)
    
    return {
        "wallet": wallet_address,
        "kite": kite,
        "stablecoin": stablecoin,
        "network": {
            "name": "KITE AI Mainnet",
            "chainId": KITE_CHAIN_ID,
            "explorer": "https://kitescan.ai/",
        }
    }


@app.get("/wallet/ready-for-payment/{wallet_address}")
async def check_wallet_ready_for_payment(wallet_address: str, user=Depends(get_current_user)):
    """
    Check if wallet has BOTH KITE and stablecoin tokens for payment
    Returns ready status and simple message
    """
    wallet_ready = payment_processor.check_wallet_ready_for_payment(wallet_address)
    
    if not wallet_ready.get("ready", False):
        wallet_ready["formatted_message"] = "Insufficient Fund"
    else:
        wallet_ready["formatted_message"] = "Ready"
    
    return wallet_ready


@app.get("/wallet/network-config")
async def get_network_config():
    """Get KITE AI network configuration for wallet setup"""
    return {
        "network": wallet_service.check_wallet_requirements("0x0")["network"],
        "stablecoin": wallet_service.check_wallet_requirements("0x0")["stablecoin"],
    }


@app.get("/wallet/faucets")
async def get_faucet_links():
    """Get faucet links for acquiring test tokens"""
    return wallet_service.get_faucet_info()


@app.post("/payment/prepare")
async def prepare_payment(request: dict, user=Depends(get_current_user)):
    """
    Prepare stablecoin transfer transaction
    Frontend signs and sends back the transaction
    """
    from_address = request.get("from_address")
    to_address = request.get("to_address")
    amount_usd = request.get("amount_usd")

    if not all([from_address, to_address, amount_usd]):
        raise HTTPException(status_code=400, detail="from_address, to_address, amount_usd required")

    # Validate parameters
    validation = payment_processor.validate_payment_params(from_address, to_address, amount_usd)
    if not validation["valid"]:
        return {"success": False, "errors": validation["errors"]}

    # Prepare transaction
    tx_prep = payment_processor.prepare_stablecoin_transfer(from_address, to_address, amount_usd)
    
    if tx_prep["success"]:
        # Add gas estimation
        gas_estimate = payment_processor.estimate_gas_cost()
        tx_prep["gas_estimate"] = gas_estimate
    
    return tx_prep


@app.post("/payment/submit")
async def submit_payment(request: dict, user=Depends(get_current_user)):
    """
    Submit signed transaction to blockchain
    Triggered after the Kite AA wallet or bundler signs the transaction
    """
    signed_tx = request.get("signed_tx")
    if not signed_tx:
        raise HTTPException(status_code=400, detail="signed_tx required")

    result = payment_processor.send_stablecoin_transaction(signed_tx)
    
    return result


@app.get("/payment/status/{tx_hash}")
async def get_payment_status(tx_hash: str, user=Depends(get_current_user)):
    """Get real-time transaction status"""
    status = payment_processor.get_transaction_status(tx_hash)
    
    # Also wait briefly for confirmation
    if status.get("status") == "pending":
        confirmation = payment_processor.wait_for_transaction(tx_hash, timeout=30)
        if confirmation.get("success"):
            return confirmation
    
    return status


@app.post("/payment/confirm")
async def confirm_payment_blockchain(request: dict, user=Depends(get_current_user)):
    """
    Confirm payment and verify on blockchain
    Called after transaction is mined
    """
    tx_hash = request.get("tx_hash")
    product_id = request.get("product_id")
    
    if not tx_hash:
        raise HTTPException(status_code=400, detail="tx_hash required")

    # Wait for confirmation
    confirmation = payment_processor.wait_for_transaction(tx_hash)
    
    if not confirmation.get("success"):
        return {
            "status": "failed",
            "error": confirmation.get("error", "Transaction failed"),
            "tx_hash": tx_hash
        }

    # Record on Kite attestation
    attestation = record_attestation_on_kite(
        task_id=tx_hash,
        user_address=request.get("from_address"),
        payment_amount=request.get("amount_usd"),
        output_hash=product_id or ""
    )

    return {
        "status": "confirmed",
        "tx_hash": tx_hash,
        "block_number": confirmation.get("block_number"),
        "transaction_fee_kite": confirmation.get("transaction_fee_kite"),
        "attestation": attestation,
        "explorer_url": confirmation.get("explorer_url")
    }


# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "services": {
            "commerce": "operational",
            "kite": kite_health_check(),
            "blockchain": "connected" if wallet_service.is_connected() else "disconnected"
        }
    }
