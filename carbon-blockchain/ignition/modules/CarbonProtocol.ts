import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const CarbonProtocolModule = buildModule("CarbonProtocolModule", (m) => {
  // 1. Deploy the Verifier contract
  const verifier = m.contract("Verifier");

  // 2. Deploy the CarbonStaking contract (No constructor arguments needed now!)
  const carbonStaking = m.contract("CarbonStaking");

  return { verifier, carbonStaking };
});

export default CarbonProtocolModule;