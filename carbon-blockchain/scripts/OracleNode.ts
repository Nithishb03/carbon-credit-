import { network } from "hardhat";
import { getAddress, parseEther, toHex } from "viem";

const STAKING_CONTRACT_ADDRESS = "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512";

async function main() {
  console.log("🟢 Booting Validator Oracle Node...");

  // 1. Setup Network Clients
  const { viem } = await network.create();
  const [owner, enterprise, validator] = await viem.getWalletClients();

  // Create a contract instance bound to the deployed address.
  const stakingContract = await viem.getContractAt(
    "CarbonStaking",
    STAKING_CONTRACT_ADDRESS,
    { client: { wallet: validator } } // The Validator pays the gas to submit the proof
  );

  console.log(`\n📡 Oracle connected to Staking Contract at: ${STAKING_CONTRACT_ADDRESS}`);
  console.log(`👤 Validator Wallet: ${validator.account.address}`);

  // 2. Setup: Ensure the enterprise is registered and staked (Simulation purposes)
  const enterpriseData = await stakingContract.read.enterprises([
    getAddress(enterprise.account.address),
  ]);
  if (!enterpriseData[3]) {
    console.log(`\n🏦 Enterprise ${enterprise.account.address} is not staked. Staking 1 ETH now...`);
    const stakingContractAsEnterprise = await viem.getContractAt(
      "CarbonStaking",
      STAKING_CONTRACT_ADDRESS,
      { client: { wallet: enterprise } }
    );
    await stakingContractAsEnterprise.write.registerAndStake({ value: parseEther("1") });
    console.log("✅ Enterprise Staked 1 ETH.");
  }

  // =====================================================================
  // THE ORACLE LOOP: Fetching Data -> ML Inference -> Smart Contract Call
  // =====================================================================

  console.log("\n⚙️  Simulating ML Validation Cycle...");

  // SIMULATION A: Legitimate Data
  console.log("\n--- Cycle 1: Legitimate Data ---");
  console.log("🧠 ML Model evaluated IoT Payload: NORMAL");

  // We generate the "Proof" (0x01 = valid in our mock verifier)
  let proof = toHex(new Uint8Array([1]));
  let tx = await stakingContract.write.submitValidation([
    getAddress(enterprise.account.address),
    proof,
    [], // pubInputs (Empty for mock)
    500n, // Expected CO2
  ]);
  console.log(`⛓️  Transaction Submitted on-chain! Hash: ${tx}`);

  let state = await stakingContract.read.enterprises([
    getAddress(enterprise.account.address),
  ]);
  console.log(`📊 Enterprise State -> Stake: ${state[0]}, Score: ${state[1]}`);

  // SIMULATION B: Fraudulent Data (The Analog Hole)
  console.log("\n--- Cycle 2: Anomalous Data Detected ---");
  console.log("🚨 ML Model evaluated IoT Payload: FRAUD (Sensor Tampering Detected!)");

  // We generate the "Proof" (0x00 = invalid in our mock verifier)
  proof = toHex(new Uint8Array([0]));
  tx = await stakingContract.write.submitValidation([
    getAddress(enterprise.account.address),
    proof,
    [],
    0n,
  ]);
  console.log(`⛓️  Slashing Transaction Submitted on-chain! Hash: ${tx}`);

  state = await stakingContract.read.enterprises([
    getAddress(enterprise.account.address),
  ]);
  console.log(`💥 Enterprise State -> Stake: ${state[0]}, Score: ${state[1]} (SLASHED)`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
