/* eslint-env es2020 */
import { ethers } from "ethers";
import { NETWORKS } from "gokite-aa-sdk/dist/config.js";
import * as utils from "gokite-aa-sdk/dist/utils.js";

class AASDKError extends Error {
  constructor(error) {
    super(error.message);
    this.name = "AASDKError";
    this.type = error.type;
    this.code = error.code;
    this.details = error.details;
  }
}

function classifyError(error, context) {
  if (error.name === "TypeError" || error.message?.includes("fetch")) {
    return {
      type: "NETWORK_ERROR",
      message: `Network error during ${context}: ${error.message}`,
      details: error,
    };
  }
  if (error.code) {
    const errorType = context.includes("estimate") ? "ESTIMATE_GAS_FAILED" : "SEND_USEROP_FAILED";
    let specificType = errorType;
    if (error.code === -32602 || error.message?.includes("insufficient funds")) {
      specificType = "INSUFFICIENT_FUNDS";
    } else if (error.code === -32602 || error.message?.includes("signature")) {
      specificType = "INVALID_SIGNATURE";
    } else if (error.code < 0) {
      specificType = "BUNDLER_ERROR";
    }
    return {
      type: specificType,
      message: error.message || `${context} failed`,
      code: error.code,
      details: error,
    };
  }
  return {
    type: "UNKNOWN_ERROR",
    message: error.message || `Unknown error during ${context}`,
    details: error,
  };
}

class BundlerProvider {
  constructor(bundlerUrl) {
    this.bundlerUrl = bundlerUrl;
  }

  async estimateUserOperationGas(userOp, entryPoint) {
    try {
      const response = await fetch(this.bundlerUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: Date.now(),
          method: "eth_estimateUserOperationGas",
          params: [(0, utils.serializeUserOperation)(userOp), entryPoint],
        }),
      });
      const result = await response.json();
      if (result.error) {
        throw new AASDKError(classifyError(result.error, "estimate gas"));
      }
      if (!result.result) {
        throw new AASDKError({
          type: "ESTIMATE_GAS_FAILED",
          message: "No gas estimate result returned from bundler",
        });
      }
      return {
        callGasLimit: BigInt(result.result.callGasLimit),
        verificationGasLimit: BigInt(result.result.verificationGasLimit),
        preVerificationGas: BigInt(result.result.preVerificationGas),
        maxFeePerGas: BigInt(25000000000),
        maxPriorityFeePerGas: BigInt(25000000000),
      };
    } catch (error) {
      if (error instanceof AASDKError) throw error;
      throw new AASDKError(classifyError(error, "estimate gas"));
    }
  }

  async sendUserOperation(userOp, entryPoint) {
    try {
      const serializedUserOp = (0, utils.serializeUserOperation)(userOp);
      const response = await fetch(this.bundlerUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: Date.now(),
          method: "eth_sendUserOperation",
          params: [serializedUserOp, entryPoint],
        }),
      });
      const result = await response.json();
      if (result.error) {
        throw new AASDKError(classifyError(result.error, "send user operation"));
      }
      if (!result.result) {
        throw new AASDKError({
          type: "SEND_USEROP_FAILED",
          message: "No user operation hash returned from bundler",
        });
      }
      return result.result;
    } catch (error) {
      if (error instanceof AASDKError) throw error;
      throw new AASDKError(classifyError(error, "send user operation"));
    }
  }

  async getUserOperationStatus(userOpHash) {
    const response = await fetch(this.bundlerUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: Date.now(),
        method: "eth_getUserOperationReceipt",
        params: [userOpHash],
      }),
    });
    const result = await response.json();
    if (result.error || !result.result) {
      return { userOpHash, status: "pending" };
    }
    const receipt = result.result;
    const status = receipt.success ? "success" : "reverted";
    return {
      userOpHash,
      status,
      transactionHash: receipt.receipt.transactionHash,
      blockNumber: parseInt(receipt.receipt.blockNumber, 16),
      gasUsed: receipt.receipt.gasUsed,
      actualGasCost: receipt.actualGasCost,
      reason: receipt.reason,
      receipt,
    };
  }

  async getUserOperationByHash(userOpHash) {
    const response = await fetch(this.bundlerUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: Date.now(),
        method: "eth_getUserOperationByHash",
        params: [userOpHash],
      }),
    });
    const result = await response.json();
    return result.result || null;
  }
}

class GokiteAASDK {
  constructor(network, rpcUrl, bundlerUrl) {
    this.config = NETWORKS[network];
    if (!this.config) {
      throw new Error(`Unsupported network: ${network}`);
    }
    this.ethersProvider = new ethers.JsonRpcProvider(rpcUrl);
    if (bundlerUrl) {
      this.provider = new BundlerProvider(bundlerUrl);
    } else {
      throw new Error("Bundler URL is required");
    }
  }

  getAccountAddress(owner, salt) {
    const actualSalt = salt || (0, utils.generateSalt)();
    return (0, utils.getAccountAddress)(this.config.accountFactory, this.config.accountImplementation, owner, actualSalt);
  }

  async getAccountNonce(accountAddress) {
    const entryPoint = new ethers.Contract(this.config.entryPoint, ['function getNonce(address,uint192) view returns (uint256)'], this.ethersProvider);
    return await entryPoint.getNonce(accountAddress, 0);
  }

  async getUserOpHash(userOp) {
    const entryPoint = new ethers.Contract(this.config.entryPoint, ['function getUserOpHash((address,uint256,bytes,bytes,bytes32,uint256,bytes32,bytes,bytes)) view returns (bytes32)'], this.ethersProvider);
    const packedUserOp = [
      userOp.sender,
      userOp.nonce,
      userOp.initCode,
      userOp.callData,
      userOp.accountGasLimits,
      userOp.preVerificationGas,
      userOp.gasFees,
      userOp.paymasterAndData,
      '0x',
    ];
    const hash = await entryPoint.getUserOpHash(packedUserOp);
    return hash;
  }

  async isAccountDeloyed(accountAddress) {
    const code = await this.ethersProvider.getCode(accountAddress);
    return code !== '0x';
  }

  buildInitCode(owner, salt) {
    const initCallData = (0, utils.encodeFunctionCall)(['function createAccount(address,uint256) returns (address)'], 'createAccount', [owner, salt]);
    return this.config.accountFactory + initCallData.slice(2);
  }

  buildCallData(request) {
    return (0, utils.encodeFunctionCall)(['function execute(address,uint256,bytes)'], 'execute', [request.target, request.value || 0n, request.callData]);
  }

  buildBatchCallData(request) {
    const values = request.values || new Array(request.targets.length).fill(0n);
    return (0, utils.encodeFunctionCall)(['function executeBatch(address[],uint256[],bytes[])'], 'executeBatch', [request.targets, values, request.callDatas]);
  }

  prependAddSupportedToken(request, accountAddress) {
    const settlementToken = this.config.settlementToken;
    const addTokenCallData = (0, utils.encodeFunctionCall)(['function addSupportedToken(address)'], 'addSupportedToken', [settlementToken]);
    if ('target' in request) {
      return {
        targets: [accountAddress, request.target],
        values: [BigInt(0), request.value || BigInt(0)],
        callDatas: [addTokenCallData, request.callData],
      };
    }
    return {
      targets: [accountAddress, ...request.targets],
      values: [BigInt(0), ...(request.values || new Array(request.targets.length).fill(BigInt(0)))],
      callDatas: [addTokenCallData, ...request.callDatas],
    };
  }

  async createUserOperation(owner, request, salt, paymasterAddress, tokenAddress) {
    const actualSalt = salt || (0, utils.generateSalt)();
    const accountAddress = this.getAccountAddress(owner, actualSalt);
    const isDeployed = await this.isAccountDeloyed(accountAddress);
    let finalRequest = request;
    if (!isDeployed) {
      finalRequest = this.prependAddSupportedToken(request, accountAddress);
    }
    const callData = 'targets' in finalRequest
      ? this.buildBatchCallData(finalRequest)
      : this.buildCallData(finalRequest);
    const callGasLimit = BigInt(300000);
    const verificationGasLimit = BigInt(300000);
    const preVerificationGas = BigInt(1000000);
    const maxFeePerGas = BigInt(10000000);
    const maxPriorityFeePerGas = BigInt(1);
    const accountGasLimits = (0, utils.packAccountGasLimits)(verificationGasLimit, callGasLimit);
    const gasFees = (0, utils.packAccountGasLimits)(maxPriorityFeePerGas, maxFeePerGas);
    if (!paymasterAddress) {
      paymasterAddress = this.config.paymaster;
    }
    let paymasterAndData = '0x';
    if (paymasterAddress) {
      tokenAddress = tokenAddress || this.config.supportedTokens[1].address;
      const paymasterData = ethers.solidityPacked(['address'], [tokenAddress]);
      paymasterAndData = (0, utils.packPaymasterAndData)(paymasterAddress, BigInt(500000), BigInt(500000), paymasterData);
    }
    return {
      sender: accountAddress,
      nonce: await this.getAccountNonce(accountAddress),
      initCode: isDeployed ? '0x' : this.buildInitCode(owner, actualSalt),
      callData,
      accountGasLimits,
      preVerificationGas,
      gasFees,
      paymasterAndData,
      signature: '0x',
    };
  }

  async estimateGas(userOp) {
    const userOpForEstimation = (0, utils.createUserOpForEstimation)(userOp);
    return await this.provider.estimateUserOperationGas(userOpForEstimation, this.config.entryPoint);
  }

  async sendUserOperation(owner, request, signFn, salt, paymasterAddress, tokenAddress) {
    const userOp = await this.createUserOperation(owner, request, salt, paymasterAddress, tokenAddress);
    const userOpWithDummy = (0, utils.createUserOpForEstimation)(userOp);
    const gasEstimate = await this.provider.estimateUserOperationGas(userOpWithDummy, this.config.entryPoint);
    gasEstimate.callGasLimit = gasEstimate.callGasLimit + 5000000n;
    userOp.accountGasLimits = (0, utils.packAccountGasLimits)(gasEstimate.verificationGasLimit, gasEstimate.callGasLimit);
    userOp.preVerificationGas = gasEstimate.preVerificationGas;
    userOp.gasFees = (0, utils.packAccountGasLimits)(gasEstimate.maxPriorityFeePerGas, gasEstimate.maxFeePerGas);
    const userOpHash = await this.getUserOpHash(userOp);
    const signature = await signFn(userOpHash);
    userOp.signature = signature;
    return await this.provider.sendUserOperation(userOp, this.config.entryPoint);
  }

  async getUserOperationStatus(userOpHash) {
    return await this.provider.getUserOperationStatus(userOpHash);
  }

  async pollUserOperationStatus(userOpHash, options = {}) {
    const { interval = 2000, timeout = 60000, maxRetries = 30 } = options;
    const startTime = Date.now();
    let retryCount = 0;
    while (Date.now() - startTime < timeout && retryCount < maxRetries) {
      try {
        const status = await this.getUserOperationStatus(userOpHash);
        if (status.status === 'success' || status.status === 'reverted' || status.status === 'failed') {
          return status;
        }
        retryCount++;
        if (retryCount < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, interval));
        }
      } catch (error) {
        retryCount++;
        if (retryCount < maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, interval));
        }
      }
    }
    throw new Error(`UserOp polling timeout: ${userOpHash} (attempt ${retryCount})`);
  }

  async sendUserOperationAndWait(owner, request, signFn, salt, paymasterAddress, pollingOptions) {
    const userOpHash = await this.sendUserOperation(owner, request, signFn, salt, paymasterAddress);
    const status = await this.pollUserOperationStatus(userOpHash, pollingOptions);
    return { userOpHash, status };
  }
}

export { GokiteAASDK };
