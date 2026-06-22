// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract OrgRegistry {

    struct Organization {
        uint256 id;
        string name;
        address wallet;
        bool exists;
    }

    uint256 public orgCount;

    mapping(uint256 => Organization) public organizations;
    mapping(address => uint256) public walletToOrgId;

    event OrganizationRegistered(uint256 indexed orgId, string name, address wallet);

    function registerOrganization(string memory _name) external {
        require(walletToOrgId[msg.sender] == 0, "Already registered");

        orgCount++;

        organizations[orgCount] = Organization({
            id: orgCount,
            name: _name,
            wallet: msg.sender,
            exists: true
        });

        walletToOrgId[msg.sender] = orgCount;

        emit OrganizationRegistered(orgCount, _name, msg.sender);
    }

    function getOrganization(uint256 _orgId) external view returns (
        uint256 id,
        string memory name,
        address wallet
    ) {
        require(organizations[_orgId].exists, "Org does not exist");

        Organization memory org = organizations[_orgId];
        return (org.id, org.name, org.wallet);
    }
}
