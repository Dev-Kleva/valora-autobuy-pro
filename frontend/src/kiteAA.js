import { GokiteAASDK } from "gokite-aa-sdk";
import { Wallet, Interface, getBytes } from "ethers";

const KITE_AA_NETWORK = process.env.REACT_APP_KITE_AA_NETWORK || "kite_mainnet";
const KITE_AA_RPC_URL = process.env.REACT_APP_KITE_AA_RPC_URL || "https://rpc.gokite.ai/";
const KITE_AA_BUNDLER_RPC = process.env.REACT_APP_KITE_AA_BUNDLER_RPC || "https://bundler-service.staging.gokite.ai/rpc/";

const sdk = new GokiteAASDK(KITE_AA_NETWORK, KITE_AA_RPC_URL, KITE_AA_BUNDLER_RPC);

export async function getAccountAddress(ownerAddress) {
  if (!ownerAddress) {
    throw new Error("ownerAddress is required to derive a Kite AA account");
  }

  return sdk.getAccountAddress(ownerAddress);
}

function getAASigner() {
  const privateKey = process.env.REACT_APP_KITE_AA_EOA_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error("REACT_APP_KITE_AA_EOA_PRIVATE_KEY is not configured for Kite AA signing.");
  }

  return new Wallet(privateKey);
}

export async function sendStablecoinPayment({ ownerAddress, tokenAddress, recipientAddress, amountRaw }) {
  const signer = getAASigner();
  const feePayerAddress = signer.address;
  const erc20Interface = new Interface(["function transfer(address to, uint256 value)"]);

  const callData = erc20Interface.encodeFunctionData("transfer", [recipientAddress, amountRaw]);
  const request = {
    target: tokenAddress,
    value: "0x0",
    callData,
  };

  return sdk.sendUserOperationAndWait(feePayerAddress, request, async (userOpHash) => {
    return signer.signMessage(getBytes(userOpHash));
  });
}
