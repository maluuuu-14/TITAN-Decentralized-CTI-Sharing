// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./OrgRegistry.sol";

contract CTIRegistry {

    struct CTI {
        uint256 id;
        bytes32 hash;
        uint256 orgId;
        uint256 timestamp;
        bool exists;
    }

    uint256 public ctiCount;

    mapping(uint256 => CTI) public ctiItems;

    OrgRegistry public orgRegistry;

    event CTIRegistered(
        uint256 indexed ctiId,
        bytes32 hash,
        uint256 indexed orgId,
        uint256 timestamp
    );

    constructor(address _orgRegistryAddress) {
        orgRegistry = OrgRegistry(_orgRegistryAddress);
    }

    function registerCTI(bytes32 _hash) external {

        uint256 orgId = orgRegistry.walletToOrgId(msg.sender);
        require(orgId != 0, "Not a registered organization");

        ctiCount++;

        ctiItems[ctiCount] = CTI({
            id: ctiCount,
            hash: _hash,
            orgId: orgId,
            timestamp: block.timestamp,
            exists: true
        });

        emit CTIRegistered(ctiCount, _hash, orgId, block.timestamp);
    }

    function getCTI(uint256 _ctiId) external view returns (
        uint256 id,
        bytes32 hash,
        uint256 orgId,
        uint256 timestamp
    ) {
        require(ctiItems[_ctiId].exists, "CTI does not exist");

        CTI memory item = ctiItems[_ctiId];

        return (item.id, item.hash, item.orgId, item.timestamp);
    }
}
