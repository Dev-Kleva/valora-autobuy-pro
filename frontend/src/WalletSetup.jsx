import React, { useState, useEffect } from "react";
import axios from "axios";
import { ethers } from "ethers";
import "./WalletSetup.css";

const WalletSetup = ({ walletAddress, onReady, API_BASE, headers }) => {
  const [requirements, setRequirements] = useState(null);
  const [balances, setBalances] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [step, setStep] = useState(0);

  const STEPS = [
    "Check Wallet",
    "Add Network",
    "Add USDC Token",
    "Fund Wallet",
    "Ready!"
  ];

  useEffect(() => {
    if (walletAddress) {
      checkRequirements();
    }
  }, [walletAddress]);

  const checkRequirements = async () => {
    try {
      setLoading(true);
      const res = await axios.post(
        `${API_BASE}/wallet/check-requirements`,
        { wallet_address: walletAddress },
        { headers }
      );

      setRequirements(res.data.requirements);
      
      // Get current balances
      const balanceRes = await axios.get(
        `${API_BASE}/wallet/balances/${walletAddress}`,
        { headers }
      );
      setBalances(balanceRes.data);

      if (res.data.requirements.ready_to_purchase) {
        setStep(4);
        onReady?.(true);
      } else {
        setStep(0);
        onReady?.(false);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const addNetwork = async () => {
    try {
      setLoading(true);
      const netRes = await axios.get(`${API_BASE}/wallet/network-config`, { headers });
      const networkConfig = netRes.data.network.config;

      alert(`Configure Kite AI Mainnet in your wallet:\n` +
        `RPC URL: ${networkConfig.rpcUrls[0]}\n` +
        `Chain ID: ${parseInt(networkConfig.chainId, 16)}\n` +
        `Native Currency: ${networkConfig.nativeCurrency.symbol}\n` +
        `Explorer: ${networkConfig.blockExplorerUrls[0]}`
      );

      setStep(2);
      setTimeout(checkRequirements, 1000);
    } catch (err) {
      setError(`Failed to retrieve network configuration: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const addUSDC = async () => {
    try {
      setLoading(true);
      const netRes = await axios.get(`${API_BASE}/wallet/network-config`, { headers });
      const usdcConfig = netRes.data.usdc.config;

      alert(`Add USDC token to your wallet with this contract address:\n` +
        `Address: ${usdcConfig.address}\n` +
        `Symbol: ${usdcConfig.symbol}\n` +
        `Decimals: ${usdcConfig.decimals}`
      );

      setStep(3);
      setTimeout(checkRequirements, 1000);
    } catch (err) {
      setError(`Failed to retrieve token configuration: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getFaucetLinks = async () => {
    try {
      const res = await axios.get(`${API_BASE}/wallet/faucets`, { headers });
      return res.data;
    } catch (err) {
      return null;
    }
  };

  if (loading) {
    return <div className="wallet-setup loading">Checking wallet requirements...</div>;
  }

  if (!requirements) {
    return <div className="wallet-setup error">Failed to check wallet: {error}</div>;
  }

  const { kite, usdc, ready_to_purchase, issues } = requirements;

  return (
    <div className="wallet-setup">
      <div className="setup-header">
        <h2>🔐 Wallet Setup</h2>
        <div className="setup-steps">
          {STEPS.map((s, i) => (
            <div
              key={i}
              className={`step ${i === step ? "active" : i < step ? "completed" : ""}`}
            >
              {i < step ? "✓" : i + 1}
            </div>
          ))}
        </div>
      </div>

      {/* Current Balances */}
      {balances && (
        <div className="balances-section">
          <h3>💰 Current Balances</h3>
          <div className="balance-cards">
            <div className={`balance-card ${kite.sufficient ? "sufficient" : "insufficient"}`}>
              <div className="token-name">KITE (Gas)</div>
              <div className="balance-amount">{kite.balance.toFixed(4)} KITE</div>
              {!kite.sufficient && (
                <div className="need-more">Need: {kite.needs.toFixed(4)} more</div>
              )}
              {kite.sufficient && <div className="status-ok">✓ Sufficient</div>}
            </div>

            <div className={`balance-card ${usdc.sufficient ? "sufficient" : "insufficient"}`}>
              <div className="token-name">USDT (Payments)</div>
              <div className="balance-amount">${usdc.balance.toFixed(2)}</div>
              {!usdc.sufficient && (
                <div className="need-more">Need: ${usdc.needs.toFixed(2)} more</div>
              )}
              {usdc.sufficient && <div className="status-ok">✓ Sufficient</div>}
            </div>
          </div>
        </div>
      )}

      {/* Issues & Setup Steps */}
      {issues.length > 0 && (
        <div className="issues-section">
          <h3>⚠️ Setup Required</h3>
          
          {issues.some(i => i.type === "insufficient_kite") && (
            <div className="issue-block kite-issue">
              <h4>Need KITE for Gas Fees</h4>
              <p>No public faucet on Kite AI Mainnet. Fund your wallet via exchange, bridge, or direct transfer.</p>
              <button
                onClick={() => alert('No public faucet on KiteAI Mainnet. Fund via exchange, bridge, or transfer.')}
                className="faucet-btn"
              >
                🔗 Funding Guidance
              </button>
            </div>
          )}

          {issues.some(i => i.type === "insufficient_usdt") && (
            <div className="issue-block usdc-issue">
              <h4>Need USDC for Purchases</h4>
              <p>No public faucet on Kite AI Mainnet. Fund your wallet with USDC via exchange, bridge, or direct transfer.</p>
              <button
                onClick={() => alert('No public faucet on KiteAI Mainnet. Fund via exchange, bridge, or transfer.')}
                className="faucet-btn"
              >
                🔗 Funding Guidance
              </button>
            </div>
          )}

          {step === 1 && (
            <div className="setup-action">
              <h4>Step 1: Add KITE AI Mainnet</h4>
              <button
                onClick={addNetwork}
                className="action-btn primary"
              >
                ➕ Get Kite AI network setup instructions
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="setup-action">
              <h4>Step 2: Add USDT Token to your wallet</h4>
              <button
                onClick={addUSDC}
                className="action-btn primary"
              >
                ➕ Add USDT Token
              </button>
            </div>
          )}

          {step === 3 && (
            <div className="setup-action">
              <h4>Step 3: Fund Wallet</h4>
              <p className="setup-instruction">
                Fund your wallet with KITE and USDC on Kite AI Mainnet, then refresh this page
              </p>
              <button
                onClick={checkRequirements}
                className="action-btn secondary"
              >
                🔄 Refresh & Check
              </button>
            </div>
          )}
        </div>
      )}

      {/* Success State */}
      {ready_to_purchase && (
        <div className="success-section">
          <h3>✅ All Set!</h3>
          <div className="success-message">
            <p>Your wallet is ready for autonomous commerce:</p>
            <ul>
              <li>✓ KITE AI Mainnet configured</li>
              <li>✓ USDC token added</li>
              <li>✓ Sufficient KITE for gas</li>
              <li>✓ Sufficient USDC for purchases</li>
            </ul>
          </div>
          <button
            onClick={() => onReady?.(true)}
            className="action-btn success"
          >
            🚀 Start Shopping
          </button>
        </div>
      )}

      {/* Refresh Button */}
      {!ready_to_purchase && (
        <div className="refresh-section">
          <button
            onClick={checkRequirements}
            disabled={loading}
            className="refresh-btn"
          >
            🔄 Refresh Status
          </button>
        </div>
      )}

      {error && (
        <div className="error-message">
          <p>Error: {error}</p>
        </div>
      )}
    </div>
  );
};

export default WalletSetup;
