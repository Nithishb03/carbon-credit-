import hre from "hardhat";

async function main() {
  console.log("Starting deployment...");

  // 1. Deploy the Mock Verifier (Kept for architecture mapping)
  const verifier = await hre.viem.deployContract("Verifier");
  console.log(`✅ Verifier deployed to: ${verifier.address}`);

  // 2. Deploy CarbonStaking (Removed the constructor argument array)
  const staking = await hre.viem.deployContract("CarbonStaking");
  console.log(`✅ CarbonStaking deployed to: ${staking.address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});