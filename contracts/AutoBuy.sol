// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint amount) external returns (bool);
}

contract AutoBuy {

    address public usdcToken;

    constructor(address _usdcToken) {
        usdcToken = _usdcToken;
    }

    function executePurchase(
        address buyer,
        address vendor,
        uint amount
    ) public {
        IERC20(usdcToken).transferFrom(buyer, vendor, amount);
    }
}