// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Vulnerable {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function dangerous(address target) external {
        require(tx.origin == owner);

        (bool ok, ) = target.call("");

        require(ok);

        uint256 t = block.timestamp;

        if (t > 0) {
            selfdestruct(payable(msg.sender));
        }
    }
}
