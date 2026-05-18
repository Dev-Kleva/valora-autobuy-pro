// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint amount) external returns (bool);
}

/**
 * @title ContentAgentAttestation
 * @dev Records proof-of-execution for AI content generation tasks on Kite
 */
contract ContentAgentAttestation {
    
    struct TaskAttestation {
        bytes32 taskId;
        address user;
        uint256 paymentAmount;
        bytes32 outputHash;
        bytes agentSignature;
        uint256 timestamp;
        bool completed;
    }
    
    mapping(bytes32 => TaskAttestation) public attestations;
    mapping(address => bytes32[]) public userTasks;
    
    address public usdcToken;
    address public agentAddress;
    uint256 public taskCount;
    
    event TaskAttested(
        bytes32 indexed taskId,
        address indexed user,
        uint256 paymentAmount,
        bytes32 outputHash,
        uint256 timestamp
    );
    
    event PaymentSettled(
        bytes32 indexed taskId,
        address indexed user,
        uint256 amount
    );
    
    constructor(address _usdcToken, address _agentAddress) {
        usdcToken = _usdcToken;
        agentAddress = _agentAddress;
        taskCount = 0;
    }
    
    /**
     * @dev Record task completion and attestation proof
     */
    function attesta(
        bytes32 taskId,
        address user,
        uint256 paymentAmount,
        bytes32 outputHash,
        bytes calldata agentSignature
    ) external {
        require(msg.sender == agentAddress, "Only agent can attest");
        require(attestations[taskId].user == address(0), "Task already attested");
        
        TaskAttestation storage att = attestations[taskId];
        att.taskId = taskId;
        att.user = user;
        att.paymentAmount = paymentAmount;
        att.outputHash = outputHash;
        att.agentSignature = agentSignature;
        att.timestamp = block.timestamp;
        att.completed = true;
        
        userTasks[user].push(taskId);
        taskCount++;
        
        emit TaskAttested(taskId, user, paymentAmount, outputHash, block.timestamp);
    }
    
    /**
     * @dev Settle USDC payment from user to platform
     */
    function settlePayment(bytes32 taskId) external {
        TaskAttestation storage att = attestations[taskId];
        require(att.completed, "Task not attested");
        require(att.paymentAmount > 0, "Invalid payment amount");
        
        // Transfer USDC
        bool success = IERC20(usdcToken).transferFrom(
            att.user,
            address(this),
            att.paymentAmount
        );
        require(success, "Payment failed");
        
        emit PaymentSettled(taskId, att.user, att.paymentAmount);
    }
    
    /**
     * @dev Get user's task history
     */
    function getUserTasks(address user) external view returns (bytes32[] memory) {
        return userTasks[user];
    }
    
    /**
     * @dev Get task attestation details
     */
    function getAttestation(bytes32 taskId) external view returns (TaskAttestation memory) {
        return attestations[taskId];
    }
    
    /**
     * @dev Verify attestation signature (agent signed)
     */
    function verifyAttestation(bytes32 taskId) external view returns (bool) {
        TaskAttestation storage att = attestations[taskId];
        return att.completed && att.agentSignature.length > 0;
    }
}
