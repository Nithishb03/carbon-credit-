// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract CarbonStaking {
    struct Enterprise {
        uint256 stakedAmount;
        uint256 reputationScore; // Starts at 100
        uint256 totalCreditsMinted;
        bool isActive;
    }

    struct ValidatorProfile {
        uint256 nodeReputation;  // Selection weight based on historics
        bool isRegistered;
    }

    struct ComplianceReport {
        address dataOwner;
        string storageURI;       // Simulates off-chain IPFS/CID location
        uint256 calculatedCO2;
        bool finalized;
        bool anomalyFlagged;
    }

    address public protocolAdmin;
    address[] public registeredValidators;

    mapping(address => Enterprise) public enterprises;
    mapping(address => ValidatorProfile) public validators;
    mapping(bytes32 => ComplianceReport) public ledgerReports; // reportHash => Record

    event EnterpriseOnboarded(address indexed enterprise, uint256 deposit);
    event ReportCommitted(bytes32 indexed reportHash, address indexed submitter, string storageURI);
    event ValidationSettled(bytes32 indexed reportHash, bool indexed legitimate, uint256 penaltyOrReward);

    modifier onlyAdmin() {
        require(msg.sender == protocolAdmin, "Unauthorized network caller");
        _;
    }

    constructor() {
        protocolAdmin = msg.sender;
    }

    function registerEnterprise() external payable {
        require(!enterprises[msg.sender].isActive, "Profile already initialized");
        require(msg.value >= 1 ether, "Escrow collateral requires min 1 ETH");

        enterprises[msg.sender] = Enterprise({
            stakedAmount: msg.value,
            reputationScore: 100,
            totalCreditsMinted: 0,
            isActive: true
        });
        emit EnterpriseOnboarded(msg.sender, msg.value);
    }

    function registerValidatorNode(address _node) external onlyAdmin {
        require(!validators[_node].isRegistered, "Validator node already in pool");
        validators[_node] = ValidatorProfile(100, true);
        registeredValidators.push(_node);
    }

    function commitReport(bytes32 _reportHash, string calldata _storageURI) external {
        require(enterprises[msg.sender].isActive, "Unregistered data provider");
        require(ledgerReports[_reportHash].dataOwner == address(0), "Report hash already committed");

        ledgerReports[_reportHash] = ComplianceReport({
            dataOwner: msg.sender,
            storageURI: _storageURI,
            calculatedCO2: 0,
            finalized: false,
            anomalyFlagged: false
        });

        emit ReportCommitted(_reportHash, msg.sender, _storageURI);
    }

    function settleEscrow(
        bytes32 _reportHash, 
        bool _isValid, 
        uint256 _co2Calculated
    ) external onlyAdmin {
        ComplianceReport storage report = ledgerReports[_reportHash];
        require(report.dataOwner != address(0), "Target record not found");
        require(!report.finalized, "Transaction already settled");

        address enterpriseAddr = report.dataOwner;
        Enterprise storage target = enterprises[enterpriseAddr];

        if (_isValid) {
            target.reputationScore += 1;
            target.totalCreditsMinted += _co2Calculated;
            report.calculatedCO2 = _co2Calculated;
            report.anomalyFlagged = false;
        } else {
            // Slashing execution path
            uint256 penalty = 0.2 ether;
            if (target.stakedAmount > penalty) {
                target.stakedAmount -= penalty;
            } else {
                target.stakedAmount = 0;
                target.isActive = false;
            }
            
            if (target.reputationScore > 10) {
                target.reputationScore -= 10;
            } else {
                target.reputationScore = 0;
            }
            report.anomalyFlagged = true;
        }

        report.finalized = true;
        emit ValidationSettled(_reportHash, _isValid, _co2Calculated);
    }

    // Network getters for peer explorer
    function getValidatorPool() external view returns (address[] memory) {
        return registeredValidators;
    }
}