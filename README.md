# 🤖 Valora AutoBuy Agent

A full-stack proof-of-concept that combines a React frontend with a FastAPI backend to discover products, require payment before revealing merchant links, and settle the resulting service fee through Kite Agent Passport.

## What this project actually does

- The frontend is a React app that authenticates users, performs product search requests, and submits payment confirmations.
- The backend is a FastAPI service that evaluates purchase requests, returns a payment-required preview, and executes payment through Kite Passport.
- Product URLs are intentionally withheld from search responses until payment is confirmed.
- Payments are executed using Kite Agent Passport via the `kpass` CLI and an agent-based transfer request.
- The backend stores pending purchase tokens in `backend/pending_purchase_links.json` and redirects redeemed tokens to the real product URL.

## Key implementation details

- `backend/main.py` exposes the real API used by the app:
  - `POST /register`
  - `POST /login`
  - `GET /me`
  - `POST /buy`
  - `POST /confirm-payment`
  - `GET /kite/health`
  - `GET /kite/settlements`
  - `POST /passport/execute`

- The `/buy` endpoint returns a `402` response when payment is required, with a product preview that omits the direct merchant URL.
- The frontend collects a Kite AA wallet address or owner address, derives an AA address via `frontend/src/kiteAA.js`, and sends it to `/confirm-payment`.
- The backend uses `kite_passport.py` and the `kpass` CLI to execute the payment as a Passport agent transfer.

## Actual technology stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.10+, FastAPI, Web3.py |
| Frontend | React 18, Axios, Ethers 6, gokite-aa-sdk |
| Wallet integration | Kite Agent Passport (`kpass`) |
| Payment flow | `POST /buy` → `402 payment_required` → `POST /confirm-payment` |
| Storage | JSON-backed pending purchase links |

## What this project does not currently do

- It does not use MetaMask or browser-based `personal_sign` for the payment confirmation flow.
- It does not expose raw product URLs before payment.
- It does not currently use a production database; pending links are stored in a JSON file.
- It does not assume full multi-chain settlement; it is implemented around the Kite Passport / Kite AA flow.

## Repo structure

- `backend/` — FastAPI backend and purchase/payment logic
- `frontend/` — React app UI
- `frontend/src/App.jsx` — app screens, login, search, wallet address entry, payment confirmation logic
- `frontend/src/kiteAA.js` — Kite AA address derivation using `gokite-aa-sdk`
- `backend/pending_purchase_links.json` — stored protected purchase links
- `backend/kite_passport.py` — Kite Passport integration wrapper

## Setup

### Backend prerequisites
- Python 3.10+
- `backend/requirements.txt` dependencies
- `kpass` CLI installed and available on PATH
- `VALORA_TREASURY_ADDRESS` set to a valid Kite wallet address
- `KITE_PASSPORT_BASE_URL` set if you want a non-default Passport endpoint

### Backend install and run

```bash
cd backend
pip install -r requirements.txt
```

Create either root `.env` or `backend/.env` (or both). The backend loads both files and uses `backend/.env` to override root values.

Required values:

```env
VALORA_TREASURY_ADDRESS=0xYourKiteTreasuryAddress
KITE_PASSPORT_BASE_URL=https://passport.dev.gokite.ai
APP_BASE_URL=http://localhost:8001
```

Start the backend:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Frontend install and run

```bash
cd frontend
npm install
```

Create `frontend/.env` or use environment variables:

```env
REACT_APP_API_URL=http://localhost:8001
REACT_APP_KITE_AA_NETWORK=kite_mainnet
REACT_APP_KITE_AA_RPC_URL=https://rpc.gokite.ai/
REACT_APP_KITE_AA_BUNDLER_RPC=https://bundler-service.staging.gokite.ai/rpc/
```

Start the frontend:

```bash
npm start
```

Open `http://localhost:3000`.

## Frontend behavior

- Users register and log in with the app.
- The app prompts for a Kite AA smart wallet address or owner address.
- Product search requests are sent to `/buy`.
- If the purchase requires payment, the response includes `status: payment_required` and `x402: true`.
- The user confirms payment and the frontend calls `/confirm-payment` with the chosen wallet address.
- The backend then executes the payment through Kite Passport.

## Environment variables used by the repo

### Backend
- `VALORA_TREASURY_ADDRESS`
- `KITE_PASSPORT_BASE_URL`
- `APP_BASE_URL`

### Frontend
- `REACT_APP_API_URL`
- `REACT_APP_KITE_AA_NETWORK`
- `REACT_APP_KITE_AA_RPC_URL`
- `REACT_APP_KITE_AA_BUNDLER_RPC`
- `REACT_APP_KITE_AA_EOA_PRIVATE_KEY` (used by `frontend/src/kiteAA.js` for advanced direct payment SDK calls)

## Notes

- This repository is a working prototype, not a polished production deployment.
- The payment confirmation flow is Passport agent-based, not browser-wallet-based.
- The product search flow intentionally hides merchant URLs until payment is confirmed.

## License

MIT License.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/buy` | Request product search and purchase recommendation |
| GET | `/tasks` | List user's purchase tasks |
| GET | `/task/{id}` | Get task details |

### Kite Settlement
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/kite/health` | Check Kite connectivity |
| GET | `/kite/attestations/{user_id}` | Get user's attestations |

### Example Request

```bash
# Login
curl -X POST http://localhost:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'

# Purchase Discovery Request
curl -X POST http://localhost:8001/buy \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query":"wireless headphones under $150","budget_usd":150}'
```

---

## 🐳 Docker Deployment

### Build

```bash
docker build -t autobuy-agent .
```

### Run Locally

```bash
docker run -p 8001:8001 \
  -e KITE_RPC_URL=https://rpc.gokite.ai/ \
  -e USDC_ADDRESS=0x7aB6f3ed87C42eF0aDb67Ed95090f8bF5240149e \
  autobuy-agent
```

---

## ☁️ Production Deployment

### Option 1: Vercel Frontend + Railway Backend (Recommended)

**Deploy Backend to Railway:**
1. Push to GitHub
2. Go to railway.app
3. Connect your repo
4. Set environment variables
5. Deploy (auto-starts `uvicorn main:app`)

**Deploy Frontend to Vercel:**
1. Push to GitHub
2. Go to vercel.com
3. Import project
4. Set `REACT_APP_API_URL` env var
5. Deploy

### Option 2: Heroku (All-in-one)

```bash
heroku login
heroku create autobuy-agent
git push heroku main
```

### Option 3: Docker + AWS/GCP

```bash
# Build & push to registry
docker build -t gcr.io/PROJECT/autobuy-agent .
docker push gcr.io/PROJECT/autobuy-agent

# Deploy to Cloud Run / ECS
# Configure RPC/API key secrets in cloud provider
```

---

## 🔐 Environment Variables

**Required:**
```
KITE_RPC_URL=https://rpc.gokite.ai/     # Kite RPC endpoint (KiteAI Mainnet)
USDC_ADDRESS=0x7aB6f3ed87C42eF0aDb67Ed95090f8bF5240149e
JWT_SECRET=your-secret-key                     # For token signing
```

**Optional:**
```
DATABASE_URL=postgresql://...                  # For persistence
```

---

## 📊 Smart Contracts

### Kite Attestation Contract

Deployed on Kite AI Mainnet. Records:
- **Task ID** - Unique identifier
- **User Address** - Task creator
- **Payment Amount** - USDC settled
- **Output Hash** - SHA256 of the task record
- **Agent Signature** - Proof of agent execution
- **Timestamp** - Block timestamp

**Functions:**
- `attesta()` - Record attestation
- `settlePayment()` - Settle USDC
- `getAttestation()` - Retrieve proof
- `verifyAttestation()` - Verify signature

---

## 🎨 UI Screenshots

### Login/Register Screen
- Username & password input
- Register or login buttons

### Purchase Discovery Screen
- Search query input
- Budget and filter controls
- Product recommendation cards
- Kite attestation logs

### Confirmation Screen  
- Purchase recommendation details
- Output hash verification
- Payment amount and Kite settlement
- "Settle on Kite" button

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/awesome`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push branch (`git push origin feature/awesome`)
5. Open Pull Request

---

## 📝 License

MIT

---

## 🙋 Support

- **Issues** - GitHub Issues
- **Discord** - Kite AI Discord community

---

## 🚀 Hackathon Submission

This project fully meets the **Kite AI Global Hackathon 2026** requirements:

✅ Autonomous AI agent executing real tasks  
✅ USDC payment settlement on Kite chain  
✅ On-chain attestation proof (task ID, user, hash, signature)  
✅ Production-ready (Docker + cloud deployable)  
✅ Functional UI with full user workflows  
✅ Publicly accessible demo available

---

## 📞 Questions?

Contact us or join the Kite AI Discord for support!