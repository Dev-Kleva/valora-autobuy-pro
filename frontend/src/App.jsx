import { useState } from "react";
import axios from "axios";
import { getAccountAddress } from "./kiteAA";
import "./App.css";

export default function App() {
  const [screen, setScreen] = useState("login");
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [walletAddress, setWalletAddress] = useState(null);
  const [walletInput, setWalletInput] = useState("");
  const [derivedAAAddress, setDerivedAAAddress] = useState(null);
  
  // Product search
  const [productQuery, setProductQuery] = useState("");
  const [productBudget, setProductBudget] = useState("");
  const [productResults, setProductResults] = useState(null);
  const [searchingProduct, setSearchingProduct] = useState(false);
  const [confirmingPayment, setConfirmingPayment] = useState(false);
  const [confirmPaymentResult, setConfirmPaymentResult] = useState(null);
  const [showPassportInstructions, setShowPassportInstructions] = useState(false);
  
  // Kite health
  const [kiteStatus, setKiteStatus] = useState(null);
  const [settlements, setSettlements] = useState([]);
  const [remainingBudget, setRemainingBudget] = useState(null);

  const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8001";
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const handleRegister = async () => {
    try {
      const res = await axios.post(`${API_BASE}/register`, { username, password });
      setToken(res.data.token);
      setScreen("passportSetup");
      setUsername("");
      setPassword("");
    } catch (e) {
      alert(`Registration failed: ${e.response?.data?.detail || e.message}`);
    }
  };

  const handleLogin = async () => {
    try {
      const res = await axios.post(`${API_BASE}/login`, { username, password });
      setToken(res.data.token);
      setScreen("passportSetup");
      setUsername("");
      setPassword("");
    } catch (e) {
      alert(`Login failed: ${e.response?.data?.detail || e.message}`);
    }
  };

  const checkKiteHealth = async () => {
    try {
      const res = await axios.get(`${API_BASE}/kite/health`);
      setKiteStatus(res.data);
    } catch (e) {
      console.error("Kite health check failed:", e);
    }
  };

  const loadKiteSettlements = async () => {
    try {
      const res = await axios.get(`${API_BASE}/kite/settlements`, { headers });
      setSettlements(res.data.settlements || []);
    } catch (e) {
      console.error("Failed to load kite settlements:", e);
    }
  };

  const handleProductSearch = async () => {
    if (!productQuery.trim() || !productBudget || Number(productBudget) <= 0) {
      alert("Enter product and budget");
      return;
    }

    setSearchingProduct(true);
    setProductResults(null);
    setConfirmPaymentResult(null);
    setRemainingBudget(Number(productBudget));

    try {
      const res = await axios.post(
        `${API_BASE}/buy`,
        {
          query: productQuery,
          budget: Number(productBudget),
          search_online: true
        },
        { headers }
      );

      setProductResults(res.data);
      if (res.data.status === "payment_required") {
        const used = Number(res.data.product?.price || 0);
        setRemainingBudget(Number(productBudget) - used);
      }
    } catch (e) {
      // Handle 402 (Payment Required) as success
      if (e.response?.status === 402) {
        setProductResults(e.response.data);
        const used = Number(e.response.data.product?.price || 0);
        setRemainingBudget(Number(productBudget) - used);
      } else {
        const error = e.response?.data || e.message;
        setProductResults({ status: "error", error });
      }
    } finally {
      setSearchingProduct(false);
    }
  };

  const handleWalletAddressSubmit = async () => {
    if (!walletInput || !walletInput.trim()) {
      alert("Enter your Kite AA smart wallet address or owner address.");
      return;
    }

    const normalized = walletInput.trim();
    try {
      const aaAddress = await getAccountAddress(normalized);
      setWalletAddress(aaAddress || normalized);
      setDerivedAAAddress(aaAddress);
    } catch (e) {
      console.warn("Could not derive Kite AA address, using entered address:", e);
      setWalletAddress(normalized);
      setDerivedAAAddress(null);
    }
  };

  const handleConfirmProductPayment = async () => {
    if (!productResults || productResults.status !== "payment_required") {
      alert("No payable product selected");
      return;
    }

    const normalizedInput = walletInput?.trim();
    const effectiveWallet = walletAddress || normalizedInput;

    if (!effectiveWallet) {
      alert("Provide your Kite AA wallet address before confirming payment.");
      return;
    }

    let resolvedWalletAddress = effectiveWallet;
    if (!walletAddress && normalizedInput) {
      try {
        const aaAddress = await getAccountAddress(normalizedInput);
        if (aaAddress) {
          resolvedWalletAddress = aaAddress;
          setWalletAddress(aaAddress);
          setDerivedAAAddress(aaAddress);
        } else {
          setWalletAddress(normalizedInput);
        }
      } catch (e) {
        console.warn("Could not derive Kite AA address from typed input, using raw value:", e);
        setWalletAddress(normalizedInput);
        setDerivedAAAddress(null);
      }
    }

    const product = productResults.product;
    const productToken = product.purchase_token;

    try {
      setConfirmingPayment(true);
      setConfirmPaymentResult(null);

      const requestBody = {
        product,
        wallet_address: resolvedWalletAddress,
      };
      if (productToken) {
        requestBody.product_token = productToken;
      }

      const response = await axios.post(
        `${API_BASE}/confirm-payment`,
        requestBody,
        { headers }
      );

      const data = response.data;
      if (!data.payment_tx) {
        throw new Error("Payment request data missing from confirm-payment response");
      }

      setConfirmPaymentResult({
        status: "success",
        data: {
          ...data,
          payment_status: "ready",
          message: "Payment request prepared. Submit through Kite Agent Passport execution.",
        }
      });

      await loadKiteSettlements();
    } catch (e) {
      setConfirmPaymentResult({ status: "error", error: e.response?.data || e.message });
    } finally {
      setConfirmingPayment(false);
    }
  };

  const handlePassportReady = async () => {
    if (!token) {
      setScreen("login");
      return;
    }
    setScreen("commerce");
    checkKiteHealth();
    await loadKiteSettlements();
  };

  const handleLogout = () => {
    setToken(null);
    setScreen("login");
  };

  return (
    <div className="App">
      <header className="header">
        <h1>🚀 Kite Agent Passport</h1>
        <p className="hero-subtitle">
          Let your AI agent discover and pay for services on your behalf while you stay in control with scoped Passport agent execution.
        </p>
        {token && <button onClick={handleLogout} className="logout-btn">Logout</button>}
      </header>

      {/* Login / Register */}
      {screen === "login" && (
        <div className="auth-container">
          <div className="auth-box">
            <h2>Get Started with Kite Agent Passport</h2>
            <p className="auth-copy">
              Login to your Passport-backed account, then approve your AI agent's payment execution using a secure passkey. Your agent can discover and pay for services autonomously within the controls you define.
            </p>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button onClick={handleLogin}>Login to Passport</button>
            <button onClick={handleRegister} className="secondary">
              Create Passport Account
            </button>
            <button
              className="secondary"
              onClick={() => setScreen("passportSetup")}
              style={{ marginTop: '12px' }}
            >
              Launch Passport Setup
            </button>
          </div>
        </div>
      )}

      {/* Passport Setup */}
      {screen === "passportSetup" && (
        <div className="container">
          <div className="passport-setup-box">
            <h2>Passport Onboarding</h2>
            <p>
              Your AI agent uses Kite Agent Passport to discover services, execute payments, and pay on your behalf. Review these steps, then continue when Passport is ready.
            </p>
            <div className="passport-steps">
              <div className="passport-step">
                <strong>1. Install Passport CLI</strong>
                <p>Use the official Kite Agent Passport installer link below if you do not have it yet.</p>
              </div>
              <div className="passport-step">
                <strong>2. Sign up and create a passkey</strong>
                <p>Verify your email and set up a secure passkey so Passport can approve payments.</p>
              </div>
              <div className="passport-step">
                <strong>3. Register the AutoBuy agent</strong>
                <p>Register the agent so it can request and execute Passport payment approvals.</p>
              </div>
              <div className="passport-step">
                <strong>4. Confirm a Passport payment</strong>
                <p>When your agent needs to pay, approve a session and let it work within your limits.</p>
              </div>
            </div>
            <div className="passport-actions">
              <button onClick={handlePassportReady} className="primary">
                I have Passport ready
              </button>
              <button
                className="secondary"
                onClick={() => setShowPassportInstructions(true)}
              >
                View Passport Instructions
              </button>
            </div>
            {showPassportInstructions && (
              <div className="passport-instructions-box" style={{ marginTop: '18px', padding: '16px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fafafa' }}>
                <h3>Need help installing Passport?</h3>
                <p>Try these steps to get started:</p>
                <ol>
                  <li>Install Kite Agent Passport on your computer.</li>
                  <li>Sign up and verify your email.</li>
                  <li>Create a secure passkey for payment approvals.</li>
                  <li>Register the AutoBuy agent in Passport.</li>
                </ol>
                <p>
                  For a full installation guide, visit:
                  <a href="https://agentpassport.ai" target="_blank" rel="noreferrer" style={{ marginLeft: '4px' }}>
                    agentpassport.ai
                  </a>
                </p>
                <button onClick={() => setShowPassportInstructions(false)} className="secondary">
                  Hide instructions
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Commerce */}
      {screen === "commerce" && token && (
        <div className="container">
          <div className="kite-status">
            {kiteStatus && (
              <p>
                🔗 Kite: <strong>{kiteStatus.status}</strong> on{" "}
                {kiteStatus.network}
              </p>
            )}
          </div>

          <div className="passport-summary">
            <h2>How Kite Agent Passport Works</h2>
            <ul>
              <li>Your AI agent searches for products or services that match your request.</li>
              <li>When payment is needed, it submits a Passport payment request with scoped controls.</li>
              <li>You approve the session once with your passkey, then the agent can act autonomously within those limits.</li>
              <li>No extra approvals are required until the session expires or the budget is used.</li>
            </ul>
          </div>

          <div className="product-search-box">
            <h2>Find Product Online</h2>
            <div style={{marginBottom: '10px'}}>
              {walletAddress ? (
                <>
                  <p>AA Wallet address in use: <strong>{walletAddress}</strong></p>
                  {derivedAAAddress && derivedAAAddress !== walletAddress && (
                    <p className="hint">Derived AA address: {derivedAAAddress}</p>
                  )}
                </>
              ) : (
                <div style={{display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap'}}>
                  <input
                    type="text"
                    placeholder="Paste your Kite AA wallet address or EOA owner address"
                    value={walletInput}
                    onChange={(e) => setWalletInput(e.target.value)}
                    style={{flex: 1, minWidth: '280px', padding: '8px'}}
                  />
                  <button onClick={handleWalletAddressSubmit} style={{marginBottom:'10px'}}>
                    Use Kite AA Wallet
                  </button>
                </div>
              )}
            </div>
            <input
              type="text"
              placeholder="e.g. laptop $500 to $600"
              value={productQuery}
              onChange={(e) => setProductQuery(e.target.value)}
            />
            <input
              type="number"
              placeholder="Budget (USD)"
              value={productBudget}
              onChange={(e) => setProductBudget(e.target.value)}
            />
            <button onClick={handleProductSearch} disabled={searchingProduct}>
              {searchingProduct ? "Searching..." : "Search Product"}
            </button>

            {productResults && (
              <div className="product-results">
                {productResults.status === "error" ? (
                  <p className="error">Error: {JSON.stringify(productResults.error)}</p>
                ) : productResults.status === "payment_required" ? (
                  <>
                    <h3>Best Match</h3>
                    <p>{productResults.product.name}</p>
                    <p>Price: ${productResults.product.price.toFixed(2)}</p>
                    <p>Source: <strong>{productResults.product.source || productResults.product.store || 'Unknown'}</strong></p>
                    <p>Remaining budget: ${remainingBudget != null ? remainingBudget.toFixed(2) : 'N/A'}</p>
                    <p>In-range: {productResults.product.price <= Number(productBudget) ? 'yes' : 'no'}</p>
                    <p>Not sponsor: {(!productResults.product.name.toLowerCase().includes('ad based') && !productResults.product.name.toLowerCase().includes('sponsored')) ? 'yes' : 'no'}</p>
                    <p className="payment-message">{productResults.message}</p>

                    <h4>Top Results</h4>
                    <ul>
                      {productResults.search_results?.map((item, idx) => (
                        <li key={idx}>
                          <strong>{item.name}</strong> - ${item.price.toFixed(2)} - {item.source || item.store || 'Unknown source'}
                        </li>
                      ))}
                    </ul>

                    <div className="payment-summary">
                      <p>
                        Your AI agent has requested a Passport payment for this purchase. Confirm it below to let Passport execute the payment with scoped controls.
                      </p>
                    </div>

                    <div className="payment-confirmation">
                      <button onClick={handleConfirmProductPayment} disabled={confirmingPayment}>
                        {confirmingPayment ? "Confirming payment..." : "Confirm Passport payment"}
                      </button>

                      {confirmPaymentResult && confirmPaymentResult.status === "success" && (
                        <div className="success">
                          <h5>Payment Request Ready</h5>
                          <p>Status: <strong>{confirmPaymentResult.data.payment_status}</strong></p>
                          {confirmPaymentResult.data.payment_instructions && (
                            <p>{confirmPaymentResult.data.payment_instructions}</p>
                          )}
                          {confirmPaymentResult.data.tx_hash && (
                            <p>Tx Hash: <code>{confirmPaymentResult.data.tx_hash?.substring(0, 20)}...</code></p>
                          )}
                      {confirmPaymentResult.data.product_source && (
                        <p>Product source: <strong>{confirmPaymentResult.data.product_source}</strong></p>
                      )}
                      {confirmPaymentResult.data.product_url && (
                        <p><a href={confirmPaymentResult.data.product_url} target="_blank" rel="noreferrer" className="product-link">🛒 Open Product Link</a></p>
                      )}
                          {confirmPaymentResult.data.explorer_url && (
                            <p><a href={confirmPaymentResult.data.explorer_url} target="_blank" rel="noreferrer">View on Block Explorer</a></p>
                          )}
                          {confirmPaymentResult.data.payment_tx && (
                            <div className="payment-payload">
                              <h5>Payment Details</h5>
                              <div className="payment-summary">
                                <div className="payment-item">
                                  <span className="payment-label">Amount:</span>
                                  <span className="payment-value">{confirmPaymentResult.data.payment_tx.amount} {confirmPaymentResult.data.payment_tx.asset || 'USDC'}</span>
                                </div>
                                <div className="payment-item">
                                  <span className="payment-label">Recipient:</span>
                                  <span className="payment-value">{confirmPaymentResult.data.payment_tx.recipient?.substring(0, 6)}...{confirmPaymentResult.data.payment_tx.recipient?.substring(38)}</span>
                                </div>
                                <div className="payment-item">
                                  <span className="payment-label">Transaction:</span>
                                  <span className="payment-value">{confirmPaymentResult.data.payment_tx.tx_hash?.substring(0, 20)}...</span>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {confirmPaymentResult && confirmPaymentResult.status === "error" && (
                        <div className="error">Error: {JSON.stringify(confirmPaymentResult.error)}</div>
                      )}
                    </div>
                  </>
                ) : (
                  <p>No matching product found within budget.</p>
                )}
              </div>
            )}
          </div>

          {/* Settlements on Kite */}
          {settlements.length > 0 && (
            <div className="settlements-box">
              <h3>Kite Settlements ({settlements.length})</h3>
              <div className="settlement-list">
                {settlements.map((s) => (
                  <div key={s.settlement_id} className="settlement-item">
                    <p>🧾 ID: {s.settlement_id}</p>
                    <p>Amount: ${s.amount}</p>
                    <p>Tx: {s.tx_hash.substring(0, 20)}...</p>
                    <p>Status: <strong>{s.status}</strong></p>
                    <small>{new Date(s.settled_at).toLocaleString()}</small>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}