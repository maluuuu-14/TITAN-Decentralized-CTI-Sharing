// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./OrgRegistry.sol";
import "./CTIRegistry.sol";

contract Reputation {
    struct RatingStats {
        uint256 totalScore;
        uint256 ratingCount;
    }
    
    OrgRegistry public orgRegistry;
    CTIRegistry public ctiRegistry;

    mapping(uint256 => uint256[]) private orgRatings;
    mapping(uint256 => uint256) public reputationScore;
    
    // Tracks the total score and vote count for specific CTI data
    mapping(uint256 => RatingStats) public ctiRatings;
    
    event RatingSubmitted(
        uint256 indexed ratedOrgId,
        uint256 score,
        uint256 newReputation
    );

    constructor(address _orgRegistry, address _ctiRegistry) {
        orgRegistry = OrgRegistry(_orgRegistry);
        ctiRegistry = CTIRegistry(_ctiRegistry);
    }

    function submitRating(uint256 _ctiId, uint8 _score) external {
        require(_score > 0 && _score <= 5, "Score must be 1-5");

        // Get rater org
        uint256 raterOrgId = orgRegistry.walletToOrgId(msg.sender);
        require(raterOrgId != 0, "Rater not registered");

        // Get CTI details
        (, , uint256 producerOrgId, ) = ctiRegistry.getCTI(_ctiId);

        require(producerOrgId != raterOrgId, "Cannot rate yourself");

        // --- NEW: Track the specific CTI's rating ---
        ctiRatings[_ctiId].totalScore += _score;
        ctiRatings[_ctiId].ratingCount += 1;
        // --------------------------------------------

        // Update the Organization's overall rating history
        orgRatings[producerOrgId].push(_score);

        // Calculate new average for the Organization
        uint256 total = 0;
        for (uint256 i = 0; i < orgRatings[producerOrgId].length; i++) {
            total += orgRatings[producerOrgId][i];
        }

        uint256 avg = total / orgRatings[producerOrgId].length;
        reputationScore[producerOrgId] = avg;

        emit RatingSubmitted(producerOrgId, _score, avg);
    }

    function getReputation(uint256 _orgId) external view returns (uint256) {
        return reputationScore[_orgId];
    }

    // --- NEW: Calculate the average rating for a specific CTI ID ---
    function getAverageRating(uint256 _ctiId) external view returns (uint256) {
        if (ctiRatings[_ctiId].ratingCount == 0) {
            return 0; // Prevent divide-by-zero if no ratings yet
        }
        return ctiRatings[_ctiId].totalScore / ctiRatings[_ctiId].ratingCount;
    }
}